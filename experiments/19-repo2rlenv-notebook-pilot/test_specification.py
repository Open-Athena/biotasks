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
    assert "trial/uv.lock" not in context["files"]
    assert (
        context["retained_evidence"]["trial/uv.lock"]["sha256"]
        == context["file_sha256"]["trial/uv.lock"]
    )
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
            disposition=decision,
            review="A blocker",
            task_brief="Do this",
            validation_handoff="Check",
        )


@pytest.mark.parametrize("mode", ["ready", "needs_evidence", "invalid", "truncated", "malformed"])
@pytest.mark.parametrize("output_format", ["json_schema", "json_unconstrained"])
def test_one_call_preserves_response_without_running_downstream(tmp_path, mode, output_format):
    import asyncio
    import time

    from run_specification import run

    calls = []
    candidate = dict(
        disposition="draft_ready" if mode == "ready" else "needs_evidence",
        review="Source review",
        task_brief="Complete brief" if mode == "ready" else "",
        validation_handoff="Executable checks needed",
    )
    if mode == "invalid":
        candidate["task_brief"] = "Blocked but nonempty"

    async def complete(payload):
        calls.append(payload)
        assert "tools" not in payload
        assert "max_tokens" not in payload
        if output_format == "json_schema":
            assert payload["response_format"]["json_schema"]["strict"] is True
        else:
            assert "response_format" not in payload
        context = json.loads(payload["messages"][1]["content"])
        assert "trial/reference.py" in context["files"]
        return {
            "choices": [
                {
                    "finish_reason": "length" if mode == "truncated" else "stop",
                    "message": {
                        "role": "assistant",
                        "content": "not JSON" if mode == "malformed" else json.dumps(candidate),
                    },
                }
            ]
        }

    config = json.loads(
        (Path(__file__).parent / "specification-diagnostic-config.json").read_text()
    )
    config["output_format"] = output_format
    root = tmp_path / "specification"
    coroutine = run(
        config,
        root=root,
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=complete,
    )
    if mode in {"invalid", "truncated", "malformed"}:
        with pytest.raises(RuntimeError):
            asyncio.run(coroutine)
    else:
        asyncio.run(coroutine)
        assert json.loads((root / "specification.json").read_text()) == candidate
        assert (root / "validation-handoff.md").read_text() == candidate[
            "validation_handoff"
        ] + "\n"
    assert len(calls) == 1
    assert (root / "task-brief.md").exists() == (mode == "ready")
    result = json.loads((root / "result.json").read_text())
    assert result["model_request_slots_used"] == 1
    assert result["daytona_sandboxes_created"] == 0
    assert not result["construction_run"]
    assert not result["solver_run"]


def test_read_only_session_inspects_then_submits_with_local_validation(tmp_path, monkeypatch):
    import asyncio
    import time

    from package_inspection import PackageInspection
    from run_specification import run

    calls = []

    async def listing(self, package, prefix=""):
        assert package in self.catalog
        return json.dumps({"package": package, "files": ["example.py"]})

    monkeypatch.setattr(PackageInspection, "list_package_files", listing)
    artifact = dict(
        disposition="needs_evidence",
        review="Remaining measurement gap",
        task_brief="",
        validation_handoff="Measure the identified uncertainty",
    )

    async def complete(payload):
        calls.append(payload)
        names = {t["function"]["name"] for t in payload["tools"]}
        assert names == {
            "submit_artifact",
            "revise_artifact",
            "list_package_files",
            "search_package",
            "read_package_file",
        }
        assert "response_format" not in payload and "max_tokens" not in payload
        if len(calls) == 1:
            name, args = "list_package_files", {"package": "scanpy"}
        elif len(calls) == 2:
            assert "example.py" in payload["messages"][-1]["content"]
            name, args = "submit_artifact", {**artifact, "task_brief": "Invalid blocked brief"}
        else:
            assert "Artifact committed." not in payload["messages"][-1]["content"]
            name, args = "submit_artifact", artifact
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": str(len(calls)),
                                "type": "function",
                                "function": {"name": name, "arguments": json.dumps(args)},
                            }
                        ],
                    },
                }
            ]
        }

    config = json.loads(
        (Path(__file__).parent / "specification-runs/013/configuration.json").read_text()
    )
    root = tmp_path / "specification"
    asyncio.run(
        run(
            config,
            root=root,
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    result = json.loads((root / "result.json").read_text())
    assert len(calls) == result["model_request_slots_used"] == 3
    assert result["package_inspection_enabled"]
    assert not result["scientific_analysis_executed"]
    assert not result["solver_run"] and not result["construction_run"]
    assert json.loads((root / "specification.json").read_text()) == artifact
    assert (root / "validation-handoff.md").read_text() == artifact["validation_handoff"] + "\n"
    assert not (root / "validation-plan.md").exists()


def test_revision_feedback_is_explicit_model_input(run):
    feedback = {
        "prior_proposal": {"task_brief": "Prior draft"},
        "operator_feedback": ["Check units"],
    }
    context = specification_context(run, {}, revision_context=feedback)
    assert context["revision_context"] == feedback
    assert "package_inspection" not in context


def test_submission_only_revision_receives_rejection_feedback(tmp_path):
    import asyncio
    import time

    from run_specification import run

    calls = []
    proposal = dict(
        disposition="draft_ready",
        review="Review",
        task_brief="Scientific task",
        validation_handoff="Measure comparisons",
    )

    async def complete(payload):
        calls.append(payload)
        assert {t["function"]["name"] for t in payload["tools"]} == {
            "submit_artifact",
            "revise_artifact",
        }
        if len(calls) > 1:
            assert "Artifact rejected" in payload["messages"][-1]["content"]
        value = proposal | ({"task_brief": ""} if len(calls) == 1 else {})
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": str(len(calls)),
                                "type": "function",
                                "function": {
                                    "name": "submit_artifact",
                                    "arguments": json.dumps(value),
                                },
                            }
                        ],
                    },
                }
            ]
        }

    config = json.loads((Path(__file__).parent / "specification-config.json").read_text())
    assert config["output_format"] == "tools" and not config["inspect_packages"]
    root = tmp_path / "submission-only"
    asyncio.run(
        run(
            config,
            root=root,
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    assert len(calls) == 2
    assert json.loads((root / "specification.json").read_text()) == proposal
