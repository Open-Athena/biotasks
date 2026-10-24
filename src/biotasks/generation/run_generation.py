"""Resume source-bound official generation through the existing lifecycle."""

import copy
import json
import time
from importlib.resources import files
from pathlib import Path
from typing import Any

from biotasks.generation import resources
from biotasks.generation.generation_pipeline import GenerationPipeline
from biotasks.validation.files import json_sha, read_json, require, sha
from biotasks.validation.planning import code_identity


def verify(root: Path, *, allow_legacy: bool = False) -> dict[str, Any]:
    plan = read_json(root / "plan.json")
    original = copy.deepcopy(plan)
    identity = original.pop("plan_identity")
    require(json_sha(original) == identity, "Generation plan changed")
    require(plan["validation_code_identity"] == code_identity(), "Shared lifecycle code changed")
    require(
        sha(Path(plan["backend"]["config"])) == plan["backend_config_sha256"],
        "SDK configuration changed",
    )
    if "generation_code_identity" in plan:
        require(
            plan["generation_code_identity"] == resources.code_identity(),
            "Generation implementation changed",
        )
    else:
        # A known old receipt is import-only. No active old plan may be driven by
        # a differently packaged implementation or silently upgraded in place.
        legacy = json.loads((files("biotasks.generation") / "legacy-profile.json").read_bytes())
        require(
            allow_legacy and all(plan.get(key) == value for key, value in legacy.items()),
            "Unsupported historical generation profile",
        )
    group = plan["group"]
    for name, digest in group["payload_sha256"].items():
        require(sha(root / group["payload_directory"] / name) == digest, "Frozen payload changed")
    require(
        sha(root / group["notices"]["path"]) == group["notices"]["sha256"], "Source notices changed"
    )
    return plan


def run(root: Path, once: bool = False) -> dict[str, Any]:
    plan = verify(root)
    pipeline = GenerationPipeline(root, plan, plan["group"])
    while True:
        state = pipeline.step()
        if state == "complete":
            readback = read_json(pipeline.directory / "readback.json")
            held = (
                (pipeline.directory / "model-budget-hold.json").exists()
                or (pipeline.directory / "budget-hold.json").exists()
                or not readback["model_billing"]["complete"]
            )
            return {
                "state": "held" if held else "complete",
                "generation_workflow": state,
                "exported_tasks": readback["exported_tasks"],
                "model_billing": readback["model_billing"],
                "native_controls_run": False,
            }
        if state.startswith("held:") or once:
            return {"state": state, "run_id": plan["group"]["run_id"]}
        stage = state.split(":", 1)[-1]
        if (
            stage
            in {
                "submission_recorded",
                "remote_terminal",
                "archive_readback_verified",
                "cleanup_terminal",
            }
            and not (pipeline.directory / (stage + ".json")).exists()
        ):
            time.sleep(300)
