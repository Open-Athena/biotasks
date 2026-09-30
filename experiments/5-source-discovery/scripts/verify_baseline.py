"""Check the imported study offline without rewriting its evidence.

Run under the shared-node resource guard documented in the research README.
This is research validation, not a supported BioTasks CLI command.
"""

import csv
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from analyze_expansion import compare
from analyze_rankings import analyze

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BASELINE = ROOT / "baseline"
DATE = "2026-09-29"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def equivalent(actual, expected, location="root"):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), location
        for key in expected:
            equivalent(actual[key], expected[key], f"{location}.{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), location
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            equivalent(a, b, f"{location}[{i}]")
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), location
    else:
        assert actual == expected, (location, actual, expected)


def average_ranks(values):
    positions = defaultdict(list)
    for i, value in enumerate(sorted(values), 1):
        positions[value].append(i)
    return [statistics.mean(positions[value]) for value in values]


def verify_pair(rows, expected):
    x_key, y_key = expected["x"], expected["y"]
    matched = [r for r in rows if all(r["adoption_metrics"][k] is not None for k in (x_key, y_key))]
    assert expected["n"] == len(matched)
    assert expected["members"] == [r["name"] for r in matched]
    if len(matched) < 3:
        assert all(
            expected[k] is None for k in ("spearman_rho", "pearson_raw_r", "pearson_log1p_r")
        )
        return
    x = [r["adoption_metrics"][x_key] for r in matched]
    y = [r["adoption_metrics"][y_key] for r in matched]
    for key, value in {
        "spearman_rho": statistics.correlation(average_ranks(x), average_ranks(y)),
        "pearson_raw_r": statistics.correlation(x, y),
        "pearson_log1p_r": statistics.correlation(
            [math.log10(1 + v) for v in x], [math.log10(1 + v) for v in y]
        ),
    }.items():
        equivalent(value, expected[key], key)


