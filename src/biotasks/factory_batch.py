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
    }
    encoded = json.dumps(record, sort_keys=True, indent=2) + "\n"
    with output.open("x") as destination:
        destination.write(encoded)
    return {"sha256": hashlib.sha256(encoded.encode()).hexdigest(), "seed_count": len(entries)}
