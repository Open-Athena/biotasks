from dataclasses import replace

import pytest

from biotasks.factory_controller import NativeEvidence, WorkerEvidence, decide


def ready_report():
    return {
        "schema_version": 1,
        "disposition": "ready_for_validation",
        "findings": [],
        "checks_performed": [],
        "checks_pending": [],
    }


def test_infrastructure_and_incomplete_artifacts_never_trigger_a_repair(tmp_path):
    worker = WorkerEvidence("authoring", "running", "", False, "a" * 64)
    assert decide(worker, None, workspace=tmp_path).action == "wait"
    worker = replace(worker, remote_state="failed", outcome="request_budget_exhausted")
    assert decide(worker, None, workspace=tmp_path).action == "recover_artifacts"
    worker = replace(worker, artifacts_verified=True)
    assert decide(worker, None, workspace=tmp_path).action == "native_validation"
    assert (
        decide(worker, NativeEvidence("a" * 64, "infra_error"), workspace=tmp_path).action
        == "validation_incomplete"
    )
    # A capped author can leave a candidate worth auditing after native checks.
    assert (
        decide(worker, NativeEvidence("a" * 64, "task_defect"), workspace=tmp_path).action
        == "review"
    )


def test_ready_review_cannot_override_native_failure_or_repeat_repair(tmp_path):
    worker = WorkerEvidence("review", "succeeded", "worker_finished", True, "a" * 64)
    kwargs = {
        "workspace": tmp_path,
        "review_report": ready_report(),
        "reviewed_candidate_sha256": "a" * 64,
        "candidate_unchanged": True,
    }
    native = NativeEvidence("a" * 64, "task_defect")
    assert decide(worker, native, **kwargs).action == "repair"
    assert (
        decide(replace(worker, slot="review_after_repair"), native, **kwargs).action
        == "budget_exhausted"
    )
    assert decide(worker, replace(native, status="passed"), **kwargs).action == "acceptance_check"


def test_changed_or_unfinished_audit_never_reaches_acceptance(tmp_path):
    worker = WorkerEvidence("review", "succeeded", "worker_finished", True, "a" * 64)
    native = NativeEvidence("a" * 64, "passed")
    kwargs = {
        "workspace": tmp_path,
        "review_report": ready_report(),
        "reviewed_candidate_sha256": "a" * 64,
        "candidate_unchanged": True,
    }
    assert (
        decide(
            worker,
            native,
            workspace=tmp_path,
            review_report=ready_report(),
            reviewed_candidate_sha256="a" * 64,
            candidate_unchanged=False,
        ).action
        == "review_incomplete"
    )
    assert (
        decide(replace(worker, outcome="request_budget_exhausted"), native, **kwargs).action
        == "review_incomplete"
    )
    kwargs["review_report"]["checks_pending"] = ["Unverified alternative implementation"]
    assert decide(worker, native, **kwargs).action == "verification_incomplete"
    with pytest.raises(ValueError, match="different candidate"):
        decide(worker, replace(native, candidate_sha256="b" * 64), **kwargs)
