"""Dispatch one frozen batch entry through a supplied remote backend."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from biotasks.factory_budget import SessionBudget

STAGE_SLOTS = {
    "authoring": ("authoring", None),
    "review": ("review", "authoring"),
    "repair": ("repair", "review"),
    "review_after_repair": ("review", "repair"),
}


def session_identity(batch_sha256: str, seed: str, slot: str) -> str:
    """Name a fixed workflow slot, including the second invocation of review."""
    if slot not in STAGE_SLOTS:
        raise ValueError("Unknown workflow slot")
    return f"{batch_sha256}:{seed}:{slot}"


def validate_predecessor(
    budget: SessionBudget, root_hash: str, seed: str, slot: str, predecessor: dict
) -> None:
    """Require the exact settled predecessor and its preserved artifact receipt.

    This checks scheduling lineage, not scientific correctness. The workflow's
    review/validation policy must select the transition before preparing a stage.
    A failed worker can still produce evidence for review, but a missing or
    ambiguous remote outcome must be reconciled before another stage is launched.
    """
    _, previous = STAGE_SLOTS[slot]
    if previous is None:
        if predecessor:
            raise ValueError("Initial authoring cannot have a predecessor")
        return
    expected = session_identity(root_hash, seed, previous)
    if predecessor.get("session_id") != expected:
        raise ValueError("Wrong workflow predecessor")
    artifact_hash = predecessor.get("artifact_receipt_sha256", "")
    if len(artifact_hash) != 64 or any(c not in "0123456789abcdef" for c in artifact_hash):
        raise ValueError("Preserved parent artifact receipt hash required")
    with budget.connect() as db:
        parent = db.execute(
            "SELECT spec_sha256, state, job_id FROM sessions WHERE id=? AND seed=? AND stage=?",
            (expected, seed, STAGE_SLOTS[previous][0]),
        ).fetchone()
    if parent is None or parent[1] not in {"succeeded", "failed", "killed"}:
        raise ValueError("Predecessor is not authoritatively terminal")
    if (predecessor.get("spec_sha256"), predecessor.get("job_id")) != (parent[0], parent[2]):
        raise ValueError("Predecessor receipt differs from the reserved session")


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
    slot = spec.get("stage_slot", spec["stage"])
    if slot not in STAGE_SLOTS or STAGE_SLOTS[slot][0] != spec["stage"]:
        raise ValueError("Worker role does not match workflow slot")
    root_hash = batch.get("root_batch_sha256", batch_sha256)
    if len(root_hash) != 64 or any(c not in "0123456789abcdef" for c in root_hash):
        raise ValueError("Exact root batch hash required")
    if slot == "authoring" and root_hash != batch_sha256:
        raise ValueError("Initial authoring must use its own frozen batch")
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != spec["input_zip_sha256"]:
        raise ValueError("Input archive changed after batch freeze")
    if hashlib.sha256(spec["prompt"].encode()).hexdigest() != spec["prompt_sha256"]:
        raise ValueError("Worker prompt hash mismatch")
    budget.bind_batch(root_hash, batch["factory_revision"], initial=slot == "authoring")
    validate_predecessor(budget, root_hash, seed, slot, spec.get("predecessor", {}))
    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    session = session_identity(root_hash, seed, slot)
    budget.reserve(session, seed, spec["stage"], spec_hash)
    job_id = submit(session, batch, archive)
    budget.submitted(session, job_id)
    return job_id
