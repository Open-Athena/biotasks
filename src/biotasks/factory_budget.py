"""Durable session reservations for a bounded factory campaign."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from biotasks.factory_stage import STAGE_PROMPTS


class SessionBudget:
    """Count every reservation, including failures and uncertain submissions.

    Import historical sessions before reserving new work. A reservation is never
    refunded automatically; its ID must be used to reconcile remote submission.
    """

    def __init__(self, path: Path, total: int, per_seed: int, concurrency: int):
        if any(type(n) is not int or n < 1 for n in (total, per_seed, concurrency)):
            raise ValueError("Budget limits must be positive integers")
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS limits (total, per_seed, concurrency)")
            current = db.execute("SELECT * FROM limits").fetchall()
            limits = (total, per_seed, concurrency)
            if current and current != [limits]:
                raise ValueError("Existing campaign limits differ; do not silently expand budget")
            if not current:
                db.execute("INSERT INTO limits VALUES (?, ?, ?)", limits)
            db.execute(
                "CREATE TABLE IF NOT EXISTS sessions "
                "(id TEXT PRIMARY KEY, seed TEXT NOT NULL, stage TEXT NOT NULL, "
                "spec_sha256 TEXT NOT NULL, state TEXT NOT NULL, job_id TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS batches "
                "(id TEXT PRIMARY KEY, factory_revision TEXT NOT NULL)"
            )

            columns = {row[1] for row in db.execute("PRAGMA table_info(batches)")}
            if "workflow_sha256" not in columns:
                db.execute("ALTER TABLE batches ADD COLUMN workflow_sha256 TEXT")

    def bind_batch(
        self, batch_sha256: str, revision: str, *, initial: bool, workflow_sha256: str | None = None
    ) -> None:
        """Keep all follow-up workers on the initially checkpointed factory.

        Older ledgers need an explicit binding from their verified original batch
        before scheduling follow-ups; absence is not permission to choose a pin.
        """
        for value, size in ((batch_sha256, 64), (revision, 40)):
            if len(value) != size or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("Exact batch hash and factory revision required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT factory_revision, workflow_sha256 FROM batches WHERE id=?", (batch_sha256,)
            ).fetchone()
            if row is None:
                if not initial:
                    raise ValueError("Root batch is not registered; reconcile its original pin")
                db.execute(
                    "INSERT INTO batches VALUES (?, ?, ?)",
                    (batch_sha256, revision, workflow_sha256),
                )
            elif row[0] != revision:
                raise ValueError("Factory revision changed within the frozen batch")
            elif row[1] != workflow_sha256:
                raise ValueError("Worker templates changed within the frozen batch")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=0)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, session_id: str, seed: str, stage: str, spec_sha256: str) -> None:
        if not session_id or not seed or stage not in STAGE_PROMPTS:
            raise ValueError("Invalid session identity")
        if len(spec_sha256) != 64 or any(c not in "0123456789abcdef" for c in spec_sha256):
            raise ValueError("Exact specification hash required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            total, per_seed, concurrency = db.execute("SELECT * FROM limits").fetchone()
            if db.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone():
                raise ValueError("Session already reserved; reconcile instead of resubmitting")
            if db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] >= total:
                raise ValueError("Campaign session budget exhausted")
            if (
                db.execute("SELECT COUNT(*) FROM sessions WHERE seed=?", (seed,)).fetchone()[0]
                >= per_seed
            ):
                raise ValueError("Seed session budget exhausted")
            if (
                db.execute(
                    "SELECT COUNT(*) FROM sessions WHERE state IN ('reserved', 'submitted')"
                ).fetchone()[0]
                >= concurrency
            ):
                raise ValueError("Campaign concurrency occupied")
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, 'reserved', NULL)",
                (session_id, seed, stage, spec_sha256),
            )

    def submitted(self, session_id: str, job_id: str) -> None:
        if not job_id:
            raise ValueError("Remote job identity required")
        with self.connect() as db:
            result = db.execute(
                "UPDATE sessions SET state='submitted', job_id=? WHERE id=? AND state='reserved'",
                (job_id, session_id),
            )
            if result.rowcount != 1:
                raise ValueError("Session is not awaiting submission reconciliation")

    def terminal(self, session_id: str, job_id: str, state: str) -> None:
        """Record an authoritative remote terminal observation, never a timeout."""
        if state not in {"succeeded", "failed", "killed"}:
            raise ValueError("Not an authoritative terminal state")
        with self.connect() as db:
            result = db.execute(
                "UPDATE sessions SET state=? WHERE id=? AND job_id=? AND state='submitted'",
                (state, session_id, job_id),
            )
            if result.rowcount != 1:
                raise ValueError("Terminal observation does not match a submitted session")
