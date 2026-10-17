"""Continue frozen SETA designs through native remote build/repair/trial/export.

Run on an authorized controller with a prepared GenerationInput and worker receipt.
Worker allocation and cleanup belong to that controller, as in the native runner.
"""

import argparse
import dataclasses
import json
import os
from pathlib import Path

from glm_authoring_adapter import adapted_authoring
from preserve_author_output import preserve
from replay_seta_designs import saved_designer
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.terminal import runner
from repo2rlenv.pipelines.terminal_synth import TerminalSynthesisPipeline
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.recipe_options import TerminalSynthesisOptions


def main():
    if os.environ.get("REPO2RLENV_MODEL_WORKER") != "1" or not os.environ.get("IRIS_OUTPUT_DIR"):
        raise RuntimeError("Approved model controller with output capture required")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--designs", type=Path, required=True)
    parser.add_argument("--designs-sha256", required=True)
    parser.add_argument("--adaptation", type=Path, required=True)
    args = parser.parse_args()
    designer = saved_designer(args.designs, args.designs_sha256)
    spec = GenerationInput.model_validate_json(args.input.read_text())
    options = TerminalSynthesisOptions(target=3, max_candidates=3)
    pipeline = TerminalSynthesisPipeline(spec, options)
    settings = json.loads(args.adaptation.read_text())
    if settings["stage"] != "generation_only" or settings["paid_fallback"]:
        raise ValueError("Invalid generation adaptation")
    if spec.llm.model != "glm-5.3" or spec.llm.fallback is not None or spec.llm.max_concurrent != 1:
        raise ValueError("Expected serial free-GLM authoring without fallback")
    if spec.llm.timeout_sec != settings["request_timeout_sec"] or spec.execution.timeout_sec > 7200:
        raise ValueError("Unexpected request or execution deadline")
    output = spec.execution.campaign_dir
    save_record(output / "seta-build-settings.json", {
        "stage": "native_build_from_saved_designs", "designs_sha256": args.designs_sha256,
        "native_options": options.model_dump(mode="json"), "adaptation": settings,
        "design_model_calls": 0, "independent_acceptance": False,
    })
    try:
        with adapted_authoring(settings, output, metering_target="terminal_builder"):
            result = runner.run_synthesis(
                spec, options, Path(spec.output.destination), pipeline.on_event, designer=designer,
            )
        record = dataclasses.asdict(result)
        record["out_dir"] = str(result.out_dir)
        save_record(output / "seta-build-result.json", record)
    finally:
        preserve(output, Path(os.environ["IRIS_OUTPUT_DIR"]))


if __name__ == "__main__":
    main()
