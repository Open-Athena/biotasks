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


@pytest.mark.parametrize("mode", ["valid", "spent", "scope", "syntax", "empty", "timeout"])
def test_runtime_repair_shares_original_allowance_and_preserves_inputs(tmp_path, mode):
    import sqlite3

    from reference_setup import PreparedReference
    from run_preparation import repair_runtime_exports

    config = json.loads((HERE / "preparation-inputs.json").read_text())
    config["max_requests"] = 2
    plan = dict(
        disposition="prepare",
        explanation="Synthetic fixture",
        export_code="print(result)\n",
        artifacts=[dict(path="result.txt", description="Fixture", source_evidence="Fixture")],
        excluded_outputs=[],
        unresolved_assumptions=[],
    )
    calls = []

    async def complete(payload):
        calls.append(payload)
        candidate = {**plan}
        if mode == "spent" and len(calls) == 1:
            candidate["export_code"] = "("
        return response(candidate)

    original = tmp_path / "preparation"
    asyncio.run(
        run(
            config,
            root=original,
            seed=json.loads((HERE / "seeds/current.json").read_text())[0],
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 60,
            complete=complete,
        )
    )
    originals = {
        p.relative_to(original): p.read_bytes()
        for p in original.rglob("*")
        if p.is_file() and p.suffix not in {".sqlite"}
    }
    repairs = []

    async def correct(payload):
        repairs.append(payload)
        assert payload["response_format"]["type"] == "json_schema"
        context = json.loads(payload["messages"][1]["content"])
        assert context["runtime_validation"]["previous_plan"] == plan
        candidate = {**plan, "export_code": "print('corrected export')\n"}
        if mode == "scope":
            candidate["excluded_outputs"] = ["Drop a scientific branch"]
        if mode == "syntax":
            candidate["export_code"] = "("
        if mode == "timeout":
            raise TimeoutError("Synthetic runtime-repair transport failure")
        reply = response(candidate)
        if mode == "empty":
            reply["choices"][0]["message"]["content"] = None
        return reply

    action = repair_runtime_exports(
        original=original,
        feedback={"kind": "runtime_export_exception", "execution": "fixture"},
        endpoint="unused",
        credential="unused",
        deadline=time.time() + 60,
        complete=correct,
    )
    if mode in {"valid", "spent"}:
        effective = asyncio.run(action)
        if mode == "valid":
            fixed = PreparedReference.load(effective)
            assert fixed.baseline == PreparedReference.load(original).baseline
            assert fixed.exports == "print('corrected export')\n"
            assert len(repairs) == 1
        else:
            assert effective is None and not repairs
    else:
        with pytest.raises(RuntimeError):
            asyncio.run(action)
        assert len(repairs) == 1
    # No additional request is available, even after a failed/uncertain repair.
    assert (
        asyncio.run(
            repair_runtime_exports(
                original=original,
                feedback={},
                endpoint="unused",
                credential="unused",
                deadline=time.time() + 60,
                complete=correct,
            )
        )
        is None
    )
    with sqlite3.connect(original / "requests.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 2
    for relative, data in originals.items():
        assert (original / relative).read_bytes() == data
