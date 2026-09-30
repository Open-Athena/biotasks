"""Check the generated explorer against the frozen source tables and reports."""

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent.parent / "baseline"
TOP = BASELINE / "data/top200-2026-09-29"


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    html = (HERE / "explorer.html").read_text()
    match = re.search(
        r'<script id="research-data">window\.BIOTASKS_DATA=(.*?);</script>', html, re.S
    )
    data = json.loads(match.group(1))
    sources = {r["id"]: r for r in data["sources"]}
    assert len(sources) == len(data["sources"]) == 672
    annotations = {r["source_id"]: r for r in rows(TOP / "source-annotations-2026-09-29.csv")}
    observations = {
        r["source_id"]: r
        for r in json.loads((TOP / "source-observations-2026-09-29.json").read_text())
    }
    ranking_rows = rows(TOP / "rankings-2026-09-29.csv")
    assert sum(len(r["ranks"]) for r in sources.values()) == len(ranking_rows) == 800
    for row in ranking_rows:
        record = sources[row["source_id"]]["ranks"][row["ranking"]]
        assert record == {
            "rank": int(row["rank"]),
            "score": int(row["score"]),
            "packages": row["packages"],
            "rawRank": int(row["first_raw_rank"]),
        }
    for key, record in sources.items():
        annotation, observation = annotations[key], observations[key]
        assert (record["type"], record["domain"], record["topic"], record["note"]) == tuple(
            annotation[x] for x in ("source_type", "primary_domain", "manual_topic", "scope_note")
        )
        assert record["url"] == observation["source_url"]
        assert record["summary"] == observation.get("summary", "")
        assert record["evidence"] == observation["evidence_urls"]
        assert record["stars"] == (observation.get("github") or {}).get("stars")
    expected = json.loads((TOP / "ranking-results-2026-09-29.json").read_text())
    for method, result in expected["rankings"].items():
        selected = [r for r in sources.values() if method in r["ranks"]]
        assert dict(Counter(r["type"] for r in selected)) == result["source_types"]
        assert dict(Counter(r["domain"] for r in selected)) == result["domains"]
    for depth, result in data["expansion"].items():
        selected = [
            r for r in sources.values() if any(x["rank"] <= int(depth) for x in r["ranks"].values())
        ]
        assert len(selected) == result["n"]
        assert len({r["topic"] for r in selected}) == result["manual_topic_bins"]
        assert len({r["domain"] for r in selected}) == result["domain_bins"]
    assert len(data["adoption"]) == 95
    expected_adoption = rows(BASELINE / "data/adoption-2026-09-29.csv")
    keys = {
        "bioconda": "bioconda_max_package_downloads",
        "bioconductor": "bioconductor_download_score",
        "pypi": "pypi_max_package_downloads_30d",
        "github": "github_stars",
    }
    for actual, original in zip(data["adoption"], expected_adoption, strict=True):
        assert actual["name"] == original["name"]
        for method, field in keys.items():
            assert actual["values"][method] == (float(original[field]) if original[field] else None)
    provenance = json.loads((HERE / "provenance.json").read_text())
    for item in provenance["inputs"]:
        assert (
            hashlib.sha256((HERE.parent.parent / item["path"]).read_bytes()).hexdigest()
            == item["sha256"]
        )
    assert (
        hashlib.sha256((HERE / "explorer.html").read_bytes()).hexdigest()
        == provenance["output"]["sha256"]
    )
    assert len(html.encode()) < 1_000_000
    assert not re.search(r"<script[^>]+src=|<link[^>]+(?:stylesheet|preload)", html)
    print(
        "PASS: 672 source identities, 800 rank/score/package records, all annotations and source links."
    )
    print(
        "PASS: every per-list domain/type count and saved expansion cutoff; all 95 adoption observations and nulls."
    )
    print("PASS: build input/output checksums, embedded scripts/styles, HTML under 1 MB.")


if __name__ == "__main__":
    main()
