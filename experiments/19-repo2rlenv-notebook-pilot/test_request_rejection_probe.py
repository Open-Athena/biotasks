"""Recorded-request diagnostics must not execute tools or expose credentials."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError
from request_rejection_probe import redact_error


def test_provider_error_redaction_preserves_reason_without_private_values():
    value = redact_error(
        {
            "error": {
                "message": "maximum context length 202752; token=fixture-secret https://private.invalid/v1 10.0.0.1"
            }
        },
        ["fixture-secret"],
    )
    assert "fixture-secret" not in value
    assert "private.invalid" not in value and "10.0.0.1" not in value
    assert "maximum context length 202752" in value


@pytest.mark.parametrize("rejected", [True, False])
def test_diagnostic_replays_one_request_without_sandbox_or_tools(tmp_path, monkeypatch, rejected):
    import openai
    import request_rejection_probe as module

    payload = {
        "model": "glm-5.3",
        "stream": False,
        "messages": [{"role": "user", "content": "fixture"}],
        "chat_template_kwargs": {"reasoning_effort": "medium"},
        "tools": [],
    }
    config = {
        "entrypoint": "run_schema_probe.py",
        "profile": "recorded_request_rejection",
        "max_requests": 1,
        "recorded_request": {"path": "request.json"},
    }
    monkeypatch.setenv("BIOTASKS_EXPORT_PYTHON", "host-python")
    monkeypatch.setenv("BIOTASKS_CONFIG", "fixture-config.json")
    monkeypatch.setenv("BIOTASKS_MODEL_ENDPOINT", "https://private.invalid/v1")
    monkeypatch.setenv("GLM_BULK_TOKEN", "fixture-secret")

    def fetch(argv, **kwargs):
        assert argv[0] == "host-python" and "--fetch" in argv and kwargs["check"]
        recorded = tmp_path / "probe/recorded"
        recorded.mkdir()
        (recorded / "request.json").write_text(json.dumps(payload))

    monkeypatch.setattr(module.subprocess, "run", fetch)
    calls = []

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            self.http_client = kwargs["http_client"]
            self.models = SimpleNamespace(list=self.list_models)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.complete))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.http_client.aclose()

        async def list_models(self):
            return SimpleNamespace(data=[])

        async def complete(self, **kwargs):
            calls.append(kwargs)
            assert kwargs == {k: v for k, v in payload.items() if k != "chat_template_kwargs"} | {
                "extra_body": {"chat_template_kwargs": payload["chat_template_kwargs"]}
            }
            if rejected:
                raise BadRequestError(
                    "private exception",
                    response=httpx.Response(
                        400, request=httpx.Request("POST", "https://private.invalid/v1")
                    ),
                    body={"error": {"message": "maximum context length exceeded fixture-secret"}},
                )
            return SimpleNamespace(
                usage=None, choices=[SimpleNamespace(finish_reason="tool_calls")]
            )

    monkeypatch.setattr(openai, "AsyncOpenAI", Client)
    asyncio.run(module.run(tmp_path / "probe", config))
    assert len(calls) == 1
    result = json.loads((tmp_path / "probe/result.json").read_text())
    assert result["model_requests"] == 1 and not result["task_tools_executed"]
    assert result["daytona_sandboxes_created"] == 0
    assert result["http_status"] == (400 if rejected else 200)
    if rejected:
        error = (tmp_path / "probe/provider-error.json").read_text()
        assert "fixture-secret" not in error and "private.invalid" not in error
        assert result["failure_category"] == "provider_context_length"


def test_error_redaction_happens_before_json_escaping():
    secret = 'fixture-backslash\\and-quote"'
    original = {secret: {"message": "token=" + secret}}
    decoded = json.loads(redact_error(original, [secret]))
    assert secret not in decoded
    assert secret not in decoded["<redacted>"]["message"]
