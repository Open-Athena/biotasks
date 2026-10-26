"""Generation transport adapter; reuse fixed-handle SDK logic with named secrets."""

import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from biotasks.generation import model_budget
from biotasks.validation import iris_client as base
from biotasks.validation.files import require


class GenerationClient:
    def __init__(self, client, secrets):
        self.client, self.secrets = client, secrets

    def __getattr__(self, name):
        return getattr(self.client, name)

    def submit(self, **kwargs):
        entrypoint, environment = kwargs["entrypoint"], kwargs["environment"]
        require(
            entrypoint.command
            == [
                "bash",
                "-c",
                'PYTHONPATH="$IRIS_WORKDIR" exec "$IRIS_PYTHON" -u -m biotasks.validation.worker.job',
            ],
            "Unexpected inherited worker command",
        )
        require(
            not environment.secrets and str(environment.secret_behavior) == "isolate",
            "Unisolated inherited environment",
        )
        require(
            set(self.secrets) == {"GH_TOKEN", "OPENROUTER_API_KEY"}, "Unexpected generation secrets"
        )
        require(
            not any(k in environment.env_vars for k in self.secrets),
            "Secrets entered ordinary environment metadata",
        )
        kwargs["environment"] = dataclasses.replace(environment, secrets=self.secrets)
        kwargs["entrypoint"] = type(entrypoint)(
            command=[
                "bash",
                "-c",
                'PYTHONPATH="$IRIS_WORKDIR" exec "$IRIS_PYTHON" -u "$IRIS_WORKDIR/generation_worker.py"',
            ],
            workdir_files=entrypoint.workdir_files,
            workdir_file_refs=entrypoint.workdir_file_refs,
        )
        return self.client.submit(**kwargs)


def generation_preflight(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    result = ORIGINAL_PREFLIGHT(client, request)
    result.pop("model_calls", None)
    result.update(operation="generate", model_usage_measured=False, upstream_only_model_calls=True)
    return result


ORIGINAL_PREFLIGHT = base.preflight


def main():
    request = json.load(sys.stdin)
    action = request["action"]
    if action == "fingerprint":
        result = base.fingerprint()
    else:
        require(
            action in {"preflight", "submit", "observe", "logs"}, "Unexpected generation action"
        )
        with base.connect(request["backend"]["config"]) as client:
            if action == "submit":
                model_budget.verify_reserved(
                    Path(request["model_ledger"]),
                    request["group"]["run_id"],
                    request["plan_identity"],
                )
                secrets = {name: os.environ[name] for name in ("GH_TOKEN", "OPENROUTER_API_KEY")}
                require(all(secrets.values()), "Approved generation credentials are missing")
                # One transport process, one operation. Only preflight metadata
                # and the trusted operation's entrypoint/secret delivery differ.
                cast(Any, base).preflight = generation_preflight
                result = base.submit(GenerationClient(client, secrets), request)
            elif action == "preflight":
                result = generation_preflight(client, request)
            else:
                result = {"observe": base.observe, "logs": base.logs}[action](client, request)
            result.pop("model_calls", None)
            result["model_usage_measured"] = False
    print("BIOTASKS_VALIDATION_RESULT=" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
