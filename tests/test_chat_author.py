import asyncio
import json
import sqlite3
import time
from copy import deepcopy

import pytest

from biotasks.chat_author import ChatLimits, GLMChatAuthor, IncompleteCompletion
from biotasks.inference_gate import Allowance, RequestLedger


def reply(name="submit_artifact", arguments=None, *, finish="tool_calls", call_id="call-1"):
    return {
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": "retained reasoning",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments or {}),
                            },
                        }
                    ],
                },
            }
        ],
    }


class Budget:
    def __init__(self):
        self.reservations, self.settlements = [], []

    def reserve(self, amount, description):
        assert amount == 0.000001
        self.reservations.append(description)
        return str(len(self.reservations))

    def settle(self, operation, amount):
        assert amount == 0
        self.settlements.append(operation)


def make_author(tmp_path, complete, *, requests=4, **limits):
    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    ledger = RequestLedger(tmp_path / "requests.sqlite", {"design": Allowance(requests, 16000)})
    author = GLMChatAuthor(
        complete=complete,
        save_record=save,
        ledger=ledger,
        scope="design",
        deadline=time.time() + 60,
        limits=ChatLimits(**limits),
    )
    return author, ledger


def options(tmp_path, handlers, *, turns=4):
    return {
        "model": "glm-5.3",
        "runtime": "biotasks-glm-chat-v1",
        "system": "Design from evidence",
        "prompt": "Source material",
        "budget": Budget(),
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "parameters": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
            }
            for name in handlers
        ],
        "handlers": handlers,
        "trace": tmp_path / "trace.jsonl",
        "max_turns": turns,
        "max_cost": 1,
    }


async def committed(**_kwargs):
    return "Artifact committed."


@pytest.mark.parametrize("reasoning_field", ["reasoning_content", "reasoning"])
def test_preserves_reasoning_and_links_tools_until_submission(tmp_path, reasoning_field):
    payloads = []

    async def complete(payload):
        payloads.append(deepcopy(payload))
        answer = (
            reply("shell", {"command": "inspect"}) if len(payloads) == 1 else reply(call_id="done")
        )
        if reasoning_field == "reasoning":
            message = answer["choices"][0]["message"]
            message["reasoning"] = message.pop("reasoning_content")
        return answer

    observed = []

    async def shell(command):
        observed.append(command)
        return "shape measured"

    author, _ = make_author(tmp_path, complete)
    result = asyncio.run(
        author(
            **options(
                tmp_path,
                {
                    "shell": shell,
                    "submit_artifact": committed,
                    "revise_artifact": committed,
                },
            )
        )
    )
    assert result["turns"] == 2 and observed == ["inspect"]
    assert payloads[1]["messages"][2][reasoning_field] == "retained reasoning"
    assert payloads[1]["messages"][3] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "shape measured",
    }
    recorded = json.loads((tmp_path / "trace/1/response.json").read_text())
    assert recorded["choices"][0]["message"][reasoning_field] == "retained reasoning"


@pytest.mark.parametrize("finish", ["length", "content_filter", None])
def test_partial_or_filtered_response_never_executes_a_tool(tmp_path, finish):
    response = reply(finish=finish)

    async def complete(_payload):
        return response

    async def forbidden(**_kwargs):
        pytest.fail("Incomplete response executed a tool")

    author, ledger = make_author(tmp_path, complete)
    with pytest.raises(IncompleteCompletion):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {
                        "submit_artifact": forbidden,
                        "revise_artifact": forbidden,
                    },
                )
            )
        )
    assert json.loads((tmp_path / "trace/1/response.json").read_text()) == response
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT state FROM calls").fetchall() == [("response_received",)]


def test_uncertain_transport_consumes_slot_without_retry_or_private_exception(tmp_path):
    calls = []

    async def complete(_payload):
        calls.append(1)
        raise ConnectionError("PRIVATE_ENDPOINT_AND_CREDENTIAL")

    author, ledger = make_author(tmp_path, complete, requests=1)
    args = options(tmp_path, {"submit_artifact": committed, "revise_artifact": committed})
    with pytest.raises(RuntimeError, match="transport failed") as error:
        asyncio.run(author(**args))
    assert "PRIVATE" not in str(error.value)
    with pytest.raises(RuntimeError, match="allowance exhausted"):
        asyncio.run(author(**args))
    assert calls == [1]
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT state FROM calls").fetchall() == [("uncertain",)]
    assert "PRIVATE" not in (tmp_path / "trace/1/failure.json").read_text()


def test_last_two_calls_reserve_submission_even_if_model_asks_for_shell(tmp_path):
    payloads = []

    async def complete(payload):
        payloads.append(deepcopy(payload))
        return reply("shell", {"command": "must not run"}, call_id=str(len(payloads)))

    async def forbidden(**_kwargs):
        pytest.fail("Shell executed during reserved submission turns")

    author, _ = make_author(tmp_path, complete)
    with pytest.raises(RuntimeError, match="exhausted"):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {
                        "shell": forbidden,
                        "submit_artifact": committed,
                        "revise_artifact": committed,
                    },
                    turns=2,
                )
            )
        )
    assert len(payloads) == 2
    assert all("shell" not in [x["function"]["name"] for x in p["tools"]] for p in payloads)


def test_oversized_context_refuses_dispatch_and_retains_quota(tmp_path):
    async def forbidden(_payload):
        pytest.fail("Oversized context reached transport")

    author, ledger = make_author(tmp_path, forbidden, max_input_bytes=10)
    with pytest.raises(ValueError, match="context"):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {
                        "submit_artifact": committed,
                        "revise_artifact": committed,
                    },
                )
            )
        )
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone() == (0,)
