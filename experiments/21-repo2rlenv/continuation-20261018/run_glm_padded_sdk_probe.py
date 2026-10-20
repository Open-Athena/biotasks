"""Zero-model long-response check through the pinned native authoring SDK.

Diagnostic routes return synthetic fixtures only. No candidate prompt, saved
model request, task source, grader or author response is replayed or executed.
"""
import hashlib
import json
import logging
import os
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path
from unittest.mock import patch


def check_native(output):
    import httpx
    import litellm
    import openai
    from repo2rlenv.llm import complete
    from repo2rlenv.pipelines.recipes.terminal.draft import TerminalDraft
    from repo2rlenv.spec.input import LLMSpec

    for name in ("httpx", "httpcore", "openai", "LiteLLM"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    base = os.environ["BIOTASKS21_INFERENCE_CLIENT_URL"].rstrip("/")
    token = os.environ["BIOTASKS21_GENERATION_CLIENT_TOKEN"]
    original = litellm.completion
    params = {"system": "Synthetic SDK transport check only. No model is called.",
              "user": "Return the diagnostic receipt, without executing a task.",
              "max_tokens": 131072, "response_schema": TerminalDraft.model_json_schema()}
    synthetic = {"id":"synthetic-only", "object":"chat.completion", "created":0,
        "model":"glm-5.3", "choices":[{"index":0, "finish_reason":"stop",
        "message":{"role":"assistant", "content":"synthetic"}}],
        "usage":{"prompt_tokens":0, "completion_tokens":0, "total_tokens":0}}
    wires = []

    def mock(request):
        assert request.url.host == "synthetic.invalid"
        wires.append(request.content)
        return httpx.Response(200, json=synthetic)

    def invoke(endpoint, client):
        def adapted(*args, **kwargs):
            kwargs["client"] = client
            kwargs["extra_headers"] = {"X-Biotasks21-Inference-Token":token}
            kwargs["extra_body"] = {"chat_template_kwargs":{"reasoning_effort":"medium"}}
            return original(*args, **kwargs)
        with patch.object(litellm, "completion", adapted):
            spec = LLMSpec.model_validate({"provider":"openai", "model":"glm-5.3",
                "endpoint":endpoint, "timeout_sec":1200, "fallback":None})
            return complete(spec, **params)

    with httpx.Client(transport=httpx.MockTransport(mock)) as http:
        client = openai.OpenAI(api_key="synthetic", base_url="https://synthetic.invalid/v1",
                               http_client=http, max_retries=0)
        invoke("https://synthetic.invalid/v1", client)
    assert len(wires) == 1
    wire_hash = hashlib.sha256(wires[0]).hexdigest()
    result = {"stage":"zero_model_native_authoring_SDK_padded_response_check",
              "model_calls":0, "candidate_attempts":0, "task_fixes":0,
              "expected_native_wire_sha256":wire_hash,
              "generation_max_output_tokens":131072, "generation_effort":"medium",
              "maximum_request_seconds":1200, "passed":False}
    try:
        error_base = base + "/v1/diagnostic-error"
        with httpx.Client(timeout=httpx.Timeout(60, connect=30)) as http:
            client = openai.OpenAI(api_key="synthetic", base_url=error_base,
                                   http_client=http, max_retries=0)
            try:
                invoke(error_base, client)
            except Exception as exc:
                result.update(synthetic_error_rejected=True, synthetic_error_type=type(exc).__name__)
            else:
                result["synthetic_error_rejected"] = False
        assert result["synthetic_error_rejected"], "Error fixture returned a completion"
        endpoint = base + "/v1/diagnostic"
        started = time.monotonic()
        with httpx.Client(timeout=httpx.Timeout(1200, connect=30)) as http:
            client = openai.OpenAI(api_key="synthetic", base_url=endpoint,
                                   http_client=http, max_retries=0)
            response = invoke(endpoint, client)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        receipt = json.loads(response.content)
        assert receipt["model_calls"] == 0 and receipt["request_sha256"] == wire_hash
        assert receipt["diagnostic_delay_seconds"] == 650 and result["elapsed_seconds"] >= 645
        assert response.prompt_tokens == response.completion_tokens == 0
        result.update(passed=True, receipt=receipt,
                      original_response_fields_preserved=True, upstream_model_service_contacted=False)
    finally:
        request = urllib.request.Request(base + "/v1/finish", data=wires[0],
            headers={"Content-Type":"application/json", "X-Biotasks21-Inference-Token":token})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result["authenticated_finish_requested"] = json.load(response).get("stage") == "finishing"
        except Exception as exc:
            result["finish_error_type"] = type(exc).__name__
        (output / "native-sdk-probe.json").write_text(json.dumps(result, indent=2) + "\n")


def main():
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    if os.environ.get("BIOTASKS21_NATIVE_PROBE_CHILD") == "1":
        check_native(output)
        return 0
    assert not os.environ.get("DAYTONA_API_KEY") and not os.environ.get("BIOTASKS21_GLM_KEY")
    started = time.monotonic()
    status = {"stage":"TRC_zero_model_native_SDK_transport_probe", "model_calls":0,
              "task_attempts":0, "repository_execution":False}
    try:
        source = Path("repo2rlenv-source.tar.gz")
        with source.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755"
        with tarfile.open(source) as archive:
            archive.extractall("native-runtime", filter="data")
        roots = list(Path("native-runtime").iterdir())
        assert len(roots) == 1
        root = roots[0]
        env = dict(os.environ, LITELLM_LOCAL_MODEL_COST_MAP="True", DO_NOT_TRACK="1")
        env.pop("VIRTUAL_ENV", None)
        env["UV_PROJECT_ENVIRONMENT"] = str(root.resolve() / ".venv")
        with (output / "private-setup.log").open("w") as log:
            subprocess.run(["uv", "sync", "--frozen", "--no-dev", "--python", "3.12.3",
                            "--project", str(root)], env=env, stdout=log, stderr=log, timeout=600, check=True)
        env["BIOTASKS21_NATIVE_PROBE_CHILD"] = "1"
        with (output / "private-native-sdk.log").open("w") as log:
            child = subprocess.run([str(root / ".venv/bin/python"), __file__], env=env,
                                   stdout=log, stderr=log, timeout=1300)
        status.update(status="completed" if child.returncode == 0 else "failed", child_exit_code=child.returncode)
        return child.returncode
    except Exception as exc:
        status.update(status="failed", error_type=type(exc).__name__)
        return 1
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "wrapper-status.json").write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
