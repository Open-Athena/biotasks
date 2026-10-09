"""Freeze a seed-independent batch plan; no execution or budget authorization."""

import hashlib
import json
import re
from pathlib import Path

from biotasks.factory_stage import STAGE_ROLES, WORKFLOWS, stage_spec, worker_template


def freeze_batch(
    revision: str,
    inputs: dict[str, Path],
    protocol: dict,
    request_cap: int,
    wall_seconds: int,
    concurrency: int,
    output: Path,
    execution_budget: Path | None = None,
    workflow_version: int = 1,
    stage_limits: dict | None = None,
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
    if workflow_version not in WORKFLOWS:
        raise ValueError("Unknown fixed workflow version")
    slots = WORKFLOWS[workflow_version]
    templates = {}
    if stage_limits is not None:
        if set(stage_limits) != set(slots):
            raise ValueError("Every fixed stage needs explicit limits")
        templates = {
            slot: worker_template(
                STAGE_ROLES[slot],
                stage_limits[slot]["request_cap"],
                stage_limits[slot]["wall_seconds"],
                stage_limits[slot],
            )
            for slot in slots
        }
    elif workflow_version != 1:
        raise ValueError("New workflows require explicit per-stage limits")
    initial_role = STAGE_ROLES[slots[0]]
    entries = {
        name: stage_spec(
            initial_role,
            archive,
            request_cap,
            wall_seconds,
            stage_limits[slots[0]] if stage_limits is not None else None,
        )
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
    if templates:
        record.update(workflow_version=workflow_version, stage_templates=templates)
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
    if batch.get("workflow_version", 1) != 1:
        version = batch["workflow_version"]
        if version != limits.get("workflow_version"):
            raise ValueError("Batch and budget workflow differ")
        templates = batch["stage_templates"]
        if set(templates) != set(WORKFLOWS[version]):
            raise ValueError("Missing frozen worker stage")
        for slot, template in templates.items():
            for field in ("request_cap", "output_cap", "wall_seconds"):
                if template[field] != limits["stage_limits"][slot][field]:
                    raise ValueError("Worker stage differs from its frozen budget")
        if len(templates) > limits["maximum_new_sessions_per_seed"]:
            raise ValueError("Workflow exceeds per-seed session budget")
        if (
            sum(t["request_cap"] for t in templates.values())
            > limits["maximum_model_requests_per_seed"]
        ):
            raise ValueError("Workflow exceeds per-seed request budget")
    return limits
