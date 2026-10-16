"""Author native SWE-smith issues from saved execution contrasts using free GLM.

Run in the approved model-client location, never inside a target-code container.
Credentials and endpoint are supplied by the private launcher. Each candidate
retains the native two-attempt authoring bound. This does not export or validate
Harbor tasks; model review is not the reward.
"""

import argparse
import json
import os
from contextlib import nullcontext
from pathlib import Path

from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_smith.issue import write_issue
from repo2rlenv.spec.input import LLMSpec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adaptation", type=Path)
    parser.add_argument("--review-feedback", type=Path)
    args = parser.parse_args()
    generation = json.loads((args.generation / "generation.json").read_text())
    if generation["attempted"] > 10 or len(generation["candidates"]) > 3:
        raise ValueError("Input exceeds the checkpointed cohort limits")
    args.output.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.adaptation.read_text()) if args.adaptation else None
    if settings:
        if settings["stage"] != "generation_only" or settings["paid_fallback"]:
            raise ValueError("Invalid generation adaptation")
        save_record(args.output / "adaptation.json", settings)
    model = LLMSpec(
        provider="openai",
        model="glm-5.3",
        endpoint=os.environ["BIOTASKS21_GLM_ENDPOINT"],
        api_key_env="BIOTASKS21_GLM_KEY",
        max_concurrent=1,
        timeout_sec=settings["request_timeout_sec"] if settings else 120,
        fallback=None,
    )
    # Retain native reservations for audit. This ledger does not measure free
    # GLM's actual charges; zero-cost responses remain uncertain upstream.
    ledger = BudgetLedger(args.output / "native-model-reservations.sqlite", limit_usd="5")
    records = []
    if settings:
        from glm_authoring_adapter import adapted_authoring

        context = adapted_authoring(settings, args.output)
    else:
        context = nullcontext()
    with context:
        feedback = json.loads(args.review_feedback.read_text()) if args.review_feedback else {}
        if feedback:
            save_record(args.output / "review-feedback.json", feedback)
        author_candidates(args, generation, model, ledger, records, feedback)


def author_candidates(args, generation, model, ledger, records, feedback):
    for candidate in generation["candidates"]:
        identifier = candidate["id"]
        record = {"candidate_id": identifier, "status": "dispatched"}
        records.append(record)
        save_record(args.output / "issues.json", {"stage": "issue_authoring", "records": records})
        try:
            issue = write_issue(
                args.generation,
                candidate,
                model,
                ledger,
                args.output / "models" / f"{identifier}.json",
                operation_id=f"issue:swe-smith:{identifier}",
                review_feedback=feedback.get(identifier),
            )
            record.update(status="authored", issue=issue.issue, reason=issue.reason)
        except Exception as exc:
            # Preserve receipts; do not print provider exception bodies.
            record.update(status="failed", error_type=type(exc).__name__)
        save_record(args.output / "issues.json", {"stage": "issue_authoring", "records": records})


if __name__ == "__main__":
    main()
