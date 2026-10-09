"""Dispatch one frozen batch entry through a supplied remote backend."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from biotasks.factory_budget import SessionBudget
from biotasks.factory_stage import STAGE_ROLES, WORKFLOWS, predecessor_slot


def session_identity(batch_sha256: str, seed: str, slot: str) -> str:
    """Name a fixed workflow slot, including the second invocation of review."""
    if slot not in STAGE_ROLES:
        raise ValueError("Unknown workflow slot")
    return f"{batch_sha256}:{seed}:{slot}"


def validate_predecessor(
    budget: SessionBudget,
    root_hash: str,
    seed: str,
    slot: str,
    predecessor: dict,
    workflow_version: int = 1,
) -> None:
    """Require the exact settled predecessor and its preserved artifact receipt.

    This checks scheduling lineage, not scientific correctness. The workflow's
    review/validation policy must select the transition before preparing a stage.
    A failed worker can still produce evidence for review, but a missing or
    ambiguous remote outcome must be reconciled before another stage is launched.
    """
    previous = predecessor_slot(slot, workflow_version)
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
            (expected, seed, STAGE_ROLES[previous]),
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
    version = batch.get("workflow_version", 1)
    if (
        version not in WORKFLOWS
        or slot not in WORKFLOWS[version]
        or STAGE_ROLES[slot] != spec["stage"]
    ):
        raise ValueError("Worker role does not match workflow slot")
    root_hash = batch.get("root_batch_sha256", batch_sha256)
    if len(root_hash) != 64 or any(c not in "0123456789abcdef" for c in root_hash):
        raise ValueError("Exact root batch hash required")
    initial = predecessor_slot(slot, version) is None
    if initial and root_hash != batch_sha256:
        raise ValueError("Initial authoring must use its own frozen batch")
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != spec["input_zip_sha256"]:
        raise ValueError("Input archive changed after batch freeze")
    if hashlib.sha256(spec["prompt"].encode()).hexdigest() != spec["prompt_sha256"]:
        raise ValueError("Worker prompt hash mismatch")
    templates = batch.get("stage_templates")
    workflow_hash = None
    if version != 1 and templates is None:
        raise ValueError("Missing frozen worker templates")
    if templates is not None:
        if set(templates) != set(WORKFLOWS[version]):
            raise ValueError("Missing frozen worker stage")
        template = templates[slot]
        for field, value in template.items():
            if field in {"request_cap", "wall_seconds"}:
                if type(spec.get(field)) is not int or not 1 <= spec[field] <= value:
                    raise ValueError("Worker exceeds frozen stage limit")
            elif spec.get(field) != value:
                raise ValueError("Worker differs from its frozen template")
        workflow_hash = hashlib.sha256(
            json.dumps({"version": version, "templates": templates}, sort_keys=True).encode()
        ).hexdigest()
    budget.bind_batch(
        root_hash, batch["factory_revision"], initial=initial, workflow_sha256=workflow_hash
    )
    validate_predecessor(budget, root_hash, seed, slot, spec.get("predecessor", {}), version)
    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    session = session_identity(root_hash, seed, slot)
    budget.reserve(session, seed, spec["stage"], spec_hash)
    job_id = submit(session, batch, archive)
    budget.submitted(session, job_id)
    return job_id
