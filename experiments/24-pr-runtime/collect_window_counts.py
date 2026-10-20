"""Count merged PRs in the frozen window for all live inventory repositories."""

import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def collect(max_batches):
    rows = [
        json.loads(line)
        for line in (ROOT / "inventory/live-repositories.jsonl").read_text().splitlines()
    ]
    panel = json.loads((ROOT / "inventory/repository-panel.json").read_text())
    window = panel["pr_window"]
    folder = ROOT / "inventory/window-counts"
    folder.mkdir(exist_ok=True)
    calls = 0
    summary = []
    for offset in range(0, len(rows), 20):
        batch = rows[offset:offset + 20]
        queries = [
            f"repo:{row['metadata']['nameWithOwner']} is:pr is:merged "
            f"merged:{window['since']}..{window['until']}"
            for row in batch
        ]
        query = "query{" + " ".join(
            f"r{i}:search(type:ISSUE,query:{json.dumps(q)}){{issueCount}}"
            for i, q in enumerate(queries)
        ) + " rateLimit{remaining resetAt cost}}"
        digest = hashlib.sha256(query.encode()).hexdigest()
        path = folder / f"{offset:04d}-{digest[:12]}.json"
        if path.exists():
            record = json.loads(path.read_text())
            if record["query_sha256"] != digest:
                raise ValueError("Cached query checksum mismatch")
        else:
            if calls >= max_batches:
                return
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True, text=True, timeout=60, check=True,
            )
            response = json.loads(result.stdout)
            if response.get("errors") or not response.get("data"):
                raise RuntimeError(f"Window counts incomplete: {response.get('errors')}")
            record = {
                "query_sha256": digest, "queries": queries, "window": window,
                "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "response": response,
            }
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(record, indent=2) + "\n")
            tmp.replace(path)
            calls += 1
        data = record["response"]["data"]
        for i, row in enumerate(batch):
            summary.append({
                "repository": row["metadata"]["nameWithOwner"],
                "github_id": row["metadata"]["id"],
                "primary_source": bool(row["primary_source_ids"]),
                "primary_language": (row["metadata"]["primaryLanguage"] or {}).get("name"),
                "archived": row["metadata"]["isArchived"],
                "merged_pr_count": data[f"r{i}"]["issueCount"],
                "evidence": str(path.relative_to(ROOT)),
            })
        print(json.dumps({
            "through": offset + len(batch),
            "window_merged_prs": sum(r["merged_pr_count"] for r in summary),
            "rate_limit": data["rateLimit"],
        }), flush=True)
        if data["rateLimit"]["remaining"] < 100:
            raise RuntimeError("GraphQL budget below 100 points")
    (ROOT / "inventory/window-counts.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in summary)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 48:
        parser.error("max-batches must be between 1 and 48")
    collect(args.max_batches)
