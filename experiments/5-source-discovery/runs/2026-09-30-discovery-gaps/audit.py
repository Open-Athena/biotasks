"""Collect a frozen nominee panel and compare it with preserved discovery evidence."""

import argparse
import csv
import datetime
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent / "baseline"
TOP = BASE / "data/top200-2026-09-29"


def read_rows(path):
    with path.open() as handle:
        return list(csv.DictReader(handle, delimiter="\t" if path.suffix == ".tsv" else ","))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.UTC).isoformat()


def collect(corrections=False):
    nominees = read_rows(HERE / "nominees.tsv")
    prefix = "correction-" if corrections else ""
    if corrections:
        mapping = json.loads((HERE / "identity-corrections.json").read_text())
        nominees = [
            {
                **r,
                "original_nominee": r["repository"],
                "repository": mapping[r["repository"]]["repository"],
            }
            for r in nominees
            if r["repository"] in mapping
        ]
    assert len(nominees) <= 150
    assert len({r["repository"].lower() for r in nominees}) == len(nominees)
    fields = """id nameWithOwner url description stargazerCount isArchived isFork createdAt
      parent { nameWithOwner } defaultBranchRef { name target { oid } }
      repositoryTopics(first:100) { nodes { topic { name } } pageInfo { hasNextPage } }"""
    records, requests = [], []
    for offset in range(0, len(nominees), 30):
        batch = nominees[offset : offset + 30]
        clauses = []
        for i, row in enumerate(batch):
            owner, name = row["repository"].split("/")
            clauses.append(
                f"r{i}: repository(owner:{json.dumps(owner)},name:{json.dumps(name)}) {{ {fields} }}"
            )
        request = HERE / f"{prefix}query-{offset // 30 + 1:02}.json"
        response = HERE / f"{prefix}response-{offset // 30 + 1:02}.json"
        request.write_text(json.dumps({"query": "query {" + "\n".join(clauses) + "}"}) + "\n")
        start = now()
        proc = subprocess.run(
            ["gh", "api", "graphql", "--input", str(request)],
            capture_output=True,
            text=True,
            timeout=50,
        )
        response.write_text(proc.stdout)
        result = json.loads(proc.stdout)
        if "data" not in result:
            raise RuntimeError(f"No GraphQL data in {response.name}; return code {proc.returncode}")
        requests.append(
            {
                "request": request.name,
                "response": response.name,
                "observed_start": start,
                "observed_end": now(),
                "exit_status": proc.returncode,
                "sha256": digest(response),
                "errors": result.get("errors", []),
            }
        )
        for i, nominee in enumerate(batch):
            records.append(
                {**nominee, "metadata": result["data"].get(f"r{i}"), "response": response.name}
            )
        print(f"Observed {len(records)}/{len(nominees)} nominees", flush=True)
    output = {
        "checkpoint": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "nominees_sha256": digest(HERE / "nominees.tsv"),
        "requests": requests,
        "records": records,
    }
    (HERE / f"{prefix}observations.json").write_text(json.dumps(output, indent=2) + "\n")


