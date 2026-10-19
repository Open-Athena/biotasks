"""One fresh tiny completion on the approved free endpoint; no repository work."""

import hashlib
import importlib.metadata
import json
import logging
import os
import time
import traceback
from pathlib import Path

import httpx
from iris.client.client import iris_ctx
from iris.cluster.types import JobName
from openai import OpenAI


def main():
    if os.environ.get("DAYTONA_API_KEY") or os.environ.get("REPO2RLENV_REMOTE_WORKER"):
        raise RuntimeError("Inference-only probe must not receive repository-worker credentials")
    for name in ("httpx", "httpcore", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    result = {"stage": "one_fresh_tiny_direct_completion_not_task_generation", "model": "glm-5.3",
              "max_tokens": 131072, "reasoning_effort": "medium", "request_timeout_sec": 1200,
              "maximum_model_calls": 1, "requests_dispatched": 0, "responses_received": 0,
              "repository_execution": False, "source_candidates_charged": 0,
              "task_outputs_edited": False, "shared_service_modified": False,
              "SDK": {name: importlib.metadata.version(name) for name in ("openai", "httpx")}}
    started = time.monotonic()

    def wire(request):
        body = request.read()
        payload = json.loads(body)
        assert request.method == "POST" and request.url.path.endswith("/chat/completions")
        assert result["requests_dispatched"] == 0
        assert payload["model"] == "glm-5.3" and payload["max_tokens"] == 131072
        assert payload["chat_template_kwargs"]["reasoning_effort"] == "medium"
        result.update(requests_dispatched=1, request_sha256=hashlib.sha256(body).hexdigest(), request_bytes=len(body))
        (output / "request-receipt.json").write_text(json.dumps(result, indent=2) + "\n")

    try:
        resolved = iris_ctx().client.resolver_for_job(JobName.from_string(os.environ["BIOTASKS21_GLM_RELAY_JOB"])).resolve("glm-5.3")
        assert resolved.endpoints
        upstream = resolved.endpoints[0].url.rstrip("/")
        if not upstream.endswith("/v1"):
            upstream += "/v1"
        result["resolved_free_service_endpoint_count"] = len(resolved.endpoints)
        timeout = httpx.Timeout(1200, connect=30)
        with httpx.Client(timeout=timeout, event_hooks={"request": [wire]}, follow_redirects=False) as transport:
            with OpenAI(base_url=upstream, api_key=os.environ["BIOTASKS21_GLM_KEY"],
                        timeout=timeout, max_retries=0, http_client=transport) as client:
                response = client.chat.completions.create(
                    model="glm-5.3", max_tokens=131072, stream=False,
                    messages=[{"role": "system", "content": "Return the requested JSON object without commentary."},
                              {"role": "user", "content": "Return exactly {\"ok\":true}."}],
                    response_format={"type": "json_schema", "json_schema": {"name": "completion_health", "strict": True,
                        "schema": {"type": "object", "properties": {"ok": {"type": "boolean"}},
                                   "required": ["ok"], "additionalProperties": False}}},
                    extra_body={"chat_template_kwargs": {"reasoning_effort": "medium"}},
                )
        result.update(status="response_received_before_processing", responses_received=1)
        raw = json.dumps(response.model_dump(mode="json"), indent=2) + "\n"
        (output / "response.json").write_text(raw)
        content = response.choices[0].message.content if response.choices else None
        parsed = None
        if content:
            try:
                parsed = json.loads(content)
            except ValueError:
                pass
        result.update(status="response_received", responses_received=1,
                      exact_expected_json=parsed == {"ok": True}, answer_characters=len(content or ""),
                      finish_reasons=[choice.finish_reason for choice in response.choices],
                      usage=response.usage.model_dump(mode="json") if response.usage else None,
                      response_sha256=hashlib.sha256(raw.encode()).hexdigest())
    except Exception as exc:
        (output / "private-error.txt").write_text(traceback.format_exc())
        result.update(status="processing_failed_after_response" if result["responses_received"] else "completion_not_received", error_type=type(exc).__name__,
                      cause_type=type(exc.__cause__).__name__ if exc.__cause__ else None,
                      HTTP_status=getattr(exc, "status_code", None), upstream_usage="unobserved_not_zero")
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "completion-probe.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result.get("exact_expected_json") else 1


if __name__ == "__main__":
    raise SystemExit(main())
