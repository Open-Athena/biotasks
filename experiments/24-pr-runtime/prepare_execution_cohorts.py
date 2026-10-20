"""Freeze development/evaluation membership before inspecting task-specific failures."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = "biotasks24-runtime-cohort-v1"


def prepare():
    panel = json.loads((ROOT / "inventory/repository-panel.json").read_text())
    selected = {
        (cohort["repository"], row["number"]): row
        for path in (ROOT / "inventory/pr-cohorts").glob("*.json")
        for cohort in [json.loads(path.read_text())]
        for row in cohort["selected"]
    }
    static = [
        json.loads(line)
        for line in (ROOT / "inventory/static-assessment.jsonl").read_text().splitlines()
    ]
    eligible = [r for r in static if r["disposition"] == "statically_eligible"]
    by_repo = {}
    for row in eligible:
        original = selected[row["repository"], row["number"]]
        item = {
            "repository": row["repository"], "number": row["number"],
            "base_sha": original["baseRefOid"], "head_sha": original["headRefOid"],
            "merge_sha": original["mergeCommit"]["oid"],
            "url": original["url"],
            "diff_path": row["diff_evidence"],
            "diff_sha256": hashlib.sha256((ROOT / row["diff_evidence"]).read_bytes()).hexdigest(),
            "rank": hashlib.sha256(
                f"{SEED}:{row['repository']}:{row['number']}".encode()
            ).hexdigest(),
        }
        by_repo.setdefault(row["repository"], []).append(item)
    development_repositories = set(
        sorted(by_repo, key=lambda repo: (-len(by_repo[repo]), repo))[:2]
    )
    result = {
        "seed": SEED, "window": panel["pr_window"],
        "rule": (
            "Select the two repositories with most statically eligible PRs, breaking ties "
            "lexically, for development. Their first two SHA-ranked eligible PRs are "
            "development; all remaining inputs are held out. Other repositories are "
            "held out at repository level."
        ),
        "development_repositories": sorted(development_repositories),
        "previous_experiment_repositories": [
            "biopython/biopython", "scikit-bio/scikit-bio", "arq5x/bedtools2", "thelovelab/DESeq2",
        ],
        "cohorts": [],
        "execution_started": False,
        "evaluation_configuration_frozen": False,
    }
    for repo, rows in sorted(by_repo.items()):
        for i, row in enumerate(sorted(rows, key=lambda r: r["rank"])):
            row["cohort"] = (
                "development" if repo in development_repositories and i < 2
                else "held_out"
            )
            row["repository_role"] = (
                "configured_on_development" if repo in development_repositories
                else "unseen_repository"
            )
            result["cohorts"].append(row)
    identities = [(r["repository"], r["number"]) for r in result["cohorts"]]
    assert len(identities) == len(set(identities)) == len(eligible)
    assert all(
        r["repository"].lower() not in {p.lower() for p in result["previous_experiment_repositories"]}
        for r in result["cohorts"]
    )
    (ROOT / "execution-cohorts.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "development": [f"{r['repository']}#{r['number']}" for r in result["cohorts"] if r["cohort"] == "development"],
        "held_out_count": sum(r["cohort"] == "held_out" for r in result["cohorts"]),
        "unseen_repository_held_out_count": sum(r["repository_role"] == "unseen_repository" for r in result["cohorts"]),
    }, indent=2))


if __name__ == "__main__":
    prepare()
