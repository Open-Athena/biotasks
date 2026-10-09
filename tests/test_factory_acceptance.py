import json

from biotasks.factory_acceptance import AUDIT_REQUIREMENTS, acceptance
from biotasks.factory_controller import NativeEvidence, WorkerEvidence, decide
from biotasks.factory_native import candidate_hash


def ready(tmp_path, monkeypatch):
    (tmp_path / "task").mkdir()
    (tmp_path / "task/instruction.md").write_text("Immutable test candidate")
    (tmp_path / "evidence.md").write_text("Test evidence placeholder; not a scientific claim.")
    directory = tmp_path / "native"
    case = directory / "reference"
    case.mkdir(parents=True)
    row = {
        "backend_disk_gib": 10,
        "backend_metrics": [{"disk_total": 10 * 1024**3, "disk_used": 1000}],
        "measurements": {"memory.peak": "1048576"},
    }
    (case / "sandbox-resources.jsonl").write_text((json.dumps(row) + "\n") * 2)
    monkeypatch.setattr(
        "biotasks.factory_acceptance.assess_saved_suite",
        lambda *_: {
            "status": "passed",
            "cases": [{"id": "reference"}],
        },
    )
    report = {
        "schema_version": 1,
        "disposition": "ready_for_validation",
        "findings": [],
        "checks_performed": [],
        "checks_pending": [],
        "acceptance_checks": {
            name: {
                "status": "satisfied",
                "rationale": "Fixture for gate behavior",
                "evidence_paths": ["evidence.md"],
            }
            for name in AUDIT_REQUIREMENTS
        },
    }
    integrity = {"candidate_unchanged": True, "candidate_sha256": candidate_hash(tmp_path)}
    return directory, report, integrity


def test_complete_evidence_routes_to_fresh_baseline_without_solver_outcome(tmp_path, monkeypatch):
    directory, report, integrity = ready(tmp_path, monkeypatch)
    result = acceptance(tmp_path, directory, report, integrity)
    assert result["status"] == "accepted"
    worker = WorkerEvidence(
        "review", "succeeded", "worker_finished", True, integrity["candidate_sha256"]
    )
    decision = decide(
        worker,
        NativeEvidence(worker.candidate_sha256, "passed"),
        workspace=tmp_path,
        review_report=report,
        reviewed_candidate_sha256=worker.candidate_sha256,
        candidate_unchanged=True,
        native_directory=directory,
    )
    assert decision.action == "baseline"


def test_host_filesystem_or_unresolved_science_prevents_acceptance(tmp_path, monkeypatch):
    directory, report, integrity = ready(tmp_path, monkeypatch)
    report["acceptance_checks"]["lineage_and_terms"]["status"] = "unresolved"
    assert acceptance(tmp_path, directory, report, integrity)["status"] == "verification_incomplete"
    report["acceptance_checks"]["lineage_and_terms"]["status"] = "satisfied"
    path = directory / "reference/sandbox-resources.jsonl"
    row = json.loads(path.read_text().splitlines()[0])
    row["backend_metrics"][0]["disk_total"] = 200 * 1024**3
    path.write_text((json.dumps(row) + "\n") * 2)
    result = acceptance(tmp_path, directory, report, integrity)
    assert result["status"] == "verification_incomplete"
    assert any("Disk metrics" in reason for reason in result["reasons"])


def test_task_mutation_after_audit_never_accepts(tmp_path, monkeypatch):
    directory, report, integrity = ready(tmp_path, monkeypatch)
    (tmp_path / "task/instruction.md").write_text("Changed instructions")
    assert acceptance(tmp_path, directory, report, integrity)["status"] == "verification_incomplete"
