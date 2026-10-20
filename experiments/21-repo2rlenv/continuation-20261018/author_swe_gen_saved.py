"""Invoke the unchanged native SWE-gen author on one successful saved context."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_gen.instruction import write_instruction
from repo2rlenv.spec.input import LLMSpec
from repo2rlenv.spec.recipe_options import PRRecipeOptions


def main():
    parser = argparse.ArgumentParser()
    for name in ("candidate", "source", "profile", "adaptation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    candidate = json.loads(args.candidate.read_text())
    source = json.loads(args.source.read_text())
    profile = json.loads(args.profile.read_text())
    assert hashlib.sha256(args.source.read_bytes()).hexdigest() == profile["source_sha256"]
    assert all(candidate[k] == value for k, value in source.items())
    assert profile["recipe"] == "swe_gen" and profile["source"]["urls"] == [source["url"]]
    options = PRRecipeOptions.model_validate(profile["options"])
    assert options.target == 3 and options.max_candidates == 10
    assert candidate["source_files"] == options.source_paths
    assert candidate["contrast"]["FAIL_TO_PASS"]
    settings = json.loads(args.adaptation.read_text())
    assert settings["stage"] == "generation_only" and not settings["paid_fallback"]
    args.output.mkdir(parents=True, exist_ok=False)
    record = {"stage": "native_swe_gen_author_not_export_or_admission",
              "candidate_id": candidate["id"], "status": "dispatched",
              "maximum_native_calls": 1, "task_specific_feedback": False}
    save_record(args.output / "author-result.json", record)
    model = LLMSpec(
        provider="openai", model="glm-5.3", endpoint=os.environ["BIOTASKS21_GLM_ENDPOINT"],
        api_key_env="BIOTASKS21_GLM_KEY", max_concurrent=1,
        timeout_sec=settings["request_timeout_sec"], fallback=None,
    )
    # Same internal reservation ledger ceiling as the native pipeline controller;
    # this is not a charge for the approved free endpoint. The function runs once.
    ledger = BudgetLedger(args.output / "native-model-reservations.sqlite", limit_usd="50")
    try:
        with adapted_authoring(settings, args.output, metering_target="swe_gen"):
            instruction = write_instruction(
                candidate, options, model, ledger,
                args.output / "models/instruction.json",
                operation_id="instruction:swe-gen:" + candidate["id"], resume=False,
            )
        record.update(status="authored" if instruction.is_substantial else "native_substantiality_rejected",
                      result=instruction.model_dump(mode="json"))
    except Exception as exc:
        record.update(status="failed_no_replay", error_type=type(exc).__name__)
        raise
    finally:
        save_record(args.output / "author-result.json", record)


if __name__ == "__main__":
    main()
