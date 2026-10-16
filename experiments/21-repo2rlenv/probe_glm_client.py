"""One schema probe through the pinned native model client; no repository code.

The private launcher discovers the approved endpoint in its execution cluster
and supplies BIOTASKS21_GLM_ENDPOINT and BIOTASKS21_GLM_KEY in the environment.
Never include those values in public reports. This probe makes no fallback or
retry request. Run with the pinned Repo2RLEnv locked environment.
"""

import argparse
import json
import os
import time
from pathlib import Path

from repo2rlenv.llm import complete
from repo2rlenv.spec.input import LLMSpec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Refuse accidental repetition of a request with an existing receipt.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump({"status": "claimed", "model_calls_dispatched": 0}, handle)
    spec = LLMSpec(
        provider="openai",
        model="glm-5.3",
        endpoint=os.environ["BIOTASKS21_GLM_ENDPOINT"],
        api_key_env="BIOTASKS21_GLM_KEY",
        max_concurrent=1,
        timeout_sec=120,
        fallback=None,
    )
    record = {
        "status": "dispatched",
        "stage": "model_schema_compatibility",
        "model_calls_dispatched": 1,
        "model": "glm-5.3",
        "max_output_tokens": 1024,
        "biological_execution": False,
        "paid_fallback": False,
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    try:
        response = complete(
            spec,
            system="Return only the requested JSON object.",
            user='Return an object whose status is "ok" and whose value is 2.',
            max_tokens=1024,
            response_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["ok"]},
                    "value": {"type": "integer", "enum": [2]},
                },
                "required": ["status", "value"],
                "additionalProperties": False,
            },
        )
        parsed = json.loads(response.content)
        valid = (
            isinstance(parsed, dict)
            and set(parsed) == {"status", "value"}
            and parsed["status"] == "ok"
            and type(parsed["value"]) is int
            and parsed["value"] == 2
        )
        record.update(
            status="passed" if valid else "invalid_response",
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            usage_present=response.usage is not None,
            client_cost_estimate_usd=response.cost_usd,
            cost_basis="client estimate, not a provider receipt",
        )
    except Exception as exc:
        # Provider exception messages can contain private endpoints or bodies.
        record.update(status="failed", error_type=type(exc).__name__)
    finally:
        record["elapsed_sec"] = round(time.monotonic() - started, 3)
        args.output.write_text(json.dumps(record, indent=2) + "\n")
    if record["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
