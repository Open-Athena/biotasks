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
    return {"choices": [{"finish_reason": finish, "message": {
        "role": "assistant", "content": json.dumps(plan),
    }}]}


@pytest.mark.parametrize("mode", ["accepted", "truncated", "structural_repair", "twice_invalid"])
def test_only_preparation_no_output_recovery(tmp_path, mode):
    calls = []
    plan = dict(disposition="reject", explanation="No eligible terminal result",
                export_code="", artifacts=[], excluded_outputs=["Plot-only result"],
                unresolved_assumptions=[])

    async def complete(payload):
        calls.append(payload)
        assert "tools" not in payload
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert "export_code" in payload["response_format"]["json_schema"]["schema"]["required"]
        properties = payload["response_format"]["json_schema"]["schema"]["properties"]
        assert not {"environment_rationale", "pyproject_toml", "system_packages", "stage_inputs_sh"} & properties.keys()
        context = json.loads(payload["messages"][1]["content"])
        assert set(context) == {"source", "baseline_script", "conversion", "limits"}
        assert "question_text" not in context["source"]
        assert "max_tokens" not in payload
        candidate = dict(plan)
        if mode == "twice_invalid" or (mode == "structural_repair" and len(calls) == 1):
            candidate.pop("disposition")
        return response(candidate, "length" if mode == "truncated" else "stop", str(len(calls)))

    coroutine = run(
        json.loads((HERE / "preparation-inputs.json").read_text()),
        root=tmp_path / "preparation",
        seed=json.loads((HERE / "seeds/current.json").read_text())[0],
        endpoint="unused", credential="unused", deadline=time.time() + 60, complete=complete,
    )
    if mode in {"truncated", "twice_invalid"}:
        with pytest.raises(RuntimeError):
            asyncio.run(coroutine)
    else:
        asyncio.run(coroutine)
        assert json.loads((tmp_path / "preparation/plan.json").read_text()) == plan
    assert len(calls) == (2 if mode in {"structural_repair", "twice_invalid"} else 1)
    result = json.loads((tmp_path / "preparation/result.json").read_text())
    assert result["daytona_sandboxes_created"] == 0
    assert result["scientific_analysis_executed"] is False
    assert result["setup_executed"] is False
    assert result["independent_review_run"] is False


@pytest.mark.parametrize("repair_syntax", [False, True])
def test_export_code_is_appended_inert_and_syntax_failure_gets_one_repair(tmp_path, repair_syntax):
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
            disposition="prepare", explanation="Synthetic inert preparation fixture",
            export_code="result = (" if repair_syntax and len(calls) == 1 else generated,
            artifacts=[dict(path="value.txt", description="Fixture", source_evidence="Fixture")],
            excluded_outputs=[], unresolved_assumptions=[],
        )
        if len(calls) == 2:
            assert "valid Python" in payload["messages"][-1]["content"]
            assert "complete corrected artifact" in payload["messages"][-1]["content"]
        return response(candidate)

    root = tmp_path / "preparation"
    asyncio.run(run(
        json.loads((HERE / "preparation-inputs.json").read_text()),
        root=root, seed=json.loads((HERE / "seeds/current.json").read_text())[0],
        endpoint="unused", credential="unused", deadline=time.time() + 60, complete=complete,
    ))
    assert len(calls) == (2 if repair_syntax else 1)
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
