"""Run native SETA design on declared seeds; no building or acceptance claims."""

import argparse
import hashlib
import json
import os
import random
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from preserve_author_output import preserve
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.seta_seed2synth import recipe
from repo2rlenv.pipelines.recipes.terminal.runner import load_seeds
from repo2rlenv.spec.input import LLMSpec


def main():
    if os.environ.get("REPO2RLENV_MODEL_WORKER") != "1" or not os.environ.get("IRIS_OUTPUT_DIR"):
        raise RuntimeError("Approved model worker with task-output capture required")
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--adaptation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if hashlib.sha256(args.seeds.read_bytes()).hexdigest() != manifest["seed_file_sha256"]:
        raise ValueError("Declared seed file changed")
    seeds = load_seeds(args.seeds)
    if not 1 <= len(seeds) <= min(10, manifest["available_seed_candidates"]):
        raise ValueError("Unexpected cohort size")
    random.Random(24).shuffle(seeds)
    settings = json.loads(args.adaptation.read_text())
    if settings["stage"] != "generation_only" or settings["paid_fallback"]:
        raise ValueError("Invalid generation settings")
    args.output.mkdir(parents=True, exist_ok=False)
    model = LLMSpec(provider="openai", model="glm-5.3",
                    endpoint=os.environ["BIOTASKS21_GLM_ENDPOINT"],
                    api_key_env="BIOTASKS21_GLM_KEY", max_concurrent=1,
                    timeout_sec=settings["request_timeout_sec"], fallback=None)
    # Native audit reservations are not billed costs for the existing free service.
    ledger = BudgetLedger(args.output / "native-model-reservations.sqlite", limit_usd="8")
    records = []
    save_record(args.output / "settings.json", {"stage": "design_only", "adaptation": settings,
                "cohort": manifest["cohort"], "seed_file_sha256": manifest["seed_file_sha256"],
                "max_calls": len(seeds), "native_retries": 0, "native_max_tokens": 9000})
    try:
        with adapted_authoring(settings, args.output, metering_target="seta_seed2synth"):
            for seed in seeds:
                digest = hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()
                record = {"seed_id": seed["id"], "seed_sha256": digest, "status": "dispatched"}
                records.append(record)
                save_record(args.output / "designs.json", {"stage": "design_only", "records": records})
                try:
                    design = recipe.design(seed, model=model, ledger=ledger,
                                           receipt=args.output / "models" / (digest + ".json"),
                                           operation_id="seta-design:" + digest, resume=False)
                    record.update(status="designed", design=design.model_dump(mode="json"))
                except Exception as exc:
                    record.update(status="failed", error_type=type(exc).__name__)
                save_record(args.output / "designs.json", {"stage": "design_only", "records": records,
                            "built_tasks": 0, "independently_validated_tasks": 0})
    finally:
        preserve(args.output, Path(os.environ["IRIS_OUTPUT_DIR"]))


if __name__ == "__main__":
    main()
