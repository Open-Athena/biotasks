"""Route the fixed worker sequence using host observations and GLM findings.

The controller does not author scientific repairs or supply a reward. Acceptance
is a separate gate: reaching it means the candidate is ready to be checked, not
that it is valid or that a solver attempt may already start.
"""

from dataclasses import dataclass
from pathlib import Path

from biotasks.factory_acceptance import acceptance
from biotasks.factory_native import assess_saved_suite
from biotasks.factory_proposal import proposal_action
from biotasks.factory_review import next_stage
from biotasks.factory_stage import STAGE_ROLES


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

    @classmethod
    def from_records(cls, workspace: Path, directory: Path):
        """Consume recovered native results, not a caller's asserted success flag."""
        assessed = assess_saved_suite(workspace, directory)
        return cls(assessed["candidate_sha256"], assessed["status"])


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
    native_directory: Path | None = None,
) -> Decision:
    """Select one operation, preserving failed jobs and the single repair bound.

    Callers obtain worker/native/integrity evidence from host-owned records. A
    worker-authored assertion is not a substitute for those observations.
    Dispatch still enforces the frozen budget and exact predecessor identity.
    """
    if worker.slot not in STAGE_ROLES:
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
    if worker.slot == "specification":
        if worker.outcome != "worker_finished":
            return Decision(
                "specification_incomplete", "Unfinished specification preserves its evidence"
            )
        try:
            action = proposal_action(workspace)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return Decision(
                "specification_incomplete", "Proposal contract or source binding is invalid"
            )
        return Decision(action, "Apply the source-bound GLM specification disposition")
    if (
        worker.slot in {"authoring", "construction", "repair"}
        and worker.outcome == "worker_finished"
    ):
        rejection = workspace / "rejection.md"
        if (
            rejection.is_file()
            and rejection.resolve().is_relative_to(workspace.resolve())
            and rejection.read_text().strip()
        ):
            return Decision(
                "rejected", "GLM worker recorded a seed rejection with its supporting evidence"
            )
    if worker.slot in {"review", "review_after_repair"} and (
        worker.outcome == "worker_finished"
        and candidate_unchanged is True
        and reviewed_candidate_sha256 == worker.candidate_sha256
        and review_report is not None
        and review_report.get("disposition") == "rejected"
    ):
        action = next_stage(review_report, workspace, int(worker.slot == "review"))
        return Decision(action, "GLM audit rejected the seed; no further native run is required")
    if native is None:
        return Decision("native_validation", "Run checks before the GLM audit")
    if native.candidate_sha256 != worker.candidate_sha256:
        raise ValueError("Native evidence belongs to a different candidate")
    if native.status not in {"passed", "task_defect", "not_runnable", "infra_error", "incomplete"}:
        raise ValueError("Unknown native validation outcome")
    if native.status in {"infra_error", "incomplete"}:
        return Decision("validation_incomplete", "Do not send infrastructure failures to repair")
    if worker.slot in {"authoring", "construction", "repair"}:
        return Decision(
            "review_after_repair" if worker.slot == "repair" else "review",
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
    if native_directory is not None:
        result = acceptance(
            workspace,
            native_directory,
            review_report,
            {
                "candidate_unchanged": candidate_unchanged,
                "candidate_sha256": reviewed_candidate_sha256,
            },
        )
        return Decision(
            "baseline" if result["status"] == "accepted" else result["status"],
            "Native evidence and scientific audit passed; run one fresh baseline"
            if result["status"] == "accepted"
            else "; ".join(result["reasons"]),
        )
    return Decision("acceptance_check", "Native checks and audit are ready for the acceptance gate")
