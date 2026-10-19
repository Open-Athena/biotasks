"""Exercise actual SDK wire/capture on synthetic HTTP responses, with no network."""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("direct_probe", BASE / "run_glm_direct_completion_probe.py")
module = importlib.util.module_from_spec(spec)
# Discovery is mocked; exercise the pinned OpenAI/httpx stack without installing
# a second runtime into the shared environment or contacting the Iris controller.
stubs = {name: ModuleType(name) for name in ("iris", "iris.client", "iris.client.client", "iris.cluster", "iris.cluster.types")}
stubs["iris.client.client"].iris_ctx = lambda: None
stubs["iris.cluster.types"].JobName = SimpleNamespace(from_string=lambda value: value)
previous_modules = {name: sys.modules.get(name) for name in stubs}
sys.modules.update(stubs)
spec.loader.exec_module(module)
original_init = httpx.Client.__init__
checks = []
for kind in ("complete", "timeout"):
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        assert payload["max_tokens"] == 131072
        assert payload["chat_template_kwargs"] == {"reasoning_effort": "medium"}
        assert payload["response_format"]["json_schema"]["strict"]
        if kind == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        return httpx.Response(200, json={"id": "synthetic", "object": "chat.completion", "created": 0,
            "model": "glm-5.3", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": '{"ok":true}', "reasoning_content": "synthetic reasoning"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}})

    def init(client, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original_init(client, *args, **kwargs)

    resolver = SimpleNamespace(resolve=lambda _: SimpleNamespace(endpoints=[SimpleNamespace(url="https://fixture.invalid/v1")]))
    context = SimpleNamespace(client=SimpleNamespace(resolver_for_job=lambda _: resolver))
    with tempfile.TemporaryDirectory(prefix="biotasks21-direct-probe-") as name:
        env = {"IRIS_OUTPUT_DIR": name, "BIOTASKS21_GLM_RELAY_JOB": "/fixture/free-glm",
               "BIOTASKS21_GLM_KEY": "synthetic-key", "DAYTONA_API_KEY": "", "REPO2RLENV_REMOTE_WORKER": ""}
        with patch.dict(os.environ, env), patch.object(module, "iris_ctx", lambda: context), patch.object(httpx.Client, "__init__", init):
            code = module.main()
        result = json.loads((Path(name) / "completion-probe.json").read_text())
        assert len(sent) == result["requests_dispatched"] == 1
        assert result["source_candidates_charged"] == 0
        if kind == "complete":
            assert code == 0 and result["responses_received"] == 1 and result.get("exact_expected_json"), (result, (Path(name) / "private-error.txt").read_text() if (Path(name) / "private-error.txt").exists() else "")
            raw = json.loads((Path(name) / "response.json").read_text())
            assert raw["choices"][0]["message"]["reasoning_content"] == "synthetic reasoning"
            assert result["usage"]["total_tokens"] == 5
        else:
            assert code == 1 and result["responses_received"] == 0
            assert result["error_type"] == "APITimeoutError" and not (Path(name) / "response.json").exists()
            assert result["upstream_usage"] == "unobserved_not_zero"
        checks.append(kind + ":single_wire_request_limits_and_durable_receipt")
(BASE / "glm-direct-completion-probe-offline-checks.json").write_text(json.dumps({
    "stage": "synthetic_actual_SDK_checks_no_live_model_or_network", "checks_passed": checks,
    "live_model_calls": 0, "target_code_execution": False,
}, indent=2) + "\n")
print(json.dumps({"offline_checks": len(checks), "live_model_calls": 0, "network": False}))
for name, previous in previous_modules.items():
    if previous is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = previous
