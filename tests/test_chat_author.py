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


def make_author(
    tmp_path,
    complete,
    *,
    requests=4,
    token_allowance=16000,
    output_format="tools",
    context_recovery_notice=None,
    **limits,
):
    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    ledger = RequestLedger(
        tmp_path / "requests.sqlite", {"design": Allowance(requests, token_allowance)}
    )
    author = GLMChatAuthor(
        complete=complete,
        save_record=save,
        ledger=ledger,
        scope="design",
        deadline=time.time() + 60,
        limits=ChatLimits(**limits),
        output_format=output_format,
        context_recovery_notice=context_recovery_notice,
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


def test_optional_size_limits_preserve_evidence_and_one_repair(tmp_path):
    payloads = []

    async def complete(payload):
        payloads.append(deepcopy(payload))
        answer = reply(call_id=str(len(payloads)))
        answer["choices"][0]["message"]["reasoning_content"] = "r" * 2_000_001
        return answer

    async def submit(**_kwargs):
        return "Rejected: " + "feedback" * 4000 if len(payloads) == 1 else "Artifact committed."

    author, _ = make_author(
        tmp_path,
        complete,
        requests=2,
        token_allowance=None,
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=None,
        reasoning_effort="medium",
    )
    args = options(tmp_path, {"submit_artifact": submit, "revise_artifact": committed}, turns=2)
    args["prompt"] = "s" * 256001
    result = asyncio.run(author(**args))
    assert result["turns"] == 2
    assert all("max_tokens" not in payload for payload in payloads)
    assert payloads[0]["chat_template_kwargs"] == {"reasoning_effort": "medium"}
    assert payloads[1]["messages"][-1]["content"] == "Rejected: " + "feedback" * 4000
    recorded = json.loads((tmp_path / "trace/1/response.json").read_text())
    assert len(recorded["choices"][0]["message"]["reasoning_content"]) == 2_000_001


def test_omitting_generation_cap_cannot_bypass_bounded_ledger(tmp_path):
    async def complete(_payload):
        pytest.fail("Must fail before dispatch")

    with pytest.raises(ValueError, match="ledger allowance"):
        make_author(tmp_path, complete, max_output_tokens=None)


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


@pytest.mark.parametrize("output_format", ["json_schema", "json_unconstrained"])
def test_json_schema_repair_resubmits_entire_object_without_merge(tmp_path, output_format):
    payloads, submissions = [], []

    async def complete(payload):
        payloads.append(deepcopy(payload))
        artifact = {"old": 1} if len(payloads) == 1 else {"new": 2}
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(artifact),
                        "reasoning": "kept",
                    },
                }
            ]
        }

    async def submit(**artifact):
        submissions.append(artifact)
        if len(submissions) == 1:
            return "Artifact rejected; call revise_artifact with only changed fields, or submit_artifact for a complete replacement: new required"
        return "Artifact committed."

    async def forbidden(**kwargs):
        pytest.fail("Merge-patch handler must not be called")

    author, _ = make_author(tmp_path, complete, requests=2, output_format=output_format)
    result = asyncio.run(
        author(
            **options(tmp_path, {"submit_artifact": submit, "revise_artifact": forbidden}, turns=2)
        )
    )
    assert result["turns"] == 2
    assert submissions == [{"old": 1}, {"new": 2}]
    assert all("tools" not in p and "tool_choice" not in p for p in payloads)
    if output_format == "json_schema":
        assert payloads[0]["response_format"] == payloads[1]["response_format"]
        assert payloads[0]["response_format"]["json_schema"]["strict"] is True
    else:
        assert all("response_format" not in p for p in payloads)
    assert payloads[1]["messages"][2]["reasoning"] == "kept"
    assert "new required" in payloads[1]["messages"][-1]["content"]
    assert "revise_artifact" not in payloads[1]["messages"][-1]["content"]


@pytest.mark.parametrize("kind", ["tool", "length", "refusal"])
@pytest.mark.parametrize("output_format", ["json_schema", "json_unconstrained"])
def test_json_schema_incomplete_or_wrong_response_never_submits(tmp_path, kind, output_format):
    async def complete(payload):
        r = reply(finish="length" if kind == "length" else "stop")
        if kind == "refusal":
            r["choices"][0]["message"].update(refusal="refused", tool_calls=None)
        return r

    async def forbidden(**kwargs):
        pytest.fail("Must not submit invalid response")

    author, _ = make_author(tmp_path, complete, output_format=output_format)
    with pytest.raises(IncompleteCompletion):
        asyncio.run(
            author(
                **options(tmp_path, {"submit_artifact": forbidden, "revise_artifact": forbidden})
            )
        )


