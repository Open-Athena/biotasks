"""Bounded GLM Chat Completions transport for an upstream artifact controller.

The caller supplies an async, no-retry transport and controller tool handlers.
This module does not choose a task, validate its science, or launch a sandbox.
Only the approved free GLM model is supported; monetary receipts are zero while
every attempted HTTP request consumes a durable RequestLedger slot.

An explicit generation-retry notice enables one retry after a timeout, typed
model connection failure or transient HTTP 502/503/504 per author instance.
The callback must not execute
tools or other external actions itself.
The uncertain request/hold is retained; tool history and original bounds remain.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from biotasks.inference_gate import RequestLedger


class AuthorBudget(Protocol):
    def reserve(self, amount: float, description: str) -> str: ...

    def settle(self, operation: str, amount: float) -> None: ...


class IncompleteCompletion(RuntimeError):
    """A preserved response cannot execute tools; recovery must be explicit."""


class OutputTokenLimit(IncompleteCompletion):
    """A received and accounted response stopped at the provider's token limit."""


class ModelConnectionError(ConnectionError):
    """The model SDK lost its connection before returning any complete response.

    A transport adapter raises this only around its pure generation request;
    arbitrary tool, filesystem and controller errors must not be normalized here.
    """

    def __init__(self, sdk_error_type: str = "APIConnectionError"):
        if sdk_error_type not in {"APIConnectionError", "APITimeoutError"}:
            raise ValueError("Unsupported model SDK connection failure")
        self.sdk_error_type = sdk_error_type
        super().__init__("Model SDK connection failed")


