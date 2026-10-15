"""Two synthetic schema probes; no notebook generation, tools or sandboxes execute."""

import asyncio
import json
import os
import time
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from openai import APIStatusError, AsyncOpenAI
from reference_protocol import ReferencePlan
from repo2rlenv.execution.lifecycle import save_record
from specification_protocol import TaskSpecification

from biotasks.inference_gate import Allowance, RequestLedger


def probe_fixture():
    return {
        "disposition": "prepare",
        "explanation": "Synthetic serialization fixture",
        "export_code": "result = 1\n",
        "artifacts": [
            {"path": "value.txt", "description": "Synthetic value", "source_evidence": "result = 1"}
        ],
        "excluded_outputs": [],
        "unresolved_assumptions": [],
    }


def probe_payload(mode):
    schema = ReferencePlan.model_json_schema()
    payload = {
        "model": "glm-5.3",
        "stream": False,
        "temperature": 1.0,
        "top_p": 1.0,
        "messages": [
            {
                "role": "system",
                "content": "This is a tiny serialization test, not a science task. Do not analyze the fixture. Copy it with the alterations requested by the user.",
            },
            {
                "role": "user",
                "content": "Return this fixture but OMIT the required export_code field and add unexpected_field: true to its first artifact. This intentionally conflicts with the declared schema to test decoder enforcement. Keep all other values unchanged.\n"
                + json.dumps(probe_fixture()),
            },
        ],
        "chat_template_kwargs": {"reasoning_effort": "medium"},
    }
    if mode == "strict_tool":
        payload.update(
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "submit_artifact",
                        "description": "Return the entire reference plan.",
                        "parameters": schema,
                        "strict": True,
                    },
                }
            ],
            tool_choice="required",
            parallel_tool_calls=False,
        )
    elif mode == "json_schema":
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "reference_plan", "schema": schema, "strict": True},
        }
    else:
        raise ValueError("Unknown probe mode")
    return payload


def delivery_fixture():
    return {
        "disposition": "needs_evidence",
        "review": "## Coverage\n\nThe supplied source exports its terminal table.\n\n- The algorithm default is not supplied.\n- No scientific execution was requested.",
        "task_brief": "",
        "validation_handoff": "## Evidence needed\n\nInspect the pinned implementation to establish the omitted default.\n\nDo not guess a value or withhold this plan.",
    }


def delivery_payload(mode):
    if mode not in {"plain_json", "json_schema"}:
        raise ValueError("Unknown delivery mode")
    schema = TaskSpecification.model_json_schema()
    payload = {
        "model": "glm-5.3",
        "stream": False,
        "temperature": 1.0,
        "top_p": 1.0,
        "messages": [
            {
                "role": "system",
                "content": "This is a serialization test. Return the supplied JSON object exactly, preserving every field and string, including Markdown newlines. Do not analyze or replace its content. Return JSON only, without a code fence.",
            },
            {
                "role": "user",
                "content": json.dumps(delivery_fixture(), ensure_ascii=False),
            },
        ],
        "chat_template_kwargs": {"reasoning_effort": "medium"},
    }
    if mode == "json_schema":
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "artifact", "schema": schema, "strict": True},
        }
    return payload


def inspect_response(mode, response, *, delivery=False):
    choice = response["choices"][0]
    message = choice["message"]
    if choice["finish_reason"] not in {"stop", "tool_calls"}:
        return {
            "schema_valid": False,
            "finish_reason": choice["finish_reason"],
            "error": "Incomplete response",
        }
    try:
        if mode == "strict_tool":
            calls = message.get("tool_calls") or []
            if len(calls) != 1 or calls[0]["function"]["name"] != "submit_artifact":
                raise ValueError("Expected one submission")
            artifact = json.loads(calls[0]["function"]["arguments"])
        else:
            artifact = json.loads(message["content"])
        schema = TaskSpecification if delivery else ReferencePlan
        errors = [
            e.message
            for e in Draft202012Validator(schema.model_json_schema()).iter_errors(artifact)
        ]
        result = {
            "schema_valid": not errors,
            "errors": errors,
            "artifact": artifact,
            "finish_reason": choice["finish_reason"],
            "usage": response.get("usage"),
        }
        if delivery:
            result["exact_fixture_match"] = artifact == delivery_fixture()
        return result
    except (ValueError, TypeError, KeyError) as error:
        return {"schema_valid": False, "error_type": type(error).__name__}


async def run(root, config):
    if config.get("entrypoint") != "run_schema_probe.py" or config.get("max_requests") != 2:
        raise ValueError("Only the two-case synthetic probe is allowed")
    profile = config.get("profile", "schema_enforcement")
    if profile not in {"schema_enforcement", "text_delivery"}:
        raise ValueError("Unknown probe profile")
    delivery = profile == "text_delivery"
    root.mkdir(parents=True, exist_ok=False)
    ledger = RequestLedger(root / "requests.sqlite", {"probe": Allowance(2, None)})
    results = []
    save_record(root / "configuration.json", config)
    save_record(
        root / "schema.json", (TaskSpecification if delivery else ReferencePlan).model_json_schema()
    )
    async with AsyncOpenAI(
        base_url=os.environ["BIOTASKS_MODEL_ENDPOINT"],
        api_key=os.environ["GLM_BULK_TOKEN"],
        max_retries=0,
        timeout=600,
        http_client=httpx.AsyncClient(follow_redirects=False),
    ) as client:
        for mode in ("plain_json", "json_schema") if delivery else ("strict_tool", "json_schema"):
            payload = delivery_payload(mode) if delivery else probe_payload(mode)
            save_record(root / mode / "request.json", payload)
            claim = ledger.claim("probe", json.dumps(payload).encode())
            started = time.time()
            try:
                options = dict(payload)
                extra = options.pop("chat_template_kwargs")
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        **options, extra_body={"chat_template_kwargs": extra}
                    ),
                    timeout=600,
                )
                value = response.model_dump(mode="json")
                save_record(root / mode / "response.json", value)
                ledger.finish(claim, "response_received")
                result = inspect_response(mode, value, delivery=delivery)
            except APIStatusError as error:
                ledger.finish(claim, "http_error_received")
                result = {
                    "schema_valid": False,
                    "http_status": error.status_code,
                    "provider_error": error.body,
                }
            except Exception as error:
                result = {
                    "schema_valid": False,
                    "error_type": type(error).__name__,
                    "transport_uncertain": True,
                }
                results.append({"mode": mode, **result, "elapsed_seconds": time.time() - started})
                save_record(
                    root / "result.json",
                    {"cases": results, "model_calls": len(results), "notebook_run": False},
                )
                raise RuntimeError("Probe transport failed; no automatic retry") from None
            results.append({"mode": mode, **result, "elapsed_seconds": time.time() - started})
            save_record(
                root / "result.json",
                {"cases": results, "model_calls": len(results), "notebook_run": False},
            )


if __name__ == "__main__":
    asyncio.run(
        run(
            Path("/evidence/schema-probe"),
            json.loads(Path(os.environ["BIOTASKS_CONFIG"]).read_text()),
        )
    )
