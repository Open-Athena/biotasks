"""Run native SWE-flow docstring/specification stages on saved contrasts.

Use only in the approved model-client environment. This prepares authoring
artifacts; export and native controls remain separate required stages.
"""

import argparse
import json
import os
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_flow.author import author
from repo2rlenv.spec.input import LLMSpec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adaptation", type=Path, required=True)
    args = parser.parse_args()
    generation = json.loads((args.generation / "generation.json").read_text())
    if generation["attempted"] > 10 or len(generation["candidates"]) > 3:
        raise ValueError("Input exceeds the approved cohort bounds")
    settings = json.loads(args.adaptation.read_text())
    if settings["stage"] != "generation_only" or settings["paid_fallback"]:
        raise ValueError("Invalid generation adaptation")
    args.output.mkdir(parents=True, exist_ok=False)
    save_record(args.output / "adaptation.json", settings)
    model = LLMSpec(
        provider="openai",
        model="glm-5.3",
        endpoint=os.environ["BIOTASKS21_GLM_ENDPOINT"],
        api_key_env="BIOTASKS21_GLM_KEY",
        max_concurrent=1,
        timeout_sec=settings["request_timeout_sec"],
        fallback=None,
    )
    # Eighteen native reservations of $0.75 fit this audit-only ledger.
    # These are not charges for the existing free GLM service.
    ledger = BudgetLedger(args.output / "native-model-reservations.sqlite", limit_usd="15")
    records = []
    with adapted_authoring(settings, args.output, metering_target="structured"):
        for candidate in generation["candidates"]:
            identifier = candidate["id"]
            record = {"candidate_id": identifier, "status": "dispatched"}
            records.append(record)
            save_record(
                args.output / "issues.json", {"stage": "flow_authoring", "records": records}
            )
            try:
                documents, instruction = author(
                    candidate,
                    model,
                    ledger,
                    args.output / "models" / identifier,
                    operation_prefix=f"flow:{identifier}",
                    resume=False,
                )
                record.update(status="authored", docstrings=documents, instruction=instruction)
            except Exception as exc:
                # Provider exception bodies may contain private routing details.
                record.update(status="failed", error_type=type(exc).__name__)
            save_record(
                args.output / "issues.json", {"stage": "flow_authoring", "records": records}
            )


if __name__ == "__main__":
    main()