def main():
    manifest = json.loads((ROOT / "migration.json").read_text())
    checked_files = 0
    for entry in manifest["tracked_delta"] + manifest["recovered_local_scripts"]:
        if entry["disposition"] == "migrated":
            assert digest(REPO / entry["destination"]) == entry["destination_sha256"], entry[
                "destination"
            ]
            checked_files += 1

    # Keep historical hashes as historical evidence; separately identify hashes
    # superseded by the source branch's recorded September 30 corrections.
    historical_mismatches = []
    expansion_provenance = json.loads(
        (BASELINE / f"data/top200-{DATE}/ranking-provenance-{DATE}.json").read_text()
    )
    mapped_paths = {
        e["source_path"]: e for e in manifest["tracked_delta"] if e["disposition"] == "migrated"
    }
    for group in (
        expansion_provenance["baseline_artifact_sha256"],
        expansion_provenance["analysis_implementation"]["script_sha256"],
    ):
        for source_path, expected in group.items():
            actual = mapped_paths[source_path]["source_sha256"]
            if expected != actual:
                historical_mismatches.append(
                    {
                        "source_path": source_path,
                        "historical_sha256": expected,
                        "imported_source_sha256": actual,
                    }
                )

    for size, data in ((100, BASELINE / "data"), (200, BASELINE / f"data/top200-{DATE}")):
        result = analyze(data, DATE, size)
        equivalent(
            result.summary,
            json.loads((data / f"ranking-results-{DATE}.json").read_text()),
            f"top{size}",
        )
        with (data / f"ranking-topic-frequencies-{DATE}.csv").open(newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ["tag", "mapped_domain", "bioconda", "bioconductor", "pypi", "github"]
        assert rows[1:] == [[str(v) for v in row] for row in result.tag_frequency_rows]
        provenance = json.loads((data / f"ranking-provenance-{DATE}.json").read_text())
        assert digest(BASELINE / "inventory.json") == provenance["original_95_inventory_sha256"]
    equivalent(
        compare(BASELINE / "data", BASELINE / f"data/top200-{DATE}", DATE),
        json.loads((BASELINE / f"data/top200-{DATE}/expansion-results-{DATE}.json").read_text()),
        "expansion",
    )

    inventory = json.loads((BASELINE / "inventory.json").read_text())
    rows = inventory["candidates"]
    adoption = inventory["adoption_analysis"]
    assert len(rows) == len({r["name"] for r in rows}) == 95
    for row in rows:
        metrics = row["adoption_metrics"]
        assert row["execution_status"] == "not run"
        for packages, field, max_key, sum_key in (
            (
                row["bioconda_packages"],
                "cumulative_downloads",
                "bioconda_max_package_downloads",
                "bioconda_sum_package_downloads",
            ),
            (
                row["pypi_packages"],
                "downloads_30d",
                "pypi_max_package_downloads_30d",
                "pypi_sum_package_downloads_30d",
            ),
        ):
            values = [p[field] for p in packages]
            assert metrics[max_key] == (max(values) if values else None)
            assert metrics[sum_key] == (sum(values) if values else None)
        assert metrics["bioconductor_download_score"] == row["bioconductor_download_score"]
        github = row.get("github_metadata")
        assert metrics["github_stars"] == (github["stargazers_count"] if github else None)
        assert metrics["pypi_max_package_downloads_90d"] == max(
            (p["downloads_90d"] for p in row["pypi_packages"]), default=None
        )
        for package in row["pypi_packages"]:
            daily = package["daily_downloads"]
            recent = [
                v
                for day, v in daily.items()
                if package["window_start"] <= day <= package["window_end"]
            ]
            assert len(daily) == 90 and len(recent) == 30
            assert sum(daily.values()) == package["downloads_90d"]
            assert sum(recent) == package["downloads_30d"]
    for key, count in adoption["coverage"].items():
        assert sum(r["adoption_metrics"][key] is not None for r in rows) == count
    pair_count = 0
    for group in (
        "pairs",
        "sensitivity_summed_package_counters",
        "sensitivity_pypi_90d",
        "sensitivity_single_package_entries",
        "sensitivity_excluding_scientific_libraries",
    ):
        selected = rows
        if group == "sensitivity_single_package_entries":
            selected = [
                r for r in rows if len(r["bioconda_packages"]) <= 1 and len(r["pypi_packages"]) <= 1
            ]
        elif group == "sensitivity_excluding_scientific_libraries":
            selected = [r for r in rows if r["role"] != "scientific library"]
        for pair in adoption[group]:
            verify_pair(selected, pair)
            pair_count += 1
    outlier = adoption["sensitivity_without_largest_pypi_package"]
    selected = [
        r
        for r in rows
        if r["name"] != outlier["excluded"]
        and all(r["adoption_metrics"][k] is not None for k in outlier["pair"])
    ]
    assert len(selected) == outlier["n"]
    x, y = ([r["adoption_metrics"][k] for r in selected] for k in outlier["pair"])
    equivalent(statistics.correlation(x, y), outlier["pearson_raw_r"])
    equivalent(statistics.correlation(average_ranks(x), average_ranks(y)), outlier["spearman_rho"])

    table = read_csv(BASELINE / f"data/adoption-{DATE}.csv")
    assert [r["name"] for r in table] == [r["name"] for r in rows]
    for record, row in zip(rows, table, strict=True):
        for key in adoption["coverage"]:
            assert (int(row[key]) if row[key] else None) == record["adoption_metrics"][key]
    topics = inventory["github_topic_analysis"]
    github = [r for r in rows if r.get("github_metadata")]
    counts = Counter(t for r in github for t in set(r["github_metadata"]["topics"]))
    assert len(github) == topics["github_repositories_queried"] == 83
    assert len(counts) == topics["distinct_topics"] == 214
    assert counts.total() == topics["topic_assignments"] == 341
    assert (
        sum(not r["github_metadata"]["topics"] for r in github)
        == topics["repositories_without_topics"]
        == 30
    )
    assert {r["topic"]: r["repository_count"] for r in topics["frequencies"]} == dict(counts)
    for group in topics["search_ideas"]:
        members = [
            r["name"]
            for r in github
            if set(r["github_metadata"]["topics"]) & set(group["observed_topics"])
        ]
        assert group["candidates"] == members and group["repository_count"] == len(members)

    links = 0
    for path in list(BASELINE.glob("*.md")) + list(ROOT.glob("*.md")):
        for target in re.findall(r"\]\(([^\s)]+)\)", path.read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            linked = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert linked.exists(), (str(path), target)
            if url.fragment and linked.suffix == ".md":
                headings = re.findall(r"^#+\s+(.+)$", linked.read_text(), flags=re.M)
                anchors = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}
                assert unquote(url.fragment) in anchors, (str(path), target)
            links += 1

    print(
        json.dumps(
            {
                "status": "passed",
                "python": sys.version.split()[0],
                "migrated_file_hashes_checked": checked_files,
                "ranking_positions_reproduced": {"top100": 400, "top200": 800},
                "expansion_reproduced": True,
                "adoption_pairs_recomputed": pair_count,
                "outlier_sensitivity_recomputed": True,
                "adoption_export_checked": 95,
                "topic_counts_checked": True,
                "local_links_checked": links,
                "historical_hashes_differing_from_imported_revision": historical_mismatches,
                "limits": [
                    "No fresh provider collection or upstream response verification.",
                    "Figures preserved by hash; not regenerated.",
                    "Source eligibility and manual labels retained, not independently re-reviewed.",
                    "Floating results compared at 1e-12 absolute/relative tolerance; identities and counts compared exactly.",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
