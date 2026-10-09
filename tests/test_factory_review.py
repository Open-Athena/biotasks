import pytest

from biotasks.factory_review import next_stage


def report(disposition="ready_for_validation"):
    return {
        "schema_version": 1,
        "disposition": disposition,
        "findings": [],
        "checks_performed": [],
        "checks_pending": ["Native execution"],
    }


def test_ready_review_never_accepts_task(tmp_path):
    assert next_stage(report(), tmp_path, 0) == "native_validation"


def test_failed_execution_alone_is_not_a_scientific_defect(tmp_path):
    (tmp_path / "failure.log").write_text("environment startup failed")
    value = report()
    value["checks_performed"] = [
        {"command": "validate", "exit_status": 1, "evidence_paths": ["failure.log"]}
    ]
    assert next_stage(value, tmp_path, 1) == "verification_incomplete"


def test_repair_cannot_exceed_remaining_budget(tmp_path):
    assert next_stage(report("repair_required"), tmp_path, 0) == "budget_exhausted"
    assert next_stage(report("repair_required"), tmp_path, 1) == "repair"


def finding(path):
    return {
        "id": "F1",
        "severity": "blocking",
        "description": "Required output has no corresponding grade check",
        "requirement": "Grade all scientific deliverables",
        "evidence_paths": [path],
    }


def test_blocking_evidence_overrides_ready_label(tmp_path):
    (tmp_path / "evidence.txt").write_text("preserved review evidence")
    value = report()
    value["findings"] = [finding("evidence.txt")]
    assert next_stage(value, tmp_path, 1) == "repair"


@pytest.mark.parametrize("path", ["missing.txt", "../outside", "/etc/passwd"])
def test_unavailable_or_escaping_evidence_cannot_advance(tmp_path, path):
    value = report()
    value["findings"] = [finding(path)]
    with pytest.raises(ValueError):
        next_stage(value, tmp_path, 1)


def test_external_symlink_is_not_evidence(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside").write_text("outside")
    (workspace / "evidence").symlink_to(tmp_path / "outside")
    value = report()
    value["findings"] = [finding("evidence")]
    with pytest.raises(ValueError):
        next_stage(value, workspace, 1)