def test_uncapped_session_records_requests_and_keeps_tools_available(tmp_path):
    calls = []

    async def complete(payload):
        calls.append(payload)
        if len(calls) <= 21:
            assert "shell" in [t["function"]["name"] for t in payload["tools"]]
            return reply("shell", {"command": "inspect"}, call_id=str(len(calls)))
        return reply(call_id=str(len(calls)))

    async def shell(command):
        assert command == "inspect"
        return "observed"

    author, ledger = make_author(tmp_path, complete, requests=None)
    result = asyncio.run(
        author(
            **options(
                tmp_path,
                {
                    "shell": shell,
                    "submit_artifact": committed,
                    "revise_artifact": committed,
                },
                turns=None,
            )
        )
    )
    assert result["turns"] == 22
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 22


def test_uncapped_session_still_stops_at_deadline(tmp_path):
    async def complete(_payload):
        pytest.fail("Expired session must not call the model")

    author, _ = make_author(tmp_path, complete, requests=None)
    author.deadline = time.time() - 1
    with pytest.raises(TimeoutError, match="deadline exhausted"):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {
                        "submit_artifact": committed,
                        "revise_artifact": committed,
                    },
                    turns=None,
                )
            )
        )


def test_received_provider_rejection_is_classified_without_private_body_or_retry(tmp_path):
    class ProviderRejected(Exception):
        status_code = 400
        body = {
            "error": {"message": "maximum context length exceeded PRIVATE_ENDPOINT_AND_CREDENTIAL"}
        }

    calls = []

    async def complete(_payload):
        calls.append(1)
        raise ProviderRejected("PRIVATE_EXCEPTION")

    author, ledger = make_author(tmp_path, complete, requests=1)
    args = options(tmp_path, {"submit_artifact": committed, "revise_artifact": committed})
    with pytest.raises(RuntimeError, match="provider rejected"):
        asyncio.run(author(**args))
    assert calls == [1]
    receipt = json.loads((tmp_path / "trace/1/failure.json").read_text())
    assert receipt["http_status"] == 400
    assert receipt["failure_category"] == "provider_context_length"
    assert receipt["request_slot_retained"]
    assert "PRIVATE" not in json.dumps(receipt)
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT state FROM calls").fetchall() == [("http_error_received",)]
    with pytest.raises(RuntimeError, match="allowance exhausted"):
        asyncio.run(author(**args))
    assert calls == [1]


def test_explicit_tool_preview_keeps_full_output_and_does_not_cap_generation(tmp_path):
    payloads = []
    full = "A" * 8000 + "middle" * 10000 + "Z" * 16000

    async def complete(payload):
        payloads.append(deepcopy(payload))
        return (
            reply("shell", {"command": "inspect"}) if len(payloads) == 1 else reply(call_id="done")
        )

    async def shell(**kwargs):
        return full

    author, _ = make_author(
        tmp_path,
        complete,
        token_allowance=None,
        max_output_tokens=None,
        max_input_bytes=None,
        max_response_bytes=None,
        tool_output_chars=24000,
    )
    asyncio.run(
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
    preview = payloads[1]["messages"][-1]["content"]
    assert preview.startswith("A" * 8000) and preview.endswith("Z" * 16000)
    assert "truncated" in preview and len(preview) < 24100
    assert "max_tokens" not in payloads[1]
    recorded = json.loads((tmp_path / "trace/1/tool-result.json").read_text())
    assert recorded["output"] == full
    events = [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]
    event = next(event for event in events if event["kind"] == "tool_result")
    assert event["truncated"] is True and event["output"] == preview
    assert event["raw_result_record"] == "trace/1/tool-result.json"


@pytest.mark.parametrize("name", ["submit_artifact", "revise_artifact"])
def test_commit_success_survives_short_tool_preview(tmp_path, name):
    calls = []

    async def complete(payload):
        calls.append(payload)
        return reply(name=name)

    async def submit(**kwargs):
        return "Artifact committed. " + "details " * 100

    author, _ = make_author(tmp_path, complete, tool_output_chars=48)
    result = asyncio.run(
        author(**options(tmp_path, {"submit_artifact": submit, "revise_artifact": submit}, turns=2))
    )
    assert result["turns"] == 1
    assert len(calls) == 1
    assert "truncated" in result["messages"][-1]["content"]


class ContextRejected(Exception):
    status_code = 400
    body = {"error": {"message": "maximum context length exceeded PRIVATE_PROVIDER_DETAIL"}}


def test_explicit_context_recovery_preserves_candidates_and_accounting(tmp_path):
    payloads, actions = [], []

    async def complete(payload):
        payloads.append(deepcopy(payload))
        index = len(payloads)
        if index == 4:
            raise ContextRejected()
        name = {1: "submit_artifact", 2: "revise_artifact", 3: "shell", 5: "revise_artifact"}[index]
        return reply(name, {"value": index}, call_id=str(index))

    async def handler(**arguments):
        actions.append(arguments["value"])
        if arguments["value"] == 3:
            return "exploratory output " * 3000
        if arguments["value"] == 5:
            return "Artifact committed."
        return "Candidate rejected: fixture feedback"

    author, ledger = make_author(
        tmp_path,
        complete,
        requests=5,
        context_recovery_notice="Explicit context restart",
        tool_output_chars=None,
    )
    args = options(
        tmp_path,
        {name: handler for name in ("shell", "submit_artifact", "revise_artifact")},
        turns=5,
    )
    result = asyncio.run(author(**args))
    assert result["turns"] == 5 and actions == [1, 2, 3, 5]
    recovered = payloads[-1]["messages"]
    assert recovered[:2] == payloads[0]["messages"]
    assert recovered[2]["content"] == "Explicit context restart"
    assert [m["tool_calls"][0]["function"]["name"] for m in recovered if "tool_calls" in m] == [
        "submit_artifact",
        "revise_artifact",
    ]
    assert [m["tool_call_id"] for m in recovered if m["role"] == "tool"] == ["1", "2"]
    assert "exploratory output" not in json.dumps(recovered)
    assert "exploratory output" in (tmp_path / "trace/3/tool-result.json").read_text()
    assert args["budget"].settlements == ["1", "2", "3", "4", "5"]
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT state FROM calls ORDER BY id").fetchall() == [
            ("response_received",),
            ("response_received",),
            ("response_received",),
            ("http_error_received",),
            ("response_received",),
        ]
    events = [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert [e for e in events if e["kind"] == "context_restarted"][0]["allowance_reset"] is False


@pytest.mark.parametrize("failure", [ContextRejected, TimeoutError])
def test_context_recovery_cannot_retry_original_input_or_uncertain_transport(tmp_path, failure):
    calls = []

    async def complete(payload):
        calls.append(deepcopy(payload))
        raise failure()

    author, _ = make_author(tmp_path, complete, context_recovery_notice="Restart notice")
    with pytest.raises(RuntimeError):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {name: committed for name in ("shell", "submit_artifact", "revise_artifact")},
                )
            )
        )
    assert len(calls) == 1


