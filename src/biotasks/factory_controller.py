"""Route the fixed worker sequence using host observations and GLM findings.

The controller does not author scientific repairs or supply a reward. Acceptance
is a separate gate: reaching it means the candidate is ready to be checked, not
that it is valid or that a solver attempt may already start.
"""

from dataclasses import dataclass
from pathlib import Path

from biotasks.factory_dispatch import STAGE_SLOTS
from biotasks.factory_review import next_stage


@dataclass(frozen=True)
class WorkerEvidence:
    slot: str
    remote_state: str
    outcome: str
    artifacts_verified: bool
    candidate_sha256: str


@dataclass(frozen=True)
class NativeEvidence:
    candidate_sha256: str
    status: str  # passed, task_defect, not_runnable, infra_error, incomplete


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str


def decide(
    worker: WorkerEvidence,
    native: NativeEvidence | None,
    *,
    workspace: Path,
    review_report: dict | None = None,
    reviewed_candidate_sha256: str | None = None,
    candidate_unchanged: bool | None = None,
) -> Decision:
    """Select one operation, preserving failed jobs and the single repair bound.

    Callers obtain worker/native/integrity evidence from host-owned records. A
    worker-authored assertion is not a substitute for those observations.
    Dispatch still enforces the frozen budget and exact predecessor identity.
    """
    if worker.slot not in STAGE_SLOTS:
        raise ValueError("Unknown workflow slot")
    if worker.remote_state in {"reserved", "unknown"}:
        return Decision("reconcile", "Submission or observation remains uncertain")
    if worker.remote_state in {"pending", "running"}:
        return Decision("wait", "The existing remote worker is still active")
    if worker.remote_state not in {"succeeded", "failed", "killed"}:
        raise ValueError("Unknown remote observation")
    if not worker.artifacts_verified:
        return Decision("recover_artifacts", "Terminal job does not prove artifact recovery")
    if len(worker.candidate_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in worker.candidate_sha256
    ):
        raise ValueError("Exact candidate manifest hash required")
    if native is None:
        return Decision("native_validation", "Run checks before the GLM audit")
    if native.candidate_sha256 != worker.candidate_sha256:
        raise ValueError("Native evidence belongs to a different candidate")
    if native.status not in {"passed", "task_defect", "not_runnable", "infra_error", "incomplete"}:
        raise ValueError("Unknown native validation outcome")
    if native.status in {"infra_error", "incomplete"}:
        return Decision("validation_incomplete", "Do not send infrastructure failures to repair")
    if worker.slot in {"authoring", "repair"}:
        return Decision(
            "review" if worker.slot == "authoring" else "review_after_repair",
            "Audit the candidate and its executable evidence, including failures",
        )
    if worker.outcome != "worker_finished":
        return Decision("review_incomplete", "An unfinished audit cannot approve the candidate")
    if candidate_unchanged is not True or reviewed_candidate_sha256 != worker.candidate_sha256:
        return Decision("review_incomplete", "Audit integrity or candidate identity is unverified")
    if review_report is None:
        return Decision("review_incomplete", "GLM audit report is missing")
    repairs_remaining = int(worker.slot == "review")
    action = next_stage(review_report, workspace, repairs_remaining)
    if action != "native_validation":
        return Decision(action, "Apply the versioned GLM review report")
    if native.status in {"task_defect", "not_runnable"}:
        return Decision(
            "repair" if repairs_remaining else "budget_exhausted",
            "Executable task defects override an advisory ready disposition",
        )
    if review_report["checks_pending"]:
        return Decision("verification_incomplete", "GLM audit still lists unresolved checks")
    return Decision("acceptance_check", "Native checks and audit are ready for the acceptance gate")
