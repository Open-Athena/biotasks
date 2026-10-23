"""Exercise the real upstream controller using scripted model/remote responses."""

import asyncio
import json
import time
from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest
from design_stage import completion_transport, design_notebook, remote_shell
from openai import AsyncOpenAI
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.quality.loop.client import RunBudget
from repo2rlenv.tasksmith.author.budget import AuthorBudget

from biotasks.chat_author import ChatLimits, ModelConnectionError, OutputTokenLimit


def response(name, payload, index):
    return {
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": "keep",
                    "tool_calls": [
                        {
                            "id": f"call-{index}",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(payload),
                            },
                        }
                    ],
                },
            }
        ],
        "id": "fake",
        "object": "chat.completion",
        "created": 0,
        "model": "glm-5.3",
    }


class Worker:
    def __init__(self):
        self.commands = []

    def exec(self, argv, **kwargs):
        self.commands.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="measured fact", stderr="")


def test_upstream_validates_revision_and_reuses_completed_stage_without_model(tmp_path):
    requests = []
    draft = "A source-grounded scientific task. " * 5
    responses = [
        response("shell", {"command": "inspect input", "timeout_sec": 10}, 1),
        response("submit_artifact", {"core_capabilities": [], "draft_spec": draft}, 2),
        response("revise_artifact", {"patch": {"core_capabilities": ["analysis"]}}, 3),
    ]

    async def complete(payload):
        requests.append(deepcopy(payload))
        return responses[len(requests) - 1]

    worker = Worker()
    root = tmp_path / "design"
    kwargs = dict(
        seed={"question_text": "complete notebook"},
        profile={
            "scientific_analysis_executed": False,
            "files": [{"path": "counts.h5"}],
        },
        workspace={"inputs": "/inputs", "scratch": "/scratch"},
        worker=worker,
        root=root,
        endpoint="https://model.invalid/v1",
        credential="fake",
        budget=AuthorBudget(
            RunBudget(BudgetLedger(tmp_path / "budget.sqlite", limit_usd="1"), "design", "1"),
            tmp_path / "charges",
            "design",
        ),
        deadline=time.time() + 60,
        max_requests=3,
        limits=ChatLimits(),
        complete=complete,
    )
    result = asyncio.run(design_notebook(**kwargs))
    assert result.core_capabilities == ["analysis"] and result.draft_spec == draft
    assert len(requests) == 3 and len(worker.commands) == 1
    assert "rejected" in requests[2]["messages"][-1]["content"]
    artifact = json.loads((root / "stage/artifact.json").read_text())
    assert artifact["artifact"] == result.model_dump()
    assert (
        json.loads((root / "design-result.json").read_text())["scientifically_validated"] is False
    )
    assert asyncio.run(design_notebook(**kwargs)) == result
    assert len(requests) == 3 and len(worker.commands) == 1
    original = (root / "input.json").read_bytes()
    with pytest.raises(ValueError, match="inputs differ"):
        asyncio.run(design_notebook(**{**kwargs, "endpoint": "https://changed.invalid/v1"}))
    assert (root / "input.json").read_bytes() == original


def test_sdk_transmits_glm_reasoning_extension_without_live_network():
    captured = []

    async def fake_http(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response("submit_artifact", {}, 1))

    async def run():
        async with AsyncOpenAI(
            base_url="https://model.invalid/v1",
            api_key="fake",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(fake_http)),
        ) as client:
            result = await completion_transport(client)(
                {
                    "model": "glm-5.3",
                    "messages": [{"role": "user", "content": "input"}],
                    "chat_template_kwargs": {"reasoning_effort": "high"},
                    "parallel_tool_calls": False,
                }
            )
            assert result["choices"][0]["message"]["reasoning_content"] == "keep"

    asyncio.run(run())
    assert len(captured) == 1
    assert captured[0]["chat_template_kwargs"] == {"reasoning_effort": "high"}


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.ReadTimeout])
def test_sdk_normalizes_only_model_connection_errors_without_retry_or_private_details(
    failure,
):
    calls = []

    async def fake_http(request):
        calls.append(request)
        raise failure("PRIVATE_ENDPOINT_OR_CREDENTIAL", request=request)

    async def run():
        async with AsyncOpenAI(
            base_url="https://model.invalid/v1",
            api_key="fake",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(fake_http)),
        ) as client:
            with pytest.raises(ModelConnectionError) as info:
                await completion_transport(client)(
                    {
                        "model": "glm-5.3",
                        "messages": [{"role": "user", "content": "input"}],
                        "chat_template_kwargs": {"reasoning_effort": "high"},
                    }
                )
            assert info.value.sdk_error_type == (
                "APITimeoutError" if failure is httpx.ReadTimeout else "APIConnectionError"
            )
            assert "PRIVATE" not in str(info.value)

    asyncio.run(run())
    assert len(calls) == 1


def test_remote_tools_are_bounded_and_have_no_local_fallback():
    worker = Worker()
    shell = remote_shell(
        worker,
        directory="/scratch with space",
        deadline=time.time() + 60,
        total_seconds=1,
    )
    assert json.loads(asyncio.run(shell("printf value")))["returncode"] == 0
    assert "exhausted" in asyncio.run(shell("must not run"))
    assert len(worker.commands) == 1
    argv, options = worker.commands[0]
    assert argv[:4] == ["timeout", "--signal=TERM", "--kill-after=5", "1s"]
    assert options["timeout"] == 11


def test_lost_remote_result_retains_allowance_and_redacts_private_route():
    class LostWorker:
        def exec(self, *_args, **_kwargs):
            raise ConnectionError("PRIVATE_PROVIDER_ROUTE")

    shell = remote_shell(
        LostWorker(), directory="/scratch", deadline=time.time() + 60, total_seconds=1
    )
    with pytest.raises(RuntimeError, match="reconcile") as error:
        asyncio.run(shell("inspect"))
    assert "PRIVATE" not in str(error.value)
    assert "exhausted" in asyncio.run(shell("must not repeat"))


def test_incomplete_response_retains_stage_and_cannot_auto_replay(tmp_path):
    calls = []

    async def complete(_payload):
        calls.append(1)
        result = response("submit_artifact", {}, 1)
        result["choices"][0]["finish_reason"] = "length"
        return result

    root = tmp_path / "design"
    kwargs = dict(
        seed={"question_text": "source"},
        profile={"scientific_analysis_executed": False, "files": [{"path": "data"}]},
        workspace={"inputs": "/inputs", "scratch": "/scratch"},
        worker=Worker(),
        root=root,
        endpoint="https://model.invalid/v1",
        credential="fake",
        budget=AuthorBudget(
            RunBudget(BudgetLedger(tmp_path / "budget.sqlite", limit_usd="1"), "failed", "1"),
            tmp_path / "charges",
            "failed",
        ),
        deadline=time.time() + 60,
        max_requests=3,
        limits=ChatLimits(),
        complete=complete,
    )
    with pytest.raises(OutputTokenLimit):
        asyncio.run(design_notebook(**kwargs))
    saved = (root / "stage/trace/1/response.json").read_bytes()
    with pytest.raises(RuntimeError, match="reconciliation"):
        asyncio.run(design_notebook(**kwargs))
    assert calls == [1]
    assert (root / "stage/trace/1/response.json").read_bytes() == saved
    assert not (root / "stage/artifact.json").exists()
