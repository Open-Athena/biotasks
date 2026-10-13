"""Bounded GLM Chat Completions transport for an upstream artifact controller.

The caller supplies an async, no-retry transport and controller tool handlers.
This module does not choose a task, validate its science, or launch a sandbox.
Only the approved free GLM model is supported; monetary receipts are zero while
every attempted HTTP request consumes a durable RequestLedger slot.
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
    """A preserved response must not execute tools or be silently regenerated."""


@dataclass(frozen=True)
class ChatLimits:
    max_output_tokens: int = 16000
    request_timeout_sec: int = 600
    max_input_bytes: int = 256000
    max_response_bytes: int = 2000000
    tool_output_chars: int = 24000
    reasoning_effort: str = "high"

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key != "reasoning_effort" and (type(value) is not int or value < 1):
                raise ValueError(f"{key} must be a positive integer")
        if self.reasoning_effort not in {"low", "medium", "high"}:
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
    ):
        if not math.isfinite(deadline) or deadline <= time.time():
            raise ValueError("A finite future deadline is required")
        if limits.max_output_tokens > ledger.allowances[scope].output_tokens:
            raise ValueError("Output tokens exceed the request ledger allowance")
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
        max_turns: int,
        max_cost: float,
        runtime: str,
    ) -> dict[str, Any]:
        if model != "glm-5.3" or runtime != "biotasks-glm-chat-v1":
            raise ValueError("This adapter supports only the approved GLM runtime")
        if (
            type(max_turns) is not int
            or max_turns < 1
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

        def event(kind, **data):
            with trace.open("a") as stream:
                stream.write(json.dumps({"kind": kind, **data}, allow_nan=False) + "\n")

        event("input", model=model, runtime=runtime, settings=asdict(self.limits))
        seen_call_ids = set()
        for turn in range(1, max_turns + 1):
            remaining = self.deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("Design deadline exhausted")
            available_tools = [
                tool
                for tool in tools
                if max_turns - turn >= 2
                or tool["function"]["name"] in {"submit_artifact", "revise_artifact"}
            ]
            permitted = {tool["function"]["name"] for tool in available_tools}
            payload = {
                "model": model,
                "messages": messages,
                "tools": available_tools,
                "tool_choice": "required",
                "parallel_tool_calls": False,
                "stream": False,
                "max_tokens": self.limits.max_output_tokens,
                "temperature": 1.0,
                "top_p": 1.0,
                "chat_template_kwargs": {"reasoning_effort": self.limits.reasoning_effort},
            }
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
            if len(body) > self.limits.max_input_bytes:
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
            try:
                response = await asyncio.wait_for(
                    self.complete(payload),
                    timeout=min(remaining, self.limits.request_timeout_sec),
                )
            except (Exception, asyncio.CancelledError) as exc:
                self.save_record(
                    request_root / "failure.json",
                    {"error_type": type(exc).__name__, "request_slot_retained": True},
                )
                # Exception text can contain the private endpoint or response body.
                if isinstance(exc, asyncio.CancelledError):
                    raise
                raise RuntimeError("Model transport failed; inspect the retained receipt") from None
            if (
                len(json.dumps(response, ensure_ascii=False).encode())
                > self.limits.max_response_bytes
            ):
                self.save_record(request_root / "failure.json", {"error_type": "oversize_response"})
                raise IncompleteCompletion("Response exceeds the evidence bound")
            self.save_record(request_root / "response.json", response)
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
            if choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise IncompleteCompletion("Incomplete model response; no tool executed")
            message = choice.get("message", {})
            if not isinstance(message, dict) or message.get("role") != "assistant":
                raise IncompleteCompletion("Expected an assistant message")
            calls = message.get("tool_calls")
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
            if "reasoning_content" in message:
                assistant["reasoning_content"] = message["reasoning_content"]
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
            if len(result) > self.limits.tool_output_chars:
                result = result[: self.limits.tool_output_chars] + "\n[tool output truncated]"
            event("tool_result", call_id=call["id"], name=name, output=result)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
            if name in {"submit_artifact", "revise_artifact"} and result.startswith(
                "Artifact committed."
            ):
                return {"messages": messages, "turns": turn, "cost": 0.0}
        raise RuntimeError("Design worker exhausted its model-call allowance")
