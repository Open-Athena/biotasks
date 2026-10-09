"""Dispatch one frozen batch entry through a supplied remote backend."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from biotasks.factory_budget import SessionBudget


def dispatch(
    batch_path: Path,
    batch_sha256: str,
    seed: str,
    archive: Path,
    budget: SessionBudget,
    submit: Callable[[str, dict, Path], str],
) -> str:
    """Reserve before calling the backend; never retry ambiguous submission.

    Backend receives a deterministic session identity for reconciliation. It must
    submit the checkpointed factory revision, enforce resources, and return a
    remote job ID. An exception leaves the reservation occupied for reconciliation.
    """
    raw = batch_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != batch_sha256:
        raise ValueError("Frozen batch hash mismatch")
    batch = json.loads(raw)
    spec = batch["entries"][seed]
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != spec["input_zip_sha256"]:
        raise ValueError("Input archive changed after batch freeze")
    if hashlib.sha256(spec["prompt"].encode()).hexdigest() != spec["prompt_sha256"]:
        raise ValueError("Worker prompt hash mismatch")
    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    session = f"{batch_sha256}:{seed}:{spec['stage']}"
    budget.reserve(session, seed, spec["stage"], spec_hash)
    job_id = submit(session, batch, archive)
    budget.submitted(session, job_id)
    return job_id
