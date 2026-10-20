"""Conservatively separate development from overlapping change families.

Shared files indicate potential leakage, not proof of duplicate biological fixes.
This pre-execution audit never consults runtime results or substitutes new inputs.
"""

import hashlib
import itertools
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def references(repository, text):
    found = {
        f"{owner}/{repo}#{number}".lower()
        for owner, repo, number in re.findall(
            r"https://github\.com/([^/\s]+)/([^/\s]+)/(?:issues|pull)/(\d+)", text
        )
    }
    found.update(
        f"{owner}/{repo}#{number}".lower()
        for owner, repo, number in re.findall(r"([\w.-]+)/([\w.-]+)#(\d+)", text)
    )
    found.update(
        f"{repository}#{number}".lower()
        for number in re.findall(r"(?<![\w/])#(\d+)", text)
    )
    return found


def main():
    original_path = ROOT / "execution-cohorts.json"
    original_bytes = original_path.read_bytes()
    original = json.loads(original_bytes)
    assert original["execution_started"] is False
    metadata = {
        (cohort["repository"], row["number"]): row
        for path in (ROOT / "inventory/pr-cohorts").glob("*.json")
        for cohort in [json.loads(path.read_text())]
        for row in cohort["selected"]
    }
    static = {
        (row["repository"], row["number"]): row
        for line in (ROOT / "inventory/static-assessment.jsonl").read_text().splitlines()
        for row in [json.loads(line)]
    }
    nodes = {}
    for row in original["cohorts"]:
        key = row["repository"], row["number"]
        meta = metadata[key]
        raw = (ROOT / row["diff_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["diff_sha256"]
        name = f"{key[0]}#{key[1]}"
        nodes[name] = {
            "repository": key[0], "number": key[1], "title": meta["title"],
            "original_cohort": row["cohort"], "diff_sha256": row["diff_sha256"],
            "source_files": sorted(static[key]["source_files"]),
            "references": sorted(references(key[0], meta["title"] + "\n" + meta["body"])),
        }
    edges = []
    neighbours = {name: set() for name in nodes}
    for (left, a), (right, b) in itertools.combinations(sorted(nodes.items()), 2):
        same_repo = a["repository"].lower() == b["repository"].lower()
        files = sorted(set(a["source_files"]) & set(b["source_files"])) if same_repo else []
        refs = sorted(set(a["references"]) & set(b["references"]))
        identical = a["diff_sha256"] == b["diff_sha256"]
        if files or refs or identical:
            edges.append({
                "left": left, "right": right, "shared_source_files": files,
                "shared_references": refs, "identical_full_diff": identical,
            })
            neighbours[left].add(right)
            neighbours[right].add(left)
    groups = []
    unseen = set(nodes)
    while unseen:
        todo = [min(unseen)]
        members = set()
        while todo:
            name = todo.pop()
            if name not in members:
                members.add(name)
                todo.extend(neighbours[name] - members)
        unseen -= members
        groups.append({
            "id": hashlib.sha256("\n".join(sorted(members)).encode()).hexdigest()[:16],
            "members": sorted(members),
            "contains_development": any(
                nodes[name]["original_cohort"] == "development" for name in members
            ),
        })
    assignment = {name: group for group in groups for name in group["members"]}
    revised = json.loads(original_bytes)
    revised["version"] = 2
    revised["supersedes"] = {
        "path": original_path.name, "sha256": hashlib.sha256(original_bytes).hexdigest(),
    }
    revised["overlap_policy"] = (
        "Conservative connected components of shared source paths in the same repository, "
        "shared issue/PR references, or identical diffs. Keep development members. "
        "Exclude original held-out members in components containing development. "
        "No replacement candidates; original denominators remain visible."
    )
    for row in revised["cohorts"]:
        name = f"{row['repository']}#{row['number']}"
        group = assignment[name]
        row["overlap_group"] = group["id"]
        row["original_cohort"] = row["cohort"]
        if row["cohort"] == "held_out" and group["contains_development"]:
            row["cohort"] = "excluded_development_overlap"
    audit = {
        "stage": "pre_execution_metadata_audit",
        "nodes": nodes, "edges": edges, "groups": groups,
        "limitations": [
            "Shared-file components are conservative leakage groups, not proven duplicate fixes.",
            "References are extracted from PR descriptions; absent references do not prove independence.",
            "Cross-repository semantic duplication is not resolved by this structural screen.",
            "Previous experiment repositories are disjoint, which does not prove semantic novelty.",
            "Per-task acceptance and runtime quality have not been assessed.",
        ],
    }
    dev_groups = {r["overlap_group"] for r in revised["cohorts"] if r["cohort"] == "development"}
    evaluation_groups = {r["overlap_group"] for r in revised["cohorts"] if r["cohort"] == "held_out"}
    assert not dev_groups & evaluation_groups
    (ROOT / "execution-cohorts-v2.json").write_text(json.dumps(revised, indent=2) + "\n")
    (ROOT / "evidence/cohort-overlap-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({
        "groups": len(groups),
        "development": sum(r["cohort"] == "development" for r in revised["cohorts"]),
        "held_out": [f"{r['repository']}#{r['number']}" for r in revised["cohorts"] if r["cohort"] == "held_out"],
        "excluded_development_overlap": [
            f"{r['repository']}#{r['number']}" for r in revised["cohorts"]
            if r["cohort"] == "excluded_development_overlap"
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
