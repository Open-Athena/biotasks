"""Offline checks of evidence linkage and blocked-draft handling."""

import json
import shutil
from pathlib import Path

import pytest
from specification_inputs import specification_context
from specification_protocol import TaskSpecification


@pytest.fixture
def run(tmp_path):
    source = Path(__file__).parent / "setup-runs/001"
    return Path(shutil.copytree(source, tmp_path / "run"))


def test_current_evidence_and_modified_source(run):
    context = specification_context(run, {})
    assert context["files"]["trial/result.json"]["execution"]["exit_code"] == 0
    with (run / "candidate/analysis.py").open("a") as stream:
        stream.write("\n# unrecorded change\n")
    with pytest.raises(ValueError, match="Original evidence changed"):
        specification_context(run, {})


def test_audit_from_another_execution_is_rejected(run):
    path = run / "output-audit.json"
    value = json.loads(path.read_text())
    value["outputs"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="audited files disagree"):
        specification_context(run, {})


def test_missing_export_audit_is_rejected(run):
    path = run / "output-audit.json"
    value = json.loads(path.read_text())
    value["outputs"].pop()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="audited files disagree"):
        specification_context(run, {})


@pytest.mark.parametrize("decision", ["needs_evidence", "reference_work_required", "reject"])
def test_blocked_response_cannot_supply_an_accepted_brief(decision):
    with pytest.raises(ValueError, match="Only draft_ready"):
        TaskSpecification(
            disposition=decision, review="A blocker", task_brief="Do this", validation_plan="Check"
        )
