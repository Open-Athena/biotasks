"""Freeze a seed-independent batch plan; no execution or budget authorization."""

import hashlib
import json
import re
from pathlib import Path

from biotasks.factory_stage import stage_spec


def freeze_batch(
    revision: str,
    inputs: dict[str, Path],
    protocol: dict,
    request_cap: int,
    wall_seconds: int,
    concurrency: int,
    output: Path,
    execution_budget: Path | None = None,
) -> dict:
    """Bind all panel entries to the same initial worker spec and protocol.

    The caller must establish that revision is a clean checkpoint containing the
    code and prompts used here. This plan does not submit jobs or reserve budget.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("An exact source revision is required")
    if not inputs or any(not re.fullmatch(r"[a-z0-9-]+", name) for name in inputs):
        raise ValueError("Batch requires safely named inputs")
    if type(concurrency) is not int or not 1 <= concurrency <= len(inputs):
        raise ValueError("Invalid batch concurrency")
    entries = {
        name: stage_spec("authoring", archive, request_cap, wall_seconds)
        for name, archive in sorted(inputs.items())
    }
    record = {
        "schema_version": 1,
        "status": "prepared_not_submitted",
        "factory_revision": revision,
        "protocol": protocol,
        "concurrency": concurrency,
        "seed_count": len(entries),
        "entries": entries,
        "automatic_retries": 0,
        "execution_budget_sha256": (
            hashlib.sha256(execution_budget.read_bytes()).hexdigest()
            if execution_budget is not None
            else None
        ),
    }
    encoded = json.dumps(record, sort_keys=True, indent=2) + "\n"
    with output.open("x") as destination:
        destination.write(encoded)
    return {"sha256": hashlib.sha256(encoded.encode()).hexdigest(), "seed_count": len(entries)}


def execution_limits(batch: dict, budget_bytes: bytes) -> dict:
    """Reject budget or resource changes after a batch has been frozen."""
    if hashlib.sha256(budget_bytes).hexdigest() != batch.get("execution_budget_sha256"):
        raise ValueError("Execution budget is not bound to this frozen batch")
    limits = json.loads(budget_bytes)
    if batch["concurrency"] != limits["concurrency"]:
        raise ValueError("Batch and budget concurrency differ")
    if len(batch["entries"]) != limits["seeds_per_batch"]:
        raise ValueError("Batch denominator differs from plan")
    if batch["protocol"]["resources"] != limits["resources"]:
        raise ValueError("Batch and budget resource profiles differ")
    for spec in batch["entries"].values():
        for field, ceiling in (
            ("request_cap", "maximum_model_requests_per_session"),
            ("output_cap", "maximum_output_tokens_per_request"),
            ("wall_seconds", "session_wall_seconds"),
        ):
            if type(spec[field]) is not int or not 1 <= spec[field] <= limits[ceiling]:
                raise ValueError(f"Session exceeds {field} limit")
    return limits
