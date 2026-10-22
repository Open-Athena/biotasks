"""Preparation-only boundary tests using a fake model and the real controller."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from render_preparation import render
from run_preparation import run

HERE = Path(__file__).parent


def response(plan, finish="stop", call_id="call"):
    return {
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(plan),
                },
            }
        ]
    }


@pytest.mark.parametrize("mode", ["accepted", "truncated", "invalid_schema"])
def test_only_preparation_no_output_recovery(tmp_path, mode):
    calls = []
    plan = dict(
        disposition="reject",
        explanation="No eligible terminal result",
        export_code="",
        artifacts=[],
        excluded_outputs=["Plot-only result"],
        unresolved_assumptions=[],
    )

    async def complete(payload):
        calls.append(payload)
        assert "tools" not in payload
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert "export_code" in payload["response_format"]["json_schema"]["schema"]["required"]
        properties = payload["response_format"]["json_schema"]["schema"]["properties"]
        assert (
            not {"environment_rationale", "pyproject_toml", "system_packages", "stage_inputs_sh"}
            & properties.keys()
        )
        context = json.loads(payload["messages"][1]["content"])
        assert set(context) == {"source", "baseline_script", "conversion", "limits"}
        assert "question_text" not in context["source"]
        assert "max_tokens" not in payload
        candidate = dict(plan)
        if mode == "invalid_schema":
            candidate.pop("disposition")
        return response(candidate, "length" if mode == "truncated" else "stop", str(len(calls)))

    coroutine = run(
        json.loads((HERE / "preparation-inputs.json").read_text()),
        root=tmp_path / "preparation",
        seed=json.loads((HERE / "seeds/current.json").read_text())[0],
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=complete,
    )
    if mode in {"truncated", "invalid_schema"}:
        with pytest.raises(RuntimeError):
            asyncio.run(coroutine)
    else:
        asyncio.run(coroutine)
        assert json.loads((tmp_path / "preparation/plan.json").read_text()) == plan
    assert len(calls) == 1
    result = json.loads((tmp_path / "preparation/result.json").read_text())
    assert result["model_request_slots_used"] == 1
    assert result["daytona_sandboxes_created"] == 0
    assert result["scientific_analysis_executed"] is False
    assert result["setup_executed"] is False
    assert result["independent_review_run"] is False


@pytest.mark.parametrize("invalid_syntax", [False, True])
def test_export_code_is_appended_inert_and_syntax_failure_stops(tmp_path, invalid_syntax):
    calls = []
    generated = None
    baseline = None

    async def complete(payload):
        nonlocal generated, baseline
        calls.append(payload)
        context = json.loads(payload["messages"][1]["content"])
        baseline = context["baseline_script"]
        generated = "raise RuntimeError('must not execute')\n"
        candidate = dict(
            disposition="prepare",
            explanation="Synthetic inert preparation fixture",
            export_code="result = (" if invalid_syntax else generated,
            artifacts=[dict(path="value.txt", description="Fixture", source_evidence="Fixture")],
            excluded_outputs=[],
            unresolved_assumptions=[],
        )
        return response(candidate)

    root = tmp_path / "preparation"
    coroutine = run(
        json.loads((HERE / "preparation-inputs.json").read_text()),
        root=root,
        seed=json.loads((HERE / "seeds/current.json").read_text())[0],
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=complete,
    )
    if invalid_syntax:
        with pytest.raises(RuntimeError):
            asyncio.run(coroutine)
        assert len(calls) == 1
        assert not (root / "reference.py").exists()
        draft = json.loads((root / "prepare/artifact-stage/draft.json").read_text())
        assert draft["artifact"]["export_code"] == "result = ("
        assert "valid Python" in draft["validation_error"]
        assert (root / "prepare/artifact-stage/trace/1/response.json").exists()
        result = json.loads((root / "result.json").read_text())
        assert result["status"] == "incomplete"
        assert result["model_request_slots_used"] == 1
        assert result["scientific_analysis_executed"] is False
        return
    asyncio.run(coroutine)
    assert len(calls) == 1
    assert (root / "exports.py").read_text() == generated
    assert (root / "reference.py").read_text() == baseline + "\n\n" + generated
    assert "+raise RuntimeError" in (root / "source.diff").read_text()
    render(root)
    rendered = (root / "plan.md").read_text()
    assert "Worker-returned export code" in rendered
    assert "Controller-assembled reference script" in rendered
    assert "Python dependencies" not in rendered and "Setup script" not in rendered
    for filename in ("pyproject.toml", "stage-inputs.sh", "setup.sh"):
        assert not (root / filename).exists()
    result = json.loads((root / "result.json").read_text())
    assert result["status"] == "ready_for_user_inspection"
    assert result["setup_executed"] is False
    assert result["scientific_analysis_executed"] is False
    assert result["independent_review_run"] is False
    assert result["daytona_sandboxes_created"] == 0


def test_more_than_one_repair_is_rejected_before_request(tmp_path):
    config = json.loads((HERE / "preparation-inputs.json").read_text())
    config["max_requests"] = 3
    root = tmp_path / "preparation"
    with pytest.raises(ValueError, match="at most one validation repair"):
        asyncio.run(
            run(
                config,
                root=root,
                seed={},
                endpoint="unused",
                credential="unused",
                deadline=time.time() + 60,
            )
        )
    assert not root.exists()


@pytest.mark.parametrize("defect", ["empty_inventory", "syntax", "malformed_json"])
def test_one_repair_uses_validation_feedback_and_preserves_both_responses(tmp_path, defect):
    config = json.loads((HERE / "preparation-inputs.json").read_text())
    config["max_requests"] = 2
    calls = []
    plan = dict(
        disposition="prepare",
        explanation="Inert synthetic fixture",
        export_code="raise RuntimeError('must not execute')\n",
        artifacts=[dict(path="value.txt", description="Fixture", source_evidence="Fixture")],
        excluded_outputs=[],
        unresolved_assumptions=[],
    )

    async def complete(payload):
        calls.append(payload)
        candidate = {**plan}
        if len(calls) == 1:
            if defect == "empty_inventory":
                candidate["artifacts"] = []
            elif defect == "syntax":
                candidate["export_code"] = "result = ("
            else:
                reply = response(candidate)
                reply["choices"][0]["message"]["content"] = "{"
                return reply
        else:
            assert payload["messages"][:2] == calls[0]["messages"][:2]
            feedback = payload["messages"][-1]["content"]
            assert "corrected artifact" in feedback
            assert "rejected" in feedback.lower()
        return response(candidate)

    root = tmp_path / "preparation"
    asyncio.run(
        run(
            config,
            root=root,
            seed=json.loads((HERE / "seeds/current.json").read_text())[0],
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    assert len(calls) == 2
    assert json.loads((root / "plan.json").read_text()) == plan
    assert (root / "exports.py").read_text() == plan["export_code"]
    assert (root / "prepare/artifact-stage/trace/1/response.json").is_file()
    assert (root / "prepare/artifact-stage/trace/2/response.json").is_file()
    result = json.loads((root / "result.json").read_text())
    assert result["model_request_slots_used"] == 2
    assert result["scientific_analysis_executed"] is False
    assert result["daytona_sandboxes_created"] == 0


@pytest.mark.parametrize("mode", ["valid", "invalid_twice", "empty", "timeout", "truncated"])
def test_repair_allowance_does_not_add_transport_or_empty_retries(tmp_path, mode):
    config = json.loads((HERE / "preparation-inputs.json").read_text())
    config["max_requests"] = 2
    calls = []

    async def complete(payload):
        calls.append(payload)
        if mode == "timeout":
            raise TimeoutError("Synthetic transport timeout")
        plan = dict(
            disposition="reject",
            explanation="Fixture rejection",
            export_code="",
            artifacts=[],
            excluded_outputs=[],
            unresolved_assumptions=[],
        )
        if mode == "invalid_twice":
            plan.pop("disposition")
        reply = response(plan, "length" if mode == "truncated" else "stop")
        if mode == "empty":
            reply["choices"][0]["message"]["content"] = None
        return reply

    root = tmp_path / "preparation"
    action = run(
        config,
        root=root,
        seed=json.loads((HERE / "seeds/current.json").read_text())[0],
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=complete,
    )
    if mode == "valid":
        asyncio.run(action)
    else:
        with pytest.raises(RuntimeError):
            asyncio.run(action)
    assert len(calls) == (2 if mode == "invalid_twice" else 1)
    result = json.loads((root / "result.json").read_text())
    assert result["model_request_slots_used"] == len(calls)
    assert result["scientific_analysis_executed"] is False
