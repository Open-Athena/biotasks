"""Select a reproducible language-stratified metadata panel before inspecting PRs."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = "biotasks-24-pr-runtime-repositories-v1"
QUOTAS = {"python": 4, "r": 2, "c_cpp": 2, "other_supported_language": 2, "other": 2}


def stratum(language):
    if language == "Python":
        return "python"
    if language == "R":
        return "r"
    if language in ("C", "C++"):
        return "c_cpp"
    if language in ("Go", "Rust", "JavaScript", "TypeScript"):
        return "other_supported_language"
    return "other"


def select():
    summary = json.loads((ROOT / "inventory/live-summary.json").read_text())
    if summary["not_yet_observed"]:
        raise ValueError("Metadata collection is incomplete; do not select a partial panel")
    inputs = [
        json.loads(line)
        for line in (ROOT / "inventory/live-repositories.jsonl").read_text().splitlines()
    ]
    strata = {name: [] for name in QUOTAS}
    excluded = Counter()
    for row in inputs:
        meta = row["metadata"]
        reason = (
            "no_primary_source_mapping" if not row["primary_source_ids"]
            else "archived" if meta["isArchived"]
            else "empty" if meta["isEmpty"]
            else "no_lifetime_merged_pr" if meta["pullRequests"]["totalCount"] == 0
            else None
        )
        if reason:
            excluded[reason] += 1
            continue
        language = (meta["primaryLanguage"] or {}).get("name", "unknown")
        group = stratum(language)
        rank = hashlib.sha256(f"{SEED}:{meta['id']}".encode()).hexdigest()
        strata[group].append({
            "repository": meta["nameWithOwner"], "github_id": meta["id"],
            "primary_language": language, "stratum": group,
            "rank": rank, "lifetime_merged_prs": meta["pullRequests"]["totalCount"],
            "source_ids": row["primary_source_ids"],
        })
    selected = []
    for group, quota in QUOTAS.items():
        selected.extend(sorted(strata[group], key=lambda row: row["rank"])[:quota])
    result = {
        "seed": SEED, "quotas": QUOTAS,
        "population_by_stratum": {group: len(rows) for group, rows in strata.items()},
        "excluded_live_repository_ids": dict(excluded),
        "unresolved_repository_names": summary["unresolved_names"],
        "selected": selected,
        "pr_window": {"since": "2025-10-20", "until": "2026-10-19"},
        "limitations": [
            "Purposefully disproportionate language strata; report within-stratum denominators.",
            "Primary language does not prove runner support or scientific relevance.",
            "No replacement for sampled repositories with no PRs in the frozen window.",
            "Archived, empty, unmapped and zero-lifetime-PR repositories remain in the inventory.",
            "This panel selects repositories for static PR inspection, not guaranteed runnable tasks.",
        ],
    }
    (ROOT / "inventory/repository-panel.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    select()
