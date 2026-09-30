"""Build the self-contained top-300 explorer from reviewed exported tables."""

import csv
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
BASE = STUDY / "baseline"
METHODS = ["bioconda", "bioconductor", "pypi", "github"]


def csv_rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def main():
    ranks = {}
    for row in csv_rows(HERE / "rankings.csv"):
        ranks.setdefault(row["source_id"], {})[row["ranking"]] = dict(
            rank=int(row["rank"]),
            score=int(row["score"]),
            packages=row["packages"],
            rawRank=int(row["first_raw_rank"]),
        )
    labels = {r["source_id"]: r for r in csv_rows(HERE / "source-annotations.csv")}
    records = []
    for r in json.loads((HERE / "source-observations.json").read_text()):
        label = labels[r["source_id"]]
        gh = r.get("github") or {}
        records.append(
            dict(
                id=r["source_id"],
                name=gh.get("name") or r["name"],
                alias=r["name"],
                url=r["source_url"],
                summary=r.get("summary", ""),
                type=label["source_type"],
                domain=label["primary_domain"],
                topic=label["manual_topic"],
                note=label["scope_note"],
                evidence=r["evidence_urls"],
                tags=gh.get("topics", []),
                stars=gh.get("stars"),
                sourceHead=gh.get("head"),
                archived=gh.get("archived"),
                ranks=ranks[r["source_id"]],
            )
        )
    metric_keys = [
        "bioconda_max_package_downloads",
        "bioconductor_download_score",
        "pypi_max_package_downloads_30d",
        "github_stars",
    ]
    adoption = [
        dict(
            name=r["name"],
            url=r["repository_url"],
            values={
                m: float(r[k]) if r[k] else None for m, k in zip(METHODS, metric_keys, strict=True)
            },
        )
        for r in csv_rows(BASE / "data/adoption-2026-09-29.csv")
    ]
    reverse = dict(zip(metric_keys, METHODS, strict=True))
    adoption_pairs = [
        dict(first=reverse[r["x"]], second=reverse[r["y"]], n=r["n"], rho=r["spearman_rho"])
        for r in json.loads((BASE / "inventory.json").read_text())["adoption_analysis"]["pairs"]
    ]
    result = json.loads((HERE / "results.json").read_text())
    inputs = [
        HERE / n
        for n in [
            "rankings.csv",
            "source-annotations.csv",
            "source-observations.json",
            "results.json",
            "analysis-provenance.json",
            "build_explorer.py",
            "template.html",
            "explorer.js",
            "explorer.css",
        ]
    ] + [BASE / "inventory.json", BASE / "data/adoption-2026-09-29.csv"]
    provenance = dict(
        checkpoint=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        main_baseline="37271415c4c201ba9dbbda66c203caa4050744c3",
        scope="Depth expansion using preserved numerical snapshots; original first-200 IDs, scores and labels unchanged. New identity metadata and labels recorded separately.",
        inputs=[
            dict(
                path=str(p.relative_to(STUDY)),
                bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            )
            for p in inputs
        ],
    )
    data = dict(
        sources=records,
        adoption=adoption,
        adoptionPairs=adoption_pairs,
        expansion=result["union_by_depth"],
        depthResults=result,
        provenance=provenance,
        snapshot="2026-09-29 numerical snapshot; 2026-09-30 depth expansion",
    )
    encoded = (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    html = (HERE / "template.html").read_text()
    for token, value in [
        ("@@STYLE@@", (HERE / "explorer.css").read_text()),
        ("@@SCRIPT@@", (HERE / "explorer.js").read_text()),
        ("@@DATA@@", encoded),
        ("@@COUNT@@", f"{len(records):,}"),
        ("@@TOPICS@@", str(len({r["topic"] for r in records}))),
    ]:
        assert token in html
        html = html.replace(token, value)
    assert "@@" not in html
    path = HERE / "explorer.html"
    path.write_text(html)
    provenance["output"] = dict(
        path=path.name,
        bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    (HERE / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                sources=len(records),
                ranking_positions=sum(len(r["ranks"]) for r in records),
                output=provenance["output"],
            )
        )
    )


if __name__ == "__main__":
    main()
