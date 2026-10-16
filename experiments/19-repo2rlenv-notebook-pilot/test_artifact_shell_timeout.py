"""Tool-advertised and enforced computation allowances agree."""

import time

import pytest
from pydantic import BaseModel
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author import artifact
from repo2rlenv.tasksmith.author.budget import AuthorBudget


class Output(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_long_foreground_call_and_over_limit_rejection(tmp_path, monkeypatch):
    seen = []

    async def shell(*, command, timeout_sec):
        seen.append((command, timeout_sec))
        return "done"

    async def agent(**kwargs):
        tool = next(t for t in kwargs["tools"] if t["function"]["name"] == "shell")
        assert tool["function"]["parameters"]["properties"]["timeout_sec"]["maximum"] == 600
        await kwargs["handlers"]["shell"]("compute", timeout_sec=300)
        with pytest.raises(ValueError, match="stage allowance"):
            await kwargs["handlers"]["shell"]("compute", timeout_sec=601)
        assert "committed" in await kwargs["handlers"]["submit_artifact"](value=1)

    monkeypatch.setattr(artifact, "run_agent", agent)
    budget = RunBudget(BudgetLedger(tmp_path / "budget.sqlite", limit_usd="1"), "test", "1")
    result = await artifact.artifact_stage(
        schema=Output,
        stage="test",
        inputs={},
        system="test",
        prompt="test",
        root=tmp_path / "stage",
        budget=AuthorBudget(budget, tmp_path / "charges", "test"),
        model="test",
        runtime="test",
        max_cost=1,
        max_turns=2,
        deadline=time.time() + 1000,
        shell=shell,
        shell_timeout_sec=600,
    )
    assert result.value == 1 and seen == [("compute", 300)]
    # Per-stage schema mutation must not alter upstream's default for other callers.
    assert (
        artifact.SHELL_TOOL["function"]["parameters"]["properties"]["timeout_sec"]["maximum"] == 120
    )
