"""Freeze the pinned official listing; no model, task repair or replacement PR."""

import dataclasses
import importlib
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from biotasks.generation import resources, source
from biotasks.generation.handoff import local_only
from biotasks.validation.files import json_sha, read_json, require, sha, write_json
from biotasks.validation.planning import UPSTREAM


def freeze(native_config: Path, source_cache: Path, output: Path) -> dict[str, Any]:
    source.verify(source_cache)
    config = read_json(native_config)
    require(config["pipeline"]["name"] == "pr_runtime", "Discovery requires pr_runtime")
    match = re.fullmatch(
        r"https://github.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", config["repo"]["url"]
    )
    require(
        match is not None and config["repo"]["access"] == "public",
        "Pinned public GitHub repo required",
    )
    assert match is not None
    owner, name = match.groups()
    options = config["pipeline"]["options"]
    require(
        resources.option_policy().accepts(options)
        and isinstance(options["limit"], int)
        and not isinstance(options["limit"], bool)
        and 1 <= options["limit"] <= 100,
        "Discovery bound is 1..100",
    )
    binding = {
        "native_config_sha256": sha(native_config),
        "source_receipt_sha256": sha(source_cache / "receipt.json"),
    }
    if output.exists():
        existing = read_json(output)
        snapshot = dict(existing)
        require(
            snapshot.pop("snapshot_identity") == json_sha(snapshot),
            "Frozen candidate snapshot changed",
        )
        require(existing["discovery_binding"] == binding, "Frozen discovery inputs changed")
        return existing
    sys.path.insert(0, str(source_cache / "source/src"))
    with local_only():
        native = importlib.import_module("repo2rlenv.github")
    require(
        native.__file__ == str(source_cache / "source/src/repo2rlenv/github.py"),
        "GitHub module came from another source cache",
    )
    # These are the official function's own gh calls/retries, unchanged. Never
    # print or extract auth; operator-approved GH_TOKEN/normal gh auth is used.
    rows = native.list_merged_prs(
        owner,
        name,
        limit=options["limit"],
        since=date.fromisoformat(options["since"]) if options["since"] else None,
        until=date.fromisoformat(options["until"]) if options["until"] else None,
    )
    require(len(rows) <= options["limit"], "Native discovery exceeded declared limit")
    value = {
        "upstream_revision": UPSTREAM,
        "kind": "Unchanged official merged-PR descriptors; not all-history coverage",
        "repo": owner + "/" + name,
        **options,
        "candidates": [dataclasses.asdict(row) for row in rows],
        "discovery_binding": binding,
        "model_calls": 0,
        "remote_jobs": 0,
    }
    value["snapshot_identity"] = json_sha(value)
    write_json(output, value)
    return value
