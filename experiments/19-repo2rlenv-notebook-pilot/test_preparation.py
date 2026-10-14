"""Preparation-only boundary tests using a fake model and the real controller."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from run_preparation import run

HERE = Path(__file__).parent


def response(plan, finish="stop", call_id="call"):
    return {"choices": [{"finish_reason": finish, "message": {
        "role": "assistant", "content": json.dumps(plan),
    }}]}


@pytest.mark.parametrize("mode", ["accepted", "truncated", "structural_repair", "twice_invalid"])
def test_only_preparation_no_output_recovery(tmp_path, mode):
    calls = []
    plan = dict(disposition="reject", explanation="Unknown dependency", environment_rationale="",
                pyproject_toml="", system_packages=[], stage_inputs_sh="", changes=[], artifacts=[], branches=[], excluded_outputs=[],
                unresolved_assumptions=["Dependency availability"])

    async def complete(payload):
        calls.append(payload)
        assert "tools" not in payload
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert "changes" in payload["response_format"]["json_schema"]["schema"]["required"]
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
