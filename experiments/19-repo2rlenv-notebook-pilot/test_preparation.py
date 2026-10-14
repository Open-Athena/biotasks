"""Preparation-only boundary tests using a fake model and the real controller."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from run_preparation import run

HERE = Path(__file__).parent


def response(plan, finish="tool_calls"):
    return {"choices": [{"finish_reason": finish, "message": {
        "role": "assistant", "content": None, "tool_calls": [{
            "id": "call", "type": "function", "function": {
                "name": "submit_artifact", "arguments": json.dumps(plan),
            },
        }],
    }}]}


@pytest.mark.parametrize("truncated", [False, True])
def test_only_preparation_no_output_recovery(tmp_path, truncated):
    calls = []
    plan = dict(disposition="reject", explanation="Unknown dependency", environment_rationale="",
                setup_sh="", changes=[], artifacts=[], branches=[], excluded_outputs=[],
                unresolved_assumptions=["Dependency availability"])

    async def complete(payload):
        calls.append(payload)
        assert {tool["function"]["name"] for tool in payload["tools"]} == {
            "submit_artifact", "revise_artifact",
        }
        context = json.loads(payload["messages"][1]["content"])
        assert set(context) == {"source", "baseline_script", "conversion", "limits"}
        assert "question_text" not in context["source"]
        assert "max_tokens" not in payload
        return response(plan, "length" if truncated else "tool_calls")

    coroutine = run(
        json.loads((HERE / "preparation-inputs.json").read_text()),
        root=tmp_path / "preparation",
        seed=json.loads((HERE / "seeds/current.json").read_text())[0],
        endpoint="unused", credential="unused", deadline=time.time() + 60, complete=complete,
    )
    if truncated:
        with pytest.raises(RuntimeError):
            asyncio.run(coroutine)
    else:
        asyncio.run(coroutine)
        assert json.loads((tmp_path / "preparation/plan.json").read_text()) == plan
    assert len(calls) == 1
    result = json.loads((tmp_path / "preparation/result.json").read_text())
    assert result["daytona_sandboxes_created"] == 0
    assert result["scientific_analysis_executed"] is False
    assert result["setup_executed"] is False
    assert result["independent_review_run"] is False
