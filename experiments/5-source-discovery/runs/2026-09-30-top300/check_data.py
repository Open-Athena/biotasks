"""Independent joins of exported CSVs, baseline preservation and artifact integrity."""

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
BASE = STUDY / "baseline/data/top200-2026-09-29"


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def main():
    rankings = rows(HERE / "rankings.csv")
    labels = {r["source_id"]: r for r in rows(HERE / "source-annotations.csv")}
    original = rows(BASE / "rankings-2026-09-29.csv")
    for r in original:
        actual = next(
            x for x in rankings if x["ranking"] == r["ranking"] and x["rank"] == r["rank"]
        )
        assert actual == r, (actual, r)
    assert all(
        labels[r["source_id"]] == r for r in rows(BASE / "source-annotations-2026-09-29.csv")
    )
    assert len(labels) == 1014 and len(rankings) == 1200
    groups = {r["primary_domain"] for r in labels.values()}
    assert len(groups) == 22
    methods = ["bioconda", "bioconductor", "pypi", "github"]
    for m in methods:
        selected = [r for r in rankings if r["ranking"] == m]
        assert [int(r["rank"]) for r in selected] == list(range(1, 301))
        assert len({r["source_id"] for r in selected}) == 300
        assert [(-int(r["score"]), r["source_id"]) for r in selected] == sorted(
            (-int(r["score"]), r["source_id"]) for r in selected
        )
    distributions = rows(HERE / "primary-group-depths.csv")
    assert len(distributions) == 3 * 5 * 22
    for k in [100, 200, 300]:
        cohorts = {
            m: {r["source_id"] for r in rankings if r["ranking"] == m and int(r["rank"]) <= k}
            for m in methods
        }
        cohorts["merged"] = set().union(*cohorts.values())
        for m, ids in cohorts.items():
            expected = Counter(labels[s]["primary_domain"] for s in ids)
            cells = [r for r in distributions if r["cohort"] == m and int(r["depth"]) == k]
            assert {r["primary_group"] for r in cells} == groups
            for r in cells:
                n = expected[r["primary_group"]]
                assert (int(r["count"]), int(r["total"])) == (n, len(ids))
                assert math.isclose(float(r["share"]), n / len(ids), abs_tol=1e-12)
                assert r["band"] == (
                    "0"
                    if not n
                    else "1"
                    if n == 1
                    else "2–5"
                    if n <= 5
                    else "6–10"
                    if n <= 10
                    else ">10"
                )
    html = (HERE / "explorer.html").read_text()
    data = json.loads(re.search(r"window\.BIOTASKS_DATA=(.*?);</script>", html, re.S)[1])
    sources = {r["id"]: r for r in data["sources"]}
    assert len(sources) == 1014
    for r in rankings:
        assert sources[r["source_id"]]["ranks"][r["ranking"]] == dict(
            rank=int(r["rank"]),
            score=int(r["score"]),
            packages=r["packages"],
            rawRank=int(r["first_raw_rank"]),
        )
    for k, r in labels.items():
        assert [sources[k][key] for key in ["type", "domain", "topic", "note"]] == [
            r[key] for key in ["source_type", "primary_domain", "manual_topic", "scope_note"]
        ]
    old = json.loads(
        re.search(
            r"window\.BIOTASKS_DATA=(.*?);</script>",
            (HERE.parent / "2026-09-30-explorer/explorer.html").read_text(),
            re.S,
        )[1]
    )
    assert data["adoption"] == old["adoption"] and data["adoptionPairs"] == old["adoptionPairs"]
    for name in ["analysis-provenance.json", "provenance.json"]:
        p = json.loads((HERE / name).read_text())
        for r in p["inputs"] + p.get("outputs", []):
            assert hashlib.sha256((STUDY / r["path"]).read_bytes()).hexdigest() == r["sha256"], r[
                "path"
            ]
        if "output" in p:
            assert (
                hashlib.sha256((HERE / p["output"]["path"]).read_bytes()).hexdigest()
                == p["output"]["sha256"]
            )
    assert not re.search(r"<script[^>]+src=|<link[^>]+(?:stylesheet|preload)", html)
    assert len(html.encode()) < 1_500_000
    print(
        "PASS: all 800 baseline rows and 672 labels unchanged; 1,200 unique rank positions; 1,014 source identities; all 330 group/count/share/band cells; embedded records; unchanged 95-source adoption data; provenance checksums; standalone HTML."
    )


if __name__ == "__main__":
    main()
