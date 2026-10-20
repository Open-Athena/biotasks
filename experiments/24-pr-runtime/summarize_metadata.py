"""Reconcile cached GitHub IDs; never interpret failed reads as empty repositories."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def summarize():
    inputs = {
        row["repository"]: row
        for row in map(json.loads, (ROOT / "inventory/repositories.jsonl").read_text().splitlines())
    }
    seen = set()
    identities = {}
    unresolved = []
    for path in sorted((ROOT / "inventory/github").glob("*.json")):
        capture = json.loads(path.read_text())
        for i, requested in enumerate(capture["repositories"]):
            if requested in seen:
                raise ValueError(f"Duplicate observation: {requested}")
            seen.add(requested)
            metadata = capture["response"]["data"].get(f"r{i}")
            if metadata is None:
                unresolved.append({
                    "repository": requested, "status": "unresolved",
                    "capture": str(path.relative_to(ROOT)),
                    "errors": [error for error in capture["response"].get("errors", [])
                               if error.get("path", [None])[0] == f"r{i}"],
                })
                continue
            identity = identities.setdefault(metadata["id"], {
                "metadata": metadata, "requested_names": [],
                "primary_source_ids": [], "source_ids": [], "captures": [],
            })
            identity["requested_names"].append(requested)
            identity["primary_source_ids"].extend(inputs[requested]["primary_source_ids"])
            identity["source_ids"].extend(inputs[requested]["source_ids"])
            identity["captures"].append(str(path.relative_to(ROOT)))
    rows = []
    for identity in identities.values():
        for key in ("primary_source_ids", "source_ids"):
            identity[key] = sorted(set(identity[key]))
        rows.append(identity)
    rows.sort(key=lambda row: row["metadata"]["nameWithOwner"].lower())
    languages = Counter()
    primary_languages = Counter()
    for row in rows:
        language = (row["metadata"]["primaryLanguage"] or {}).get("name", "unknown")
        languages[language] += 1
        if row["primary_source_ids"]:
            primary_languages[language] += 1
    summary = {
        "requested_repository_names": len(inputs),
        "observed_names": len(seen),
        "not_yet_observed": sorted(set(inputs) - seen),
        "unresolved_names": len(unresolved),
        "unique_live_repository_ids": len(rows),
        "primary_source_repository_ids": sum(bool(r["primary_source_ids"]) for r in rows),
        "repositories_with_any_merged_pr": sum(r["metadata"]["pullRequests"]["totalCount"] > 0 for r in rows),
        "lifetime_merged_pr_total": sum(r["metadata"]["pullRequests"]["totalCount"] for r in rows),
        "archived_repository_ids": sum(r["metadata"]["isArchived"] for r in rows),
        "primary_languages_all_repositories": dict(languages.most_common()),
        "primary_languages_primary_source_repositories": dict(primary_languages.most_common()),
        "limitations": [
            "Merged PR totals cover lifetime, not the evaluation window.",
            "Primary language is not a test-runner compatibility judgment.",
            "Unresolved API reads are not zero-PR observations.",
            "Metadata observations are time-stamped individually, not transactionally.",
        ],
    }
    for name, records in (("live-repositories.jsonl", rows), ("unresolved-repositories.jsonl", unresolved)):
        (ROOT / "inventory" / name).write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in records))
    (ROOT / "inventory/live-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    summarize()