def provider_failure(error: BaseException) -> dict[str, Any]:
    """Keep useful rejection categories without copying private response text."""
    record: dict[str, Any] = {
        "error_type": type(error).__name__,
        "request_slot_retained": True,
        "failure_category": "transport_uncertain",
    }
    if isinstance(error, ModelConnectionError):
        record["sdk_error_type"] = error.sdk_error_type
    status = getattr(error, "status_code", None)
    if type(status) is not int or not 400 <= status <= 599:
        return record
    record["http_status"] = status
    record["failure_category"] = "provider_http_error"
    body = getattr(error, "body", None)
    # Classify the provider's error, not arbitrary echoed request/input text.
    detail = body.get("error", body) if isinstance(body, dict) else None
    if isinstance(detail, dict):
        detail = {key: detail.get(key) for key in ("message", "code", "type")}
    try:
        text = json.dumps(detail, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        text = ""
    if any(
        term in text
        for term in (
            "context_length_exceeded",
            "maximum context length",
            "max_model_len",
            "context window",
            "too many tokens",
            "prompt is too long",
        )
    ):
        record["failure_category"] = "provider_context_length"
    elif status == 400 and any(
        term in text for term in ("tool_call_id", "tool_calls", "tool call")
    ):
        record["failure_category"] = "provider_tool_protocol"
    elif status in {401, 403}:
        record["failure_category"] = "provider_authentication"
    elif status == 429:
        record["failure_category"] = "provider_rate_limit"
    return record


def _restart_context(messages: list[dict[str, Any]], notice: str) -> list[dict[str, Any]] | None:
    """Keep original instructions and the latest complete candidate/patch chain."""
    artifacts: list[dict[str, Any]] = []
    for index, message in enumerate(messages[2:], start=2):
        calls = message.get("tool_calls", [])
        if message.get("role") != "assistant" or len(calls) != 1:
            continue
        name = calls[0]["function"]["name"]
        if name not in {"submit_artifact", "revise_artifact"}:
            continue
        if index + 1 >= len(messages):
            continue
        feedback = messages[index + 1]
        if feedback.get("role") != "tool" or feedback.get("tool_call_id") != calls[0]["id"]:
            continue
        if name == "submit_artifact":
            artifacts = []
        artifacts.extend([message, feedback])
    reduced = messages[:2] + [{"role": "user", "content": notice}] + artifacts
    if len(json.dumps(reduced, ensure_ascii=False)) >= len(
        json.dumps(messages, ensure_ascii=False)
    ):
        return None
    return reduced


@dataclass(frozen=True)
class ChatLimits:
    max_output_tokens: int | None = 16000
    request_timeout_sec: int = 600
    max_input_bytes: int | None = 256000
    max_response_bytes: int | None = 2000000
    tool_output_chars: int | None = 24000
    reasoning_effort: str = "high"

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key != "request_timeout_sec" and value is None:
                continue
            if key != "reasoning_effort" and (type(value) is not int or value < 1):
                raise ValueError(f"{key} must be a positive integer")
        if self.reasoning_effort not in {"low", "medium", "high", "max"}:
            raise ValueError("Unsupported reasoning effort")


class GLMChatAuthor:
    def __init__(
        self,
        *,
        complete: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        save_record: Callable[[Path, dict[str, Any]], None],
        ledger: RequestLedger,
        scope: str,
        deadline: float,
        limits: ChatLimits,
        output_format: str = "tools",
        context_recovery_notice: str | None = None,
        empty_response_retry_notice: str | None = None,
        generation_retry_notice: str | None = None,
        missing_tool_retry_notice: str | None = None,
        runtime_budget_notice: str | None = None,
    ):
        if not math.isfinite(deadline) or deadline <= time.time():
            raise ValueError("A finite future deadline is required")
        token_bound = ledger.allowances[scope].output_tokens
        if token_bound is not None and (
            limits.max_output_tokens is None or limits.max_output_tokens > token_bound
        ):
            raise ValueError("Output tokens exceed the request ledger allowance")
        if output_format not in {"tools", "json_schema", "json_unconstrained"}:
            raise ValueError("Unsupported artifact output format")
        if context_recovery_notice is not None and not context_recovery_notice.strip():
            raise ValueError("Context recovery requires an explicit notice")
        if empty_response_retry_notice is not None and not empty_response_retry_notice.strip():
            raise ValueError("Empty-response retry requires an explicit notice")
        if generation_retry_notice is not None and not generation_retry_notice.strip():
            raise ValueError("Generation retry requires an explicit notice")
        if missing_tool_retry_notice is not None and not missing_tool_retry_notice.strip():
            raise ValueError("Missing-tool recovery requires an explicit notice")
        if runtime_budget_notice is not None and not all(
            placeholder in runtime_budget_notice
            for placeholder in ("{{REMAINING_SECONDS}}", "{{REQUEST_TIMEOUT_SECONDS}}")
        ):
            raise ValueError("Runtime budget notice requires both timing placeholders")
        self.context_recovery_notice = context_recovery_notice
        self.empty_response_retry_notice = empty_response_retry_notice
        self.generation_retry_notice = generation_retry_notice
        self.missing_tool_retry_notice = missing_tool_retry_notice
        self.runtime_budget_notice = runtime_budget_notice
        # One allowance for this stage instance, including upstream resubmissions.
        self.empty_response_retries_used = 0
        self.generation_retries_used = 0
        self.missing_tool_retries_used = 0
        self.output_format = output_format
        self.complete, self.save_record = complete, save_record
        self.ledger, self.scope, self.deadline, self.limits = ledger, scope, deadline, limits

    async def __call__(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        budget: AuthorBudget,
        tools: list[dict[str, Any]],
        handlers: dict[str, Callable[..., Awaitable[str]]],
        trace: Path,
        max_turns: int | None,
        max_cost: float,
        runtime: str,
    ) -> dict[str, Any]:
        if model != "glm-5.3" or runtime != "biotasks-glm-chat-v1":
            raise ValueError("This adapter supports only the approved GLM runtime")
        if (
            (max_turns is not None and (type(max_turns) is not int or max_turns < 1))
            or not math.isfinite(max_cost)
            or max_cost <= 0
        ):
            raise ValueError("Finite positive stage allowances are required")
        trace.parent.mkdir(parents=True, exist_ok=True)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        names = {tool["function"]["name"] for tool in tools}
        if not {"submit_artifact", "revise_artifact"} <= names or not names <= handlers.keys():
            raise ValueError("Artifact tools and their controller handlers are required")

        submission = next(
            tool["function"] for tool in tools if tool["function"]["name"] == "submit_artifact"
        )

        def event(kind, **data):
            with trace.open("a") as stream:
                stream.write(json.dumps({"kind": kind, **data}, allow_nan=False) + "\n")

        event(
            "input",
            model=model,
            runtime=runtime,
            settings=asdict(self.limits),
            output_format=self.output_format,
        )
        seen_call_ids = set()
        turn = 0
        while max_turns is None or turn < max_turns:
            turn += 1
            remaining = self.deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("Design deadline exhausted")
            available_tools = [
                tool
                for tool in tools
                if max_turns is None
                or max_turns - turn >= 2
                or tool["function"]["name"] in {"submit_artifact", "revise_artifact"}
            ]
            permitted = {tool["function"]["name"] for tool in available_tools}
            request_messages = messages
            if self.runtime_budget_notice is not None:
                notice = self.runtime_budget_notice.replace(
                    "{{REMAINING_SECONDS}}", str(math.floor(remaining))
                ).replace("{{REQUEST_TIMEOUT_SECONDS}}", str(self.limits.request_timeout_sec))
                # Keep the current snapshot at the end of the request, without
                # accumulating obsolete countdowns in the conversation history.
                # The exact sent notice is preserved in the request receipt.
                request_messages = [*messages, {"role": "user", "content": notice}]
            payload = {
                "model": model,
                "messages": request_messages,
                "tools": available_tools,
                "tool_choice": "required",
                "parallel_tool_calls": False,
                "stream": False,
                "temperature": 1.0,
                "top_p": 1.0,
                "chat_template_kwargs": {"reasoning_effort": self.limits.reasoning_effort},
            }
            if self.output_format in {"json_schema", "json_unconstrained"}:
                for key in ("tools", "tool_choice", "parallel_tool_calls"):
                    del payload[key]
            # Diagnostic plain JSON keeps local artifact validation and original
            # responses, but does not request server-side grammar constraints.
            if self.output_format == "json_schema":
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "artifact",
                        "schema": submission["parameters"],
                        "strict": True,
                    },
                }
            # None delegates generation length to the provider/context window;
            # it does not assert that the provider has no limit of its own.
            if self.limits.max_output_tokens is not None:
                payload["max_tokens"] = self.limits.max_output_tokens
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
            if self.limits.max_input_bytes is not None and len(body) > self.limits.max_input_bytes:
                raise ValueError("Design context exceeds its input bound; no silent truncation")
            # The durable claim occurs before dispatch and is never refunded.
            call_id = self.ledger.claim(self.scope, body)
            request_root = trace.with_suffix("") / str(call_id)
            self.save_record(request_root / "request.json", payload)
            # The upstream ledger requires a positive hold. Its smallest unit is
            # one micro-dollar; settle this bookkeeping hold to zero on response.
            operation = budget.reserve(0.000001, f"Free GLM design request {call_id}")
            event("model_request", turn=turn, call_id=call_id, operation=operation)
            started = time.monotonic()
            print(
                json.dumps({"event": "model_request_started", "stage": self.scope, "turn": turn}),
                flush=True,
            )
            try:
                response = await asyncio.wait_for(
                    self.complete(payload),
                    timeout=min(remaining, self.limits.request_timeout_sec),
                )
            except (Exception, asyncio.CancelledError) as exc:
                failure = provider_failure(exc)
                self.save_record(request_root / "failure.json", failure)
                # A received rejection is definite; the attempted slot is retained.
                # Never log raw SDK exception text, endpoints or response bodies.
                if "http_status" in failure:
                    self.ledger.finish(call_id, "http_error_received")
                    if (
                        failure["failure_category"] == "provider_context_length"
                        and failure["http_status"] == 400
                        and self.context_recovery_notice is not None
                        and self.output_format == "tools"
                        and names - {"submit_artifact", "revise_artifact"}
                    ):
                        reduced = _restart_context(messages, self.context_recovery_notice)
                        if reduced is not None:
                            budget.settle(operation, 0.0)
                            event(
                                "context_restarted",
                                rejected_call_id=call_id,
                                previous_messages=len(messages),
                                retained_messages=len(reduced),
                                allowance_reset=False,
                            )
                            messages = reduced
                            continue
                if isinstance(exc, asyncio.CancelledError):
                    raise
                transient_http = failure.get(
                    "failure_category"
                ) == "provider_http_error" and failure.get("http_status") in {502, 503, 504}
                if (
                    (isinstance(exc, (TimeoutError, ModelConnectionError)) or transient_http)
                    and self.generation_retry_notice is not None
                    and self.generation_retries_used == 0
                    and (max_turns is None or turn < max_turns)
                    and time.time() < self.deadline
                ):
                    # Only pure model generation is repeated. No response from
                    # this attempt reached tool dispatch; prior actions/results
                    # stay in the conversation. The original request and its
                    # bookkeeping hold remain uncertain for transport loss.
                    # A received HTTP rejection is accounted separately.
                    self.generation_retries_used += 1
                    if transient_http:
                        budget.settle(operation, 0.0)
                    messages.append({"role": "user", "content": self.generation_retry_notice})
                    event(
                        "generation_retry_requested",
                        **{"rejected_call_id" if transient_http else "uncertain_call_id": call_id},
                        error_type=type(exc).__name__,
                        retry_number=self.generation_retries_used,
                        backend_outcome="http_error_received" if transient_http else "unknown",
                        actions_executed=0,
                        allowance_reset=False,
                    )
                    continue
                if "http_status" in failure:
                    raise RuntimeError(
                        "Model provider rejected the request; inspect the retained receipt"
                    ) from None
                raise RuntimeError("Model transport failed; inspect the retained receipt") from None
            if self.limits.max_response_bytes is not None and (
                len(json.dumps(response, ensure_ascii=False).encode())
                > self.limits.max_response_bytes
            ):
                self.save_record(request_root / "failure.json", {"error_type": "oversize_response"})
                raise IncompleteCompletion("Response exceeds the evidence bound")
            self.save_record(request_root / "response.json", response)
            print(
                json.dumps(
                    {
                        "event": "model_response_received",
                        "stage": self.scope,
                        "turn": turn,
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                    }
                ),
                flush=True,
            )
            self.ledger.finish(call_id, "response_received")
            budget.settle(operation, 0.0)
            event(
                "model_response",
                turn=turn,
                call_id=call_id,
                elapsed_seconds=time.monotonic() - started,
                response=str(request_root / "response.json"),
            )
            choices = response.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise IncompleteCompletion("Expected one complete model choice")
            choice = choices[0]
            if not isinstance(choice, dict):
                raise IncompleteCompletion("Malformed model choice")
            if choice.get("finish_reason") == "length":
                if (
                    self.context_recovery_notice is not None
                    and self.output_format == "tools"
                    and names - {"submit_artifact", "revise_artifact"}
                    and (max_turns is None or turn < max_turns)
                ):
                    reduced = _restart_context(messages, self.context_recovery_notice)
                    if reduced is not None:
                        # The received response and its consumed request remain
                        # recorded. Never append or execute its partial action.
                        # Reuse the existing context recovery; completed tool
                        # effects and all original execution bounds stay put.
                        event(
                            "context_restarted",
                            reason="completion_length",
                            incomplete_call_id=call_id,
                            previous_messages=len(messages),
                            retained_messages=len(reduced),
                            actions_executed=0,
                            allowance_reset=False,
                        )
                        messages = reduced
                        continue
                raise OutputTokenLimit("Response reached its output-token limit; no tool executed")
            if choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise IncompleteCompletion("Incomplete model response; no tool executed")
            message = choice.get("message", {})
            if not isinstance(message, dict) or message.get("role") != "assistant":
                raise IncompleteCompletion("Expected an assistant message")
            content = message.get("content")
            empty = (
                (content is None or (isinstance(content, str) and not content.strip()))
                and message.get("tool_calls") in (None, [])
                and message.get("function_call") is None
                and not message.get("refusal")
            )
            if empty:
                if (
                    self.empty_response_retry_notice is not None
                    and self.empty_response_retries_used == 0
                    and (max_turns is None or turn < max_turns)
                ):
                    self.empty_response_retries_used += 1
                    # Keep the raw response, but never put an invalid assistant
                    # tool message into the next provider request. All completed
                    # actions and feedback remain in their original order.
                    messages.append({"role": "user", "content": self.empty_response_retry_notice})
                    event(
                        "empty_response_retry_requested",
                        empty_call_id=call_id,
                        response=str(request_root / "response.json"),
                        retry_number=self.empty_response_retries_used,
                        allowance_reset=False,
                        actions_executed=0,
                    )
                    continue
                raise IncompleteCompletion("Empty model response; no tool executed")
            if self.output_format in {"json_schema", "json_unconstrained"}:
                if (
                    message.get("refusal")
                    or message.get("tool_calls")
                    or choice["finish_reason"] != "stop"
                ):
                    raise IncompleteCompletion(
                        "Expected a complete JSON artifact, not a tool action"
                    )
                assistant = {"role": "assistant", "content": message.get("content")}
                for field in ("reasoning", "reasoning_content"):
                    if field in message:
                        assistant[field] = message[field]
                messages.append(assistant)
                try:
                    artifact = json.loads(message.get("content"))
                    if not isinstance(artifact, dict):
                        raise ValueError("Artifact must be an object")
                except (ValueError, TypeError):
                    result = "Artifact rejected: response must be one complete JSON object."
                else:
                    event("artifact_submission", artifact=artifact)
                    result = str(await handlers["submit_artifact"](**artifact))
                event("artifact_validation", output=result)
                if result.startswith("Artifact committed."):
                    return {"messages": messages, "turns": turn, "cost": 0.0}
                # The upstream validator still supplies its original feedback,
                # but merge-patch instructions do not apply to this interface.
                feedback = result.replace(
                    "call revise_artifact with only changed fields, or submit_artifact for a complete replacement: ",
                    "",
                )
                messages.append(
                    {
                        "role": "user",
                        "content": "Return a complete corrected artifact using the same JSON schema, including unchanged fields. Do not return a patch or tool call.\n"
                        + feedback,
                    }
                )
                continue
            calls = message.get("tool_calls")
            if (
                calls in (None, [])
                and message.get("function_call") is None
                and not message.get("refusal")
                and isinstance(content, str)
                and content.strip()
                and self.missing_tool_retry_notice is not None
                and self.missing_tool_retries_used == 0
                and (max_turns is None or turn < max_turns)
            ):
                # A received text-only reply dispatched no action. Preserve it
                # and request the proper artifact protocol, without replaying
                # completed work or resetting the caller's execution bounds.
                self.missing_tool_retries_used += 1
                assistant = {"role": "assistant", "content": content}
                for field in ("reasoning", "reasoning_content"):
                    if field in message:
                        assistant[field] = message[field]
                messages.append(assistant)
                messages.append({"role": "user", "content": self.missing_tool_retry_notice})
                self.save_record(
                    request_root / "failure.json",
                    {"failure_category": "missing_tool_action", "actions_executed": 0},
                )
                event(
                    "missing_tool_retry_requested",
                    call_id=call_id,
                    response=str(request_root / "response.json"),
                    retry_number=self.missing_tool_retries_used,
                    actions_executed=0,
                    allowance_reset=False,
                )
                continue
            if message.get("refusal") or not isinstance(calls, list) or len(calls) != 1:
                raise IncompleteCompletion("Expected one tool action; no tool executed")
            call = calls[0]
            if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                raise IncompleteCompletion("Malformed tool action; no tool executed")
            function = call.get("function", {})
            if (
                call.get("type") != "function"
                or not isinstance(call.get("id"), str)
                or not call["id"]
                or call["id"] in seen_call_ids
                or not isinstance(function.get("name"), str)
                or not isinstance(function.get("arguments"), str)
            ):
                raise IncompleteCompletion("Malformed tool action; no tool executed")
            seen_call_ids.add(call["id"])
            # GLM reasoning content must survive subsequent tool-result turns.
            assistant = {
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": calls,
            }
            # Current vLLM uses `reasoning`; retain the provider's field name,
            # while also supporting recorded responses from older endpoints.
            for field in ("reasoning", "reasoning_content"):
                if field in message:
                    assistant[field] = message[field]
            messages.append(assistant)
            name = function["name"]
            arguments: dict[str, Any] = {}
            try:
                parsed = json.loads(function["arguments"])
                if not isinstance(parsed, dict):
                    raise ValueError
                arguments = parsed
                if name not in permitted:
                    result = "Tool unavailable. Use one of the currently supplied tools."
                else:
                    inspect.signature(handlers[name]).bind(**arguments)
                    result = None
            except (ValueError, TypeError):
                result = "Invalid tool arguments. Follow the supplied JSON object schema."
            if result is None:
                event("tool_request", call_id=call["id"], name=name, arguments=arguments)
                result = await handlers[name](**arguments)
            result = str(result)
            committed = name in {"submit_artifact", "revise_artifact"} and result.startswith(
                "Artifact committed."
            )
            raw_result = request_root / "tool-result.json"
            self.save_record(raw_result, {"call_id": call["id"], "name": name, "output": result})
            truncated = (
                self.limits.tool_output_chars is not None
                and len(result) > self.limits.tool_output_chars
            )
            if truncated:
                assert self.limits.tool_output_chars is not None
                head = self.limits.tool_output_chars // 3
                tail = self.limits.tool_output_chars - head
                result = (
                    result[:head]
                    + "\n[tool output truncated; full output retained in execution artifacts]\n"
                    + result[-tail:]
                )
            event(
                "tool_result",
                call_id=call["id"],
                name=name,
                output=result,
                truncated=truncated,
                raw_result_record=str(raw_result.relative_to(trace.parent)),
            )
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
            if committed:
                return {"messages": messages, "turns": turn, "cost": 0.0}
        raise RuntimeError("Design worker exhausted its model-call allowance")
