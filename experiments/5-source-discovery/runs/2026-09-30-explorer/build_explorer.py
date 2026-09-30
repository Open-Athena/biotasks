"""Build the offline research explorer from frozen inputs, without network access."""

import csv
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
BASELINE = STUDY / "baseline"
DATE = "2026-09-29"
METHODS = ["bioconda", "bioconductor", "pypi", "github"]


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def assemble():
    directory = BASELINE / "data" / f"top200-{DATE}"
    inputs = [
        directory / f"{name}-{DATE}.{suffix}"
        for name, suffix in [
            ("rankings", "csv"),
            ("source-annotations", "csv"),
            ("source-observations", "json"),
            ("ranking-results", "json"),
            ("expansion-results", "json"),
            ("ranking-provenance", "json"),
        ]
    ] + [BASELINE / "data" / f"adoption-{DATE}.csv", BASELINE / "inventory.json"]
    ranked = read_csv(inputs[0])
    annotations = {row["source_id"]: row for row in read_csv(inputs[1])}
    observations = {row["source_id"]: row for row in json.loads(inputs[2].read_text())}
    assert len(ranked) == 800 and len(annotations) == len(observations) == 672
    assert set(annotations) == set(observations) == {row["source_id"] for row in ranked}
    by_source = {key: {} for key in annotations}
    for method in METHODS:
        rows = [row for row in ranked if row["ranking"] == method]
        assert sorted(int(row["rank"]) for row in rows) == list(range(1, 201))
        assert len({row["source_id"] for row in rows}) == 200
        for row in rows:
            by_source[row["source_id"]][method] = {
                "rank": int(row["rank"]),
                "score": int(row["score"]),
                "packages": row["packages"],
                "rawRank": int(row["first_raw_rank"]),
            }
    records = []
    for key in sorted(annotations):
        label, observation = annotations[key], observations[key]
        github = observation.get("github") or {}
        records.append(
            {
                "id": key,
                "name": github.get("name") or observation["name"],
                "alias": observation["name"],
                "url": observation["source_url"],
                "summary": observation.get("summary", ""),
                "type": label["source_type"],
                "domain": label["primary_domain"],
                "topic": label["manual_topic"],
                "note": label["scope_note"],
                "evidence": observation["evidence_urls"],
                "tags": github.get("topics", []),
                "stars": github.get("stars"),
                "sourceHead": github.get("head"),
                "archived": github.get("archived"),
                "ranks": by_source[key],
            }
        )
    adoption = []
    metric_keys = [
        "bioconda_max_package_downloads",
        "bioconductor_download_score",
        "pypi_max_package_downloads_30d",
        "github_stars",
    ]
    for row in read_csv(inputs[-2]):
        adoption.append(
            {
                "name": row["name"],
                "url": row["repository_url"],
                "values": {
                    method: float(row[key]) if row[key] else None
                    for method, key in zip(METHODS, metric_keys, strict=True)
                },
            }
        )
    analysis = json.loads(inputs[-1].read_text())["adoption_analysis"]
    reverse = dict(zip(metric_keys, METHODS, strict=True))
    adoption_pairs = [
        {
            "first": reverse[row["x"]],
            "second": reverse[row["y"]],
            "n": row["n"],
            "rho": row["spearman_rho"],
        }
        for row in analysis["pairs"]
    ]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    tracked_inputs = inputs + [
        HERE / name
        for name in ("build_explorer.py", "template.html", "explorer.css", "explorer.js")
    ]
    provenance = {
        "checkpoint": revision,
        "main_baseline": "37271415c4c201ba9dbbda66c203caa4050744c3",
        "scope": "Saved-input visualization. No fresh collection or changed annotations.",
        "inputs": [
            {
                "path": str(path.relative_to(STUDY)),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in tracked_inputs
        ],
    }
    data = {
        "sources": records,
        "adoption": adoption,
        "adoptionPairs": adoption_pairs,
        "baselinePairs": json.loads(inputs[3].read_text())["pairs"],
        "expansion": json.loads(inputs[4].read_text())["union_by_depth"],
        "provenance": provenance,
        "snapshot": DATE,
    }
    return data, provenance


def main():
    data, provenance = assemble()
    html = (HERE / "template.html").read_text()
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    encoded = (
        encoded.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    )
    for token, content in [
        ("@@STYLE@@", (HERE / "explorer.css").read_text()),
        ("@@DATA@@", encoded),
        ("@@SCRIPT@@", (HERE / "explorer.js").read_text()),
    ]:
        assert html.count(token) == 1
        html = html.replace(token, content)
    output = HERE / "explorer.html"
    output.write_text(html)
    provenance["output"] = {
        "path": output.name,
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (HERE / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(
        json.dumps(
            {
                "sources": len(data["sources"]),
                "adoption": len(data["adoption"]),
                "checkpoint": provenance["checkpoint"],
                "output": provenance["output"],
            }
        )
    )


if __name__ == "__main__":
    main()
