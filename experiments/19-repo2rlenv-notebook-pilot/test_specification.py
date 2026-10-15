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


@pytest.mark.parametrize("mode", ["ready", "needs_evidence", "invalid", "truncated"])
def test_one_call_preserves_response_without_running_downstream(tmp_path, mode):
    import asyncio
    import time

    from run_specification import run

    calls = []
    candidate = dict(
        disposition="draft_ready" if mode == "ready" else "needs_evidence",
        review="Source review",
        task_brief="Complete brief" if mode == "ready" else "",
        validation_plan="Executable checks needed",
    )
    if mode == "invalid":
        candidate["task_brief"] = "Blocked but nonempty"

    async def complete(payload):
        calls.append(payload)
        assert "tools" not in payload
        assert "max_tokens" not in payload
        assert payload["response_format"]["json_schema"]["strict"] is True
        context = json.loads(payload["messages"][1]["content"])
        assert "trial/reference.py" in context["files"]
        return {
            "choices": [
                {
                    "finish_reason": "length" if mode == "truncated" else "stop",
                    "message": {"role": "assistant", "content": json.dumps(candidate)},
                }
            ]
        }

    config = json.loads((Path(__file__).parent / "specification-config.json").read_text())
    root = tmp_path / "specification"
    coroutine = run(
        config,
        root=root,
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=complete,
    )
    if mode in {"invalid", "truncated"}:
        with pytest.raises(RuntimeError):
            asyncio.run(coroutine)
    else:
        asyncio.run(coroutine)
        assert json.loads((root / "specification.json").read_text()) == candidate
    assert len(calls) == 1
    assert (root / "task-brief.md").exists() == (mode == "ready")
    result = json.loads((root / "result.json").read_text())
    assert result["model_request_slots_used"] == 1
    assert result["daytona_sandboxes_created"] == 0
    assert not result["construction_run"]
    assert not result["solver_run"]