def test_context_restart_keeps_only_latest_complete_submission_chain():
    from biotasks.chat_author import _restart_context

    messages = [{"role": "system", "content": "instructions"}, {"role": "user", "content": "input"}]
    for index, name in enumerate(
        (
            "submit_artifact",
            "revise_artifact",
            "shell",
            "submit_artifact",
            "revise_artifact",
            "shell",
        )
    ):
        messages.append(reply(name, call_id=str(index))["choices"][0]["message"])
        messages.append(
            {"role": "tool", "tool_call_id": str(index), "content": "observation" * 100}
        )
    recovered = _restart_context(messages, "restart")
    assert recovered is not None
    assert [m["tool_call_id"] for m in recovered if m["role"] == "tool"] == ["3", "4"]


def test_context_recovery_does_not_add_request_slots(tmp_path):
    async def complete(payload):
        if len(payload["messages"]) == 2:
            return reply("shell")
        raise ContextRejected()

    async def shell():
        return "observation" * 100

    author, ledger = make_author(tmp_path, complete, requests=2, context_recovery_notice="Restart")
    with pytest.raises(RuntimeError, match="allowance exhausted"):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {"shell": shell, "submit_artifact": committed, "revise_artifact": committed},
                    turns=None,
                )
            )
        )
    with sqlite3.connect(ledger.path) as db:
        assert db.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 2


@pytest.mark.parametrize("kind", ["transport", "server"])
def test_context_recovery_never_retries_uncertain_or_server_errors_after_tools(tmp_path, kind):
    calls = []

    class ServerError(ContextRejected):
        status_code = 500

    async def complete(payload):
        calls.append(deepcopy(payload))
        if len(calls) == 1:
            return reply("shell")
        raise TimeoutError() if kind == "transport" else ServerError()

    async def shell():
        return "observation" * 100

    author, _ = make_author(tmp_path, complete, context_recovery_notice="Restart")
    with pytest.raises(RuntimeError):
        asyncio.run(
            author(
                **options(
                    tmp_path,
                    {"shell": shell, "submit_artifact": committed, "revise_artifact": committed},
                )
            )
        )
    assert len(calls) == 2
    assert '"kind": "context_restarted"' not in (tmp_path / "trace.jsonl").read_text()


def test_echoed_context_words_are_not_a_provider_context_rejection():
    from biotasks.chat_author import provider_failure

    class Rejected(Exception):
        status_code = 400
        body = {
            "error": {"message": "Invalid request", "request": "maximum context length exceeded"}
        }

    assert provider_failure(Rejected())["failure_category"] == "provider_http_error"
