"""Report complete window counts and bounded static sample estimates."""

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - half), min(1, center + half)]


def summarize():
    counts = [
        json.loads(line)
        for line in (ROOT / "inventory/window-counts.jsonl").read_text().splitlines()
    ]
    live = [
        json.loads(line)
        for line in (ROOT / "inventory/live-repositories.jsonl").read_text().splitlines()
    ]
    assert {r["github_id"] for r in counts} == {r["metadata"]["id"] for r in live}
    assert len({r["github_id"] for r in counts}) == len(counts)
    primary = [row for row in counts if row["primary_source"]]
    language_totals = Counter()
    language_active_repos = Counter()
    for row in primary:
        language = row["primary_language"] or "unknown"
        language_totals[language] += row["merged_pr_count"]
        language_active_repos[language] += row["merged_pr_count"] > 0
    static = [
        json.loads(line)
        for line in (ROOT / "inventory/static-assessment.jsonl").read_text().splitlines()
    ]
    panels = []
    for path in sorted((ROOT / "inventory/pr-cohorts").glob("*.json")):
        cohort = json.loads(path.read_text())
        rows = [r for r in static if r["repository"] == cohort["repository"]]
        assert len(rows) == len(cohort["selected"])
        census = next(r for r in counts if r["repository"] == cohort["repository"])
        assert census["merged_pr_count"] == cohort["merged_pr_count"]
        summary = Counter(row["disposition"] for row in rows)
        n, k = len(rows), summary["statically_eligible"]
        unresolved = sum(v for key, v in summary.items() if key.startswith("unresolved"))
        if n == cohort["merged_pr_count"]:
            estimate = {
                "method": "census within this repository/window",
                "candidate_count_bounds": [k, k + unresolved],
            }
        else:
            # The repository is the inference boundary. Do not pool across strata.
            interval = wilson(k, n)
            upper_interval = wilson(k + unresolved, n)
            estimate = {
                "method": "within-repository hash sample; approximate Wilson 95% interval",
                "estimated_candidate_count": k / n * cohort["merged_pr_count"] if n else None,
                "candidate_count_interval": [
                    interval[0] * cohort["merged_pr_count"],
                    upper_interval[1] * cohort["merged_pr_count"],
                ] if interval else None,
                "interval_note": (
                    "Binomial approximation without finite-population correction; "
                    "upper endpoint allows unresolved inputs to be eligible."
                ),
            }
        panels.append({
            "repository": cohort["repository"], "window_merged_prs": cohort["merged_pr_count"],
            "sampled": n, "statically_eligible": k, "unresolved": unresolved,
            "dispositions": dict(summary), "estimate": estimate,
        })
    result = {
        "window": json.loads((ROOT / "inventory/repository-panel.json").read_text())["pr_window"],
        "all_live_repositories": len(counts),
        "all_live_window_merged_prs": sum(r["merged_pr_count"] for r in counts),
        "primary_source_repositories": len(primary),
        "primary_repositories_with_window_prs": sum(r["merged_pr_count"] > 0 for r in primary),
        "primary_window_merged_prs": sum(r["merged_pr_count"] for r in primary),
        "primary_window_prs_by_language": dict(language_totals.most_common()),
        "primary_active_repositories_by_language": dict(language_active_repos.most_common()),
        "panel": panels,
        "limitations": [
            "Static eligibility is not executable task suitability or automatic acceptance.",
            "No whole-inventory task-yield estimate is established by this small panel.",
            "Primary language is not a native test-runner compatibility verdict.",
            "Counts omit the unresolved historical repository and sources without primary GitHub mappings.",
            "Search counts are individually timestamped observations; the historical window is fixed.",
        ],
    }
    (ROOT / "inventory/opportunity-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        key: value for key, value in result.items()
        if key not in ("panel", "primary_window_prs_by_language", "primary_active_repositories_by_language")
    }, indent=2))


if __name__ == "__main__":
    summarize()
