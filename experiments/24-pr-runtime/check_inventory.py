"""Validate joins and accounting against loaded inputs rather than fixed counts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "inventory"


def read_rows(name):
    return [json.loads(line) for line in (ROOT / name).read_text().splitlines()]


def check():
    sources = read_rows("sources.jsonl")
    repositories = read_rows("repositories.jsonl")
    source_ids = {row["source_id"] for row in sources}
    assert len(source_ids) == len(sources), "Duplicate source identity"
    by_name = {row["repository"]: row for row in repositories}
    assert len(by_name) == len(repositories), "Duplicate historical repository"
    for source in sources:
        if source["repository"]:
            assert source["source_id"] in by_name[source["repository"]]["primary_source_ids"]
    primary_pairs = {
        (row["source_id"], row["repository"]) for row in sources if row["repository"]
    }
    assert primary_pairs == {
        (source, row["repository"])
        for row in repositories for source in row["primary_source_ids"]
    }, "Primary source mapping changed across ledgers"
    live = read_rows("live-repositories.jsonl")
    unresolved = read_rows("unresolved-repositories.jsonl")
    observed = [name for row in live for name in row["requested_names"]]
    observed.extend(row["repository"] for row in unresolved)
    assert len(set(observed)) == len(observed), "Duplicate live disposition"
    assert set(observed) == set(by_name), "Missing or extra live disposition"
    assert len({row["metadata"]["id"] for row in live}) == len(live)
    for row in live:
        expected = {
            source for name in row["requested_names"]
            for source in by_name[name]["primary_source_ids"]
        }
        assert set(row["primary_source_ids"]) == expected, "Lost primary mapping on alias merge"
    panel = json.loads((ROOT / "repository-panel.json").read_text())
    selected = panel["selected"]
    assert len({row["github_id"] for row in selected}) == len(selected)
    by_id = {row["metadata"]["id"]: row for row in live}
    for row in selected:
        original = by_id[row["github_id"]]
        assert original["primary_source_ids"], "Linked-only repository selected"
        assert not original["metadata"]["isArchived"]
        assert not original["metadata"]["isEmpty"]
        assert original["metadata"]["pullRequests"]["totalCount"] > 0
    for group, quota in panel["quotas"].items():
        assert sum(row["stratum"] == group for row in selected) == min(
            quota, panel["population_by_stratum"][group]
        )
    print("PASS: source joins, alias identity accounting, complete dispositions and panel membership")


if __name__ == "__main__":
    check()