def analyze():
    observations = json.loads((HERE / "observations.json").read_text())
    correction_file = HERE / "correction-observations.json"
    if correction_file.exists():
        corrected = {
            r["original_nominee"]: r for r in json.loads(correction_file.read_text())["records"]
        }
        for i, row in enumerate(observations["records"]):
            if row["repository"] in corrected:
                assert row["metadata"] is None
                replacement = corrected[row["repository"]]
                observations["records"][i] = {**replacement, "repository": row["repository"]}
    pool = {
        r["package"].lower(): r for r in read_rows(TOP / "ranking-candidates-github-2026-09-29.csv")
    }
    selected = read_rows(TOP / "rankings-2026-09-29.csv")
    original_terms = [
        r["query"].split(" in:")[0]
        for r in json.loads((BASE / "data/ranking-provenance-2026-09-29.json").read_text())[
            "github"
        ]["search_queries"]
    ]
    rows, seen = [], set()
    for observed in observations["records"]:
        meta = observed["metadata"]
        if not meta:
            rows.append(
                {
                    "requested": observed["repository"],
                    "area": observed["area"],
                    "status": "unresolved",
                }
            )
            continue
        if meta["id"] in seen:
            raise RuntimeError(
                "Alias duplicate in reference panel; deduplicate before reporting denominators"
            )
        seen.add(meta["id"])
        names = {observed["repository"].lower(), meta["nameWithOwner"].lower()}
        candidates = [pool[name] for name in names if name in pool]
        candidate = candidates[0] if candidates else None
        ranks = {
            r["ranking"]: int(r["rank"])
            for r in selected
            if r["source_id"].lower() in {"github:" + name for name in names}
        }
        topics = [r["topic"]["name"] for r in meta["repositoryTopics"]["nodes"]]
        haystack = " ".join([meta["nameWithOwner"], meta["description"] or "", *topics]).lower()
        rows.append(
            {
                "requested": observed["repository"],
                "canonical": meta["nameWithOwner"],
                "url": meta["url"],
                "head": (meta["defaultBranchRef"] or {}).get("target", {}).get("oid"),
                "area": observed["area"],
                "current_stars": meta["stargazerCount"],
                "archived": meta["isArchived"],
                "fork": meta["isFork"],
                "description": meta["description"],
                "topics": topics,
                "literal_query_term_matches": [t for t in original_terms if t in haystack],
                "in_saved_github_pool": bool(candidate),
                "saved_github_status": candidate["status"] if candidate else None,
                "saved_github_score": int(candidate["score"]) if candidate else None,
                "saved_exclusion_reason": candidate["reason"] if candidate else None,
                "selected_ranks": ranks,
                "status": "in_pool" if candidate else "absent_pool",
                "above_saved_cutoff_now": meta["stargazerCount"] >= 889,
                "response": observed["response"],
            }
        )
    resolved = [r for r in rows if r["status"] != "unresolved"]
    missing = sorted(
        [r for r in resolved if r["status"] == "absent_pool"], key=lambda r: -r["current_stars"]
    )
    summary = {
        "nominees": len(rows),
        "resolved_unique": len(resolved),
        "unresolved": [r["requested"] for r in rows if r["status"] == "unresolved"],
        "in_saved_github_pool": sum(r["in_saved_github_pool"] for r in resolved),
        "absent_saved_github_pool": len(missing),
        "absent_pool_above_saved_cutoff_now": sum(r["above_saved_cutoff_now"] for r in missing),
        "absent_four_list_union": sum(not r["selected_ranks"] for r in resolved),
        "selected_github": sum("github" in r["selected_ranks"] for r in resolved),
        "statuses": dict(
            Counter(r["saved_github_status"] for r in resolved if r["in_saved_github_pool"])
        ),
        "missing": missing,
    }
    result = {
        "observation_sha256": digest(HERE / "observations.json"),
        "correction_observation_sha256": digest(correction_file)
        if correction_file.exists()
        else None,
        "baseline_sha256": {
            str(p.relative_to(BASE)): digest(p)
            for p in [
                TOP / "ranking-candidates-github-2026-09-29.csv",
                TOP / "rankings-2026-09-29.csv",
            ]
        },
        "summary": summary,
        "records": rows,
    }
    (HERE / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def probe():
    results = []
    for case in json.loads((HERE / "probes.json").read_text()):
        query = f"{case['term']} repo:{case['repo']} in:{case['fields']} fork:false is:public stars:>=500"
        proc = subprocess.run(
            [
                "gh",
                "api",
                "search/repositories",
                "--method",
                "GET",
                "-f",
                "q=" + query,
                "-F",
                "per_page=10",
            ],
            capture_output=True,
            text=True,
            timeout=40,
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr)
        data = json.loads(proc.stdout)
        result = {
            **case,
            "query": query,
            "observed_at": now(),
            "total_count": data["total_count"],
            "incomplete_results": data["incomplete_results"],
            "matches": [r["full_name"] for r in data["items"]],
        }
        assert not result["incomplete_results"]
        results.append(result)
        (HERE / "probe-results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(case["repo"], case["term"], case["fields"], result["total_count"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["collect", "collect-corrections", "analyze", "probe"])
    args = parser.parse_args()
    if args.action == "collect":
        collect()
    elif args.action == "collect-corrections":
        collect(corrections=True)
    elif args.action == "probe":
        probe()
    else:
        analyze()
