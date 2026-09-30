"""Export the reviewed depth comparison with explicit per-cohort denominators."""

import csv
import hashlib
import itertools
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
METHODS = ["bioconda", "bioconductor", "pypi", "github"]


def read_csv(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(name, rows):
    with (HERE / name).open("w") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def band(n):
    return "0" if n == 0 else "1" if n == 1 else "2–5" if n <= 5 else "6–10" if n <= 10 else ">10"


def correlation(a, b):
    n = len(a)
    if n < 3:
        return None

    # Unique list rank positions are reranked within the intersection.
    def ranks(values):
        indices = sorted(range(n), key=lambda i: values[i])
        out = [0] * n
        for rank, i in enumerate(indices):
            out[i] = rank
        return out

    x, y = ranks(a), ranks(b)
    mid = (n - 1) / 2
    denom = math.sqrt(sum((v - mid) ** 2 for v in x) * sum((v - mid) ** 2 for v in y))
    return sum((u - mid) * (v - mid) for u, v in zip(x, y, strict=True)) / denom if denom else None


def main():
    data = json.loads((HERE / "provisional.json").read_text())
    annotations = {r["source_id"]: r for r in read_csv(HERE / "source-annotations.csv")}
    rankings = [
        dict(
            ranking=m,
            rank=r["rank"],
            source_id=r["source_id"],
            score=r["score"],
            packages=";".join(r["packages"]),
            first_raw_rank=r["first_raw_rank"],
        )
        for m, rows in data["cohorts"].items()
        for r in rows
    ]
    # Independent published baseline, not the provisional cache used by prepare.py.
    old = read_csv(STUDY / "baseline/data/top200-2026-09-29/rankings-2026-09-29.csv")
    for m in METHODS:
        current = [r for r in rankings if r["ranking"] == m]
        assert len(current) == len({r["source_id"] for r in current}) == 300
        assert [(r["source_id"], r["score"]) for r in current[:200]] == [
            (r["source_id"], int(r["score"])) for r in old if r["ranking"] == m
        ]
    write_csv("rankings.csv", rankings)
    for r in data["sources"]:
        gh = r.get("github")
        if gh and "nameWithOwner" in gh:
            branch = gh.get("defaultBranchRef") or {}
            r["github"] = dict(
                name=gh["nameWithOwner"],
                url=gh["url"],
                stars=gh["stargazerCount"],
                archived=gh["isArchived"],
                fork=gh["isFork"],
                head=(branch.get("target") or {}).get("oid"),
                topics=[n["topic"]["name"] for n in gh["repositoryTopics"]["nodes"]],
            )
    dump("source-observations.json", data["sources"])
    groups = sorted({r["primary_domain"] for r in annotations.values()})
    assert len(groups) == 22, "Review any ontology extension explicitly."
    depths = {}
    distributions, pairs, expansion = [], [], {}
    for k in [10, 25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300]:
        ids = {m: {r["source_id"] for r in data["cohorts"][m] if r["rank"] <= k} for m in METHODS}
        ids["merged"] = set().union(*ids.values())
        expansion[str(k)] = dict(
            n=len(ids["merged"]),
            domain_bins=len({annotations[s]["primary_domain"] for s in ids["merged"]}),
            manual_topic_bins=len({annotations[s]["manual_topic"] for s in ids["merged"]}),
        )
        if k not in [100, 200, 300]:
            continue
        depths[k] = {}
        for m, members in ids.items():
            counts = Counter(annotations[s]["primary_domain"] for s in members)
            counts = {g: counts[g] for g in groups}
            types = dict(Counter(annotations[s]["source_type"] for s in members))
            depths[k][m] = dict(
                n=len(members),
                counts=counts,
                types=types,
                bands=dict(Counter(band(v) for v in counts.values())),
            )
            for g, count in counts.items():
                distributions.append(
                    dict(
                        depth=k,
                        cohort=m,
                        primary_group=g,
                        count=count,
                        total=len(members),
                        share=count / len(members),
                        band=band(count),
                    )
                )
        for a, b in itertools.combinations(METHODS, 2):
            shared = sorted(ids[a] & ids[b])
            ranks = {m: {r["source_id"]: r["rank"] for r in data["cohorts"][m]} for m in [a, b]}
            pairs.append(
                dict(
                    depth=k,
                    first=a,
                    second=b,
                    n_shared=len(shared),
                    jaccard=len(shared) / len(ids[a] | ids[b]),
                    spearman_rho=correlation(
                        [ranks[a][s] for s in shared], [ranks[b][s] for s in shared]
                    ),
                )
            )
    fixed = {}
    for m in [*METHODS, "merged"]:
        at100 = depths[100][m]["counts"]
        fixed[m] = dict(
            tail_at_100=[g for g in groups if 1 <= at100[g] <= 5],
            absent_at_100=[g for g in groups if not at100[g]],
            newly_at_200=[g for g in groups if not at100[g] and depths[200][m]["counts"][g]],
            newly_at_300=[g for g in groups if not at100[g] and depths[300][m]["counts"][g]],
        )
    write_csv("primary-group-depths.csv", distributions)
    write_csv("rank-correlations.csv", pairs)
    results = dict(
        groups=groups,
        depths=depths,
        fixed=fixed,
        pairs=pairs,
        union_by_depth=expansion,
        annotation_method="Assistant manual metadata review with selected README checks; not independently human-validated.",
        definitions=dict(
            bands=["0", "1", "2–5", "6–10", ">10"],
            fixed_tail="Groups with 1–5 sources in this cohort at top 100; membership fixed at later depths.",
            newly_represented="Groups absent at top 100, positive at the indicated later depth.",
            denominator="Each route has exactly depth sources; merged counts distinct canonical source identities once.",
        ),
    )
    dump("results.json", results)
    inputs = [
        HERE / n
        for n in [
            "prepare.py",
            "annotate.py",
            "analyze.py",
            "decisions.json",
            "imported-inputs.json",
            "github-identities.json",
            "additional-bioconda.json",
            "source-annotations.csv",
        ]
    ] + sorted((HERE / "metadata").glob("*.json"))
    outputs = [
        HERE / n
        for n in [
            "rankings.csv",
            "source-observations.json",
            "primary-group-depths.csv",
            "rank-correlations.csv",
            "results.json",
        ]
    ]

    def inventory(paths):
        return [
            dict(
                path=str(p.relative_to(STUDY)),
                bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            )
            for p in paths
        ]

    dump(
        "analysis-provenance.json",
        dict(
            checkpoint=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            assembly_checkpoint=data["checkpoint"],
            numerical_snapshot="2026-09-29 preserved",
            identity_metadata="2026-09-30 additional metadata; original baseline labels preserved",
            inputs=inventory(inputs),
            outputs=inventory(outputs),
        ),
    )
    print(
        json.dumps(
            dict(
                union=expansion,
                merged_depths={k: depths[k]["merged"] for k in depths},
                fixed_merged=fixed["merged"],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
