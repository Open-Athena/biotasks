"""One approved 16,384-token replay of a saved native authoring request.

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

from pydantic import TypeAdapter
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.llm import LLMResponse, complete
from repo2rlenv.pipelines.recipes.swe_smith.issue import IssueReport, issue_violations
from repo2rlenv.spec.input import LLMSpec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    candidate = json.loads(args.candidates.read_text())["candidates"][0]
    if candidate["id"] != "0e17fb52981f3f272561":
        raise ValueError("Unexpected frozen candidate")
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
        "stage": "authoring_combined_token_adaptation",
        "model_calls_dispatched": 1,
        "model": "glm-5.3",
        "max_output_tokens": 16384,
        "biological_execution": False,
        "paid_fallback": False,
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    try:
        response = complete(
            spec,
            system=request["system"],
            user=request["user"],
            max_tokens=16384,
            response_schema=request["response_schema"],
        )
        # LiteLLM usage is only shallowly converted to dict by the native client;
        # nested token-detail objects still need Pydantic JSON normalization.
        normalized = TypeAdapter(LLMResponse).dump_python(response, mode="json")
        save_record(args.output.with_suffix(".response.json"), normalized)
        record["content"] = normalized["content"]
        record["usage"] = normalized["usage"]
        record["prompt_tokens"] = response.prompt_tokens
        record["completion_tokens"] = response.completion_tokens
        details = (normalized["usage"] or {}).get("completion_tokens_details") or {}
        reasoning = details.get("reasoning_tokens")
        record["reasoning_tokens"] = reasoning
        record["non_reasoning_completion_tokens"] = (
            response.completion_tokens - reasoning if isinstance(reasoning, int) else None
        )
        parsed = IssueReport.model_validate_json(response.content)
        violations = issue_violations(parsed, candidate)
        record["native_issue_violations"] = violations
        valid = not violations
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
