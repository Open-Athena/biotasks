"""Recover the frozen #5/#16 source and repository denominators without downloads."""

import csv
import hashlib
import io
import json
import subprocess
from collections import Counter
from pathlib import Path

REVISION = "09e375e2dd5a2d1e055ef2e78efe778f636b9311"
ROOT = Path(__file__).resolve().parent
PREFIX = "experiments/16-analysis-discovery/reassessment/"
INPUTS = {
    "sources": PREFIX + "source-counts.csv",
    "repositories": PREFIX + "repository-counts.csv",
    "aliases": PREFIX + "repository-alias-evidence.json",
    "readmes": (
        "experiments/5-classification-pilot/full-inventory/"
        "repository-acquisition.jsonl"
    ),
}


def canonical(repo, aliases):
    repo = repo.lower().strip().removeprefix("https://github.com/").rstrip("/")
    seen = set()
    while repo in aliases:
        if repo in seen:
            raise ValueError(f"Alias cycle: {repo}")
        seen.add(repo)
        repo = aliases[repo]
    return repo


def prepare():
    raw = {
        key: subprocess.check_output(["git", "show", f"{REVISION}:{path}"])
        for key, path in INPUTS.items()
    }
    aliases = {}
    for row in json.loads(raw["aliases"]):
        old = row["requested_url"].split("/repos/")[1].split("/git/")[0].lower()
        new = row["canonical_tree_url"].split("/repos/")[1].split("/git/")[0].lower()
        if old != new:
            if old in aliases and aliases[old] != new:
                raise ValueError(f"Conflicting alias: {old}")
            aliases[old] = new
    sources = list(csv.DictReader(io.StringIO(raw["sources"].decode())))
    repositories = list(csv.DictReader(io.StringIO(raw["repositories"].decode())))
    readmes = [json.loads(line) for line in raw["readmes"].splitlines()]
    ledger = {}

    def add(repo, origin, source_ids=()):
        name = canonical(repo, aliases)
        if len(name.split("/")) != 2 or any(not part for part in name.split("/")):
            raise ValueError(f"Unexpected GitHub repository identity: {repo!r}")
        row = ledger.setdefault(name, {
            "repository": name, "historical_names": set(), "origins": set(),
            "source_ids": set(), "primary_source_ids": set(),
            "live_metadata_status": "not_fetched",
        })
        row["historical_names"].add(repo)
        row["origins"].add(origin)
        row["source_ids"].update(source_ids)
        return row

    for row in repositories:
        add(row["repository"], "repository_counts", json.loads(row["source_ids"]))
    for row in readmes:
        add(row["repository"], "readme_acquisition")
    source_ledger = []
    for row in sources:
        repo = row["repo"]
        entry = {"source_id": row["source_id"], "original_repository": repo}
        if repo:
            mapped = add(repo, "primary_source_mapping", [row["source_id"]])
            mapped["primary_source_ids"].add(row["source_id"])
            entry.update(repository=mapped["repository"], disposition="mapped_github")
        else:
            entry.update(repository=None, disposition="no_primary_repository_mapping")
        source_ledger.append(entry)
    rows = [
        {key: sorted(value) if isinstance(value, set) else value
         for key, value in row.items()}
        for _, row in sorted(ledger.items())
    ]
    summary = {
        "source_revision": REVISION,
        "inputs": {
            key: {"path": INPUTS[key], "bytes": len(value),
                  "sha256": hashlib.sha256(value).hexdigest()}
            for key, value in raw.items()
        },
        "source_rows": len(sources),
        "source_dispositions": dict(Counter(r["disposition"] for r in source_ledger)),
        "repository_count_rows": len(repositories),
        "readme_rows": len(readmes),
        "unique_github_repository_names_after_historical_aliases": len(rows),
        "repositories_with_primary_source_mapping": sum(
            bool(r["primary_source_ids"]) for r in rows
        ),
        "historical_aliases": aliases,
        "limitations": [
            "Historical aliases only; live repository IDs have not been reconciled.",
            "Missing primary mappings are not claims that GitHub repositories do not exist.",
            "Linked tutorial repositories remain distinct from primary source repositories.",
            "No PR eligibility, executable validation or task yield has been measured.",
        ],
    }
    out = ROOT / "inventory"
    out.mkdir(exist_ok=True)
    for filename, records in (("repositories.jsonl", rows), ("sources.jsonl", source_ledger)):
        (out / filename).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("inputs", "historical_aliases")}, indent=2))


if __name__ == "__main__":
    prepare()
