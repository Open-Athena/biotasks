"""Matched synthetic tool turns diagnose reasoning transport, with no sandbox."""

import asyncio
import json
import os
import time

import httpx
from openai import AsyncOpenAI
from repo2rlenv.execution.lifecycle import save_record

from biotasks.inference_gate import Allowance, RequestLedger


async def run(root, config):
    root.mkdir(parents=True, exist_ok=False)
    save_record(root / "configuration.json", config)
    ledger = RequestLedger(root / "requests.sqlite", {"probe": Allowance(4, None)})
    summaries = []
    async with AsyncOpenAI(
        base_url=os.environ["BIOTASKS_MODEL_ENDPOINT"],
        api_key=os.environ["GLM_BULK_TOKEN"],
        max_retries=0,
        timeout=600,
        http_client=httpx.AsyncClient(follow_redirects=False),
    ) as client:
        for mode in ("required", "auto"):
            messages = [
                {
                    "role": "system",
                    "content": "Use read_problem to obtain the problem, then solve it carefully and call submit_answer. Do not run code. This is a synthetic tool-transport test.",
                },
                {"role": "user", "content": "Please obtain the problem and solve it."},
            ]
            for turn in (1, 2):
                name = "read_problem" if turn == 1 else "submit_answer"
                schema = {"type": "object", "properties": {}, "additionalProperties": False}
                if turn == 2:
                    schema.update(properties={"answer": {"type": "integer"}}, required=["answer"])
                payload = dict(
                    model="glm-5.3",
                    messages=messages,
                    tool_choice=mode,
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": "Obtain the problem."
                                if turn == 1
                                else "Submit the integer solution.",
                                "parameters": schema,
                            },
                        }
                    ],
                    parallel_tool_calls=False,
                    stream=False,
                    temperature=1.0,
                    top_p=1.0,
                    chat_template_kwargs={"reasoning_effort": "medium"},
                )
                folder = root / mode / str(turn)
                save_record(folder / "request.json", payload)
                claim = ledger.claim("probe", json.dumps(payload).encode())
                started = time.time()
                options = dict(payload)
                extra = options.pop("chat_template_kwargs")
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        **options, extra_body={"chat_template_kwargs": extra}
                    ),
                    timeout=600,
                )
                value = response.model_dump(mode="json")
                save_record(folder / "response.json", value)
                ledger.finish(claim, "response_received")
                message = value["choices"][0]["message"]
                calls = message.get("tool_calls") or []
                summaries.append(
                    dict(
                        mode=mode,
                        turn=turn,
                        elapsed_seconds=time.time() - started,
                        reasoning_characters=sum(
                            len(message.get(k) or "") for k in ("reasoning", "reasoning_content")
                        ),
                        reasoning_tokens=(
                            value.get("usage", {}).get("completion_tokens_details") or {}
                        ).get("reasoning_tokens"),
                        finish_reason=value["choices"][0]["finish_reason"],
                        tool_names=[c["function"]["name"] for c in calls],
                    )
                )
                save_record(root / "result.json", {"cases": summaries, "sandbox_created": False})
                if len(calls) != 1 or calls[0]["function"]["name"] != name:
                    break
                assistant = {
                    k: message[k]
                    for k in ("role", "content", "tool_calls", "reasoning", "reasoning_content")
                    if k in message
                }
                messages.append(assistant)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": calls[0]["id"],
                        "content": "Find the smallest nonnegative integer n such that n mod 17 = 5, n mod 23 = 7, and n mod 31 = 11.",
                    }
                )
