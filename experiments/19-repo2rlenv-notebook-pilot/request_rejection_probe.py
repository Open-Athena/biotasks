"""Replay one hash-verified rejected request for diagnosis; never execute tools."""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def redact_error(body, secrets):
    """Keep provider diagnostics without recording credentials or private URLs."""
    secrets = [value for value in secrets if value]

    def clean(value):
        if isinstance(value, dict):
            return {clean(str(key)): clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if not isinstance(value, (str, int, float, bool, type(None))):
            value = str(value)
        if not isinstance(value, str):
            return "<redacted>" if str(value) in secrets else value
        for secret in secrets:
            value = value.replace(secret, "<redacted>")
        value = re.sub(r"https?://[^\s\"<>]+", "<redacted-url>", value)
        return re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<redacted-address>", value)

    return json.dumps(clean(body), ensure_ascii=False)


def fetch(config, destination):
    import fsspec
    from coverage_inputs import restore

    item = config["recorded_request"]
    receipts = restore(
        [item],
        prefix=os.environ["BIOTASKS_REFERENCE_ARCHIVE"].rstrip("/"),
        root=destination,
        open_source=lambda uri: fsspec.open(uri, "rb").open(),
        byte_limit=item["bytes"],
    )
    (destination.parent / "retrieval.json").write_text(
        json.dumps({"files": receipts, "hash_verified": True}, indent=2, sort_keys=True) + "\n"
    )


async def run(root, config):
    import httpx
    from openai import APIStatusError, AsyncOpenAI
    from repo2rlenv.execution.lifecycle import save_record

    from biotasks.chat_author import provider_failure
    from biotasks.inference_gate import Allowance, RequestLedger

    if config.get("entrypoint") != "run_schema_probe.py" or config.get("max_requests") != 1:
        raise ValueError("Only one recorded-request diagnostic is allowed")
    root.mkdir(parents=True, exist_ok=False)
    save_record(root / "configuration.json", config)
    recorded = root / "recorded"
    subprocess.run(
        [
            os.environ["BIOTASKS_EXPORT_PYTHON"],
            str(Path(__file__)),
            "--fetch",
            os.environ["BIOTASKS_CONFIG"],
            str(recorded),
        ],
        check=True,
        timeout=120,
    )
    payload = json.loads((recorded / config["recorded_request"]["path"]).read_text())
    if payload.get("model") != "glm-5.3" or payload.get("stream") is not False:
        raise ValueError("Recorded approved nonstreaming GLM request required")
    ledger = RequestLedger(root / "requests.sqlite", {"probe": Allowance(1, None)})
    started = time.time()
    endpoint, token = os.environ["BIOTASKS_MODEL_ENDPOINT"], os.environ["GLM_BULK_TOKEN"]
    result = {"notebook_run": False, "task_tools_executed": False, "daytona_sandboxes_created": 0}
    async with AsyncOpenAI(
        base_url=endpoint,
        api_key=token,
        max_retries=0,
        timeout=120,
        http_client=httpx.AsyncClient(follow_redirects=False),
    ) as client:
        try:
            models = await client.models.list()
            rows = [m.model_dump(mode="json") for m in models.data if m.id == "glm-5.3"]
            save_record(
                root / "model-metadata.json",
                {"models": [{k: r[k] for k in ("id", "max_model_len") if k in r} for r in rows]},
            )
        except Exception as error:
            save_record(root / "model-metadata.json", {"error_type": type(error).__name__})
        claim = ledger.claim("probe", json.dumps(payload).encode())
        result["model_requests"] = 1
        options = dict(payload)
        extension = options.pop("chat_template_kwargs")
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    **options, extra_body={"chat_template_kwargs": extension}
                ),
                timeout=120,
            )
            ledger.finish(claim, "response_received")
            result.update(status="accepted_without_tool_execution", http_status=200)
            save_record(
                root / "response-summary.json",
                {
                    "usage": response.usage.model_dump(mode="json") if response.usage else None,
                    "finish_reasons": [c.finish_reason for c in response.choices],
                },
            )
        except APIStatusError as error:
            ledger.finish(claim, "http_error_received")
            result.update(status="provider_rejection_received", **provider_failure(error))
            save_record(
                root / "provider-error.json",
                {
                    "http_status": error.status_code,
                    "redacted_provider_error": redact_error(error.body, [token, endpoint]),
                },
            )
        except Exception as error:
            result.update(status="transport_uncertain", error_type=type(error).__name__)
        result["elapsed_seconds"] = time.time() - started
        save_record(root / "result.json", result)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--fetch":
        fetch(json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3]))
    else:
        raise ValueError("Use the checkpointed schema-probe entrypoint")
