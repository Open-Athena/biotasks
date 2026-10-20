"""Cache public GitHub metadata in bounded, serial GraphQL batches via normal gh."""

import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def collect(max_batches):
    rows = [json.loads(line) for line in (ROOT / "inventory/repositories.jsonl").read_text().splitlines()]
    out = ROOT / "inventory/github"
    out.mkdir(exist_ok=True)
    made = 0
    for offset in range(0, len(rows), 20):
        batch = rows[offset:offset + 20]
        fields = []
        for i, row in enumerate(batch):
            owner, name = row["repository"].split("/")
            fields.append(
                f"r{i}: repository(owner:{json.dumps(owner)},name:{json.dumps(name)})"
                "{id nameWithOwner url isArchived isFork isEmpty "
                "diskUsage pushedAt primaryLanguage{name} "
                "languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}} "
                "licenseInfo{spdxId} defaultBranchRef{name target{oid}} "
                "pullRequests(states:MERGED){totalCount}}"
            )
        query = "query {" + " ".join(fields) + " rateLimit{remaining resetAt cost}}"
        digest = hashlib.sha256(query.encode()).hexdigest()
        destination = out / f"{offset:04d}-{digest[:12]}.json"
        if destination.exists():
            cached = json.loads(destination.read_text())
            if cached["query_sha256"] != digest or cached["response"].get("data") is None:
                raise ValueError(f"Invalid cached response: {destination}")
            continue
        if made >= max_batches:
            break
        captured = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, timeout=60,
        )
        if not result.stdout.strip():
            raise RuntimeError(f"gh returned no JSON (exit {result.returncode}); not caching stderr")
        response = json.loads(result.stdout)
        if response.get("data") is None:
            raise RuntimeError(f"GraphQL request failed: {response.get('errors')}")
        record = {
            "captured_at": captured,
            "query_sha256": digest,
            "repositories": [row["repository"] for row in batch],
            "gh_exit_code": result.returncode,
            "response": response,
        }
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(destination)
        made += 1
        print(json.dumps({
            "offset": offset, "repositories": len(batch),
            "errors": len(response.get("errors", [])),
            "rate_limit": response["data"].get("rateLimit"),
        }), flush=True)
        rate = response["data"].get("rateLimit") or {}
        if rate.get("remaining", 0) < 100:
            raise RuntimeError("Stopping with fewer than 100 GraphQL points remaining")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 48:
        parser.error("max-batches must be between 1 and 48")
    collect(args.max_batches)
