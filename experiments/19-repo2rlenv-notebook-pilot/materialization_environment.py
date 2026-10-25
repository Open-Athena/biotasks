"""Bind a worker's installed-answer assessment to executed final task artifacts.

The controller checks identities and applies explicit content-bound declarations;
it never selects an answer file or decides scientific relevance from a match.
"""

import hashlib
import json
import re

from dependency_assets import validate_manifest


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def exclusion_key(item):
    return re.sub(r"[-_.]+", "-", item["distribution"]).lower(), item["path"]


def merge_exclusions(base, additional, *, already_applied=()):
    """Do not restore an earlier removal or replace an observed file identity."""
    base = base or {"files": []}
    validate_manifest(base, require_reason=True)
    validate_manifest({"files": additional}, require_reason=True)
    entries = {exclusion_key(row): row for row in base["files"]}
    for row in additional:
        key = exclusion_key(row)
        if key in entries:
            raise ValueError("Additional exclusion duplicates the frozen base manifest")
        entries[key] = row
    for row in already_applied:
        current = entries.get(exclusion_key(row))
        if current is None or current["sha256"] != row["sha256"]:
            raise ValueError("Cannot undo or change a dependency removal in this session")
    return {"files": [entries[key] for key in sorted(entries)]}


def removal_receipt(manifest):
    return {
        "files": [
            {key: row[key] for key in ("distribution", "path", "sha256")}
            for row in manifest["files"]
        ],
        "excluded_files_absent": True,
    }


def binding(execution):
    """Every input and final answer identity participates, including recovered leaves."""
    return {
        "artifact_inventory_sha256": digest(
            {kind: execution[kind] for kind in ("inputs", "reference", "oracle_outputs")}
        ),
        "asset_catalog_sha256": execution["environment"]["asset_catalog"]["sha256"],
    }


def check_review(review, execution):
    if review is None or any(review.get(key) != value for key, value in binding(execution).items()):
        raise ValueError(
            "Review the executed final artifact inventory and installed assets, then resubmit "
            "environment_review with these exact identities: " + json.dumps(binding(execution))
        )
    if not isinstance(review.get("assessment"), str) or not review["assessment"].strip():
        raise ValueError("Explain final-output answer exposure and unused-file evidence")
    validate_manifest({"files": review["additional_exclusions"]}, require_reason=True)


def effective_exclusions(base, candidate, execution):
    """Historical artifacts have no post-construction environment declaration."""
    review, environment = candidate.get("environment_review"), execution.get("environment")
    if review is None and environment is None:
        return base
    if review is None or environment is None:
        raise ValueError("Incomplete final-environment review or execution evidence")
    check_review(review, execution)
    merged = merge_exclusions(base, review["additional_exclusions"])
    if environment["exclusions"] != merged:
        raise ValueError("Final environment differs from the worker-declared manifest")
    if environment["removal_receipt"] != removal_receipt(merged):
        raise ValueError("Final environment has no matching verified removal receipt")
    return merged
