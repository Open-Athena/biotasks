"""Resume a frozen panel, filling capacity without replaying submitted workers.

One invocation observes each active handle once and submits available slots.
The caller decides when to observe again; this module never polls or retries.
"""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from biotasks.factory_budget import SessionBudget
from biotasks.factory_dispatch import dispatch, session_identity


def resume_batch(
    batch_path: Path,
    batch_sha256: str,
    archives: Path,
    budget: SessionBudget,
    submit: Callable[[str, dict, Path], str],
    observe: Callable[[str], str],
) -> list[dict]:
    """Reconcile known jobs, skip reserved slots, and fill remaining capacity.

    A reservation without a job ID requires explicit reconciliation. An unknown
    observation retains capacity. Neither case permits resubmitting that slot.
    Submission exceptions propagate with the reservation still occupied.
    """
    raw = batch_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != batch_sha256:
        raise ValueError("Frozen batch hash mismatch")
    batch = json.loads(raw)
    root_hash = batch.get("root_batch_sha256", batch_sha256)
    with budget.connect() as db:
        active = db.execute("SELECT id, job_id FROM sessions WHERE state='submitted'").fetchall()
    for session, job in active:
        state = observe(job)
        if state in {"succeeded", "failed", "killed"}:
            budget.terminal(session, job, state)
        elif state not in {"pending", "running", "unknown"}:
            raise ValueError("Unknown remote observation")
    records = []
    for seed, spec in batch["entries"].items():
        slot = spec.get("stage_slot", spec["stage"])
        session = session_identity(root_hash, seed, slot)
        with budget.connect() as db:
            existing = db.execute(
                "SELECT state, job_id FROM sessions WHERE id=?", (session,)
            ).fetchone()
            concurrency = db.execute("SELECT concurrency FROM limits").fetchone()[0]
            occupied = db.execute(
                "SELECT COUNT(*) FROM sessions WHERE state IN ('reserved', 'submitted')"
            ).fetchone()[0]
        if existing:
            state, job = existing
        elif occupied >= concurrency:
            state, job = "pending_capacity", None
        else:
            job = dispatch(
                batch_path, batch_sha256, seed, archives / (seed + ".zip"), budget, submit
            )
            state = "submitted"
        records.append({"seed": seed, "session": session, "state": state, "job_id": job})
    return records
