"""Freeze complete inputs for two untouched saved-design continuations; launch nothing."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
sys.path.insert(0, str(ROOT))
from package_provider_task import pack  # noqa: E402


def freeze(private):
    proof_path = BASE / "saved-terminal-stage-reconciliation.json"
    proof = json.loads(proof_path.read_text())
    common = {
        "run_saved_terminal_stage_trc.py": BASE / "run_saved_terminal_stage_trc.py",
        "run_saved_terminal_build.py": BASE / "run_saved_terminal_build.py",
        "saved-terminal-stage-reconciliation.json": proof_path,
        **{name: ROOT / name for name in (
            "run_dataarc_build.py", "build_dataarc.py", "replay_seta_designs.py",
            "replay_parent_evolution.py", "glm_authoring_adapter.py", "preserve_author_output.py",
            "package_provider_task.py", "glm-generation-adaptation.json")},
    }
    for recipe in ("seta_seed2synth", "seta_evol"):
        row = next(row for row in proof["rows"] if row["recipe"] == recipe)
        destination = private / ("saved-terminal-" + recipe + "-20261019-01")
        destination.mkdir(exist_ok=False)
        paths = dict(common, **{"saved-designs.json": ROOT / row["design_source"]})
        if recipe == "seta_seed2synth":
            paths["seeds.json"] = ROOT / "seeds/seta-genomic-intervals/seeds.json"
        else:
            paths["parent-manifest.json"] = ROOT / "seeds/pr2633-parent-v1/manifest.json"
            bundled = destination / "parent-bundle.tar.gz"
            bundle_manifest = pack(ROOT / "seeds/pr2633-parent-v1/parent", bundled)
            (destination / "parent-bundle-manifest.json").write_text(json.dumps(bundle_manifest, indent=2) + "\n")
        for name, source in paths.items():
            shutil.copyfile(source, destination / name)
        for name in ("run_saved_terminal_build.py", "run_saved_terminal_stage_trc.py"):
            compile((destination / name).read_text(), name, "exec")
        records = {}
        for path in sorted(destination.iterdir()):
            data = path.read_bytes()
            records[path.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        manifest = {
            "stage": "prepared_offline_not_dispatched_saved_design_native_continuation",
            "recipe": recipe, "files": records,
            "selected_seed_sha256": row["pending_first_build_seed_sha256"][0],
            "design_source_sha256": row["design_source_sha256"],
            "prior_candidate_charge": 3, "new_candidate_charge": 0,
            "campaign_target": 3, "campaign_candidate_cap": 10,
            "maximum_first_builds": 1, "maximum_native_repairs": 2,
            "manual_task_fixes": 0, "external_author_feedback": False, "new_design_calls": 0,
            "controller": "existing_free_reserved_TRC_CPU", "required_controller_and_sandbox_slots": 2,
            "sandbox": {"cpu": 2, "memory_gib": 4, "disk_gib": 10},
            "GLM": "existing_free_endpoint_via_finite_inference_only_client",
            "combined_output_token_limit": 131072, "reasoning_effort": "medium", "request_timeout_sec": 1200,
            "maximum_controller_seconds": 6600, "total_run_ceiling_seconds": 7200,
            "budget_hold_usd_if_dispatched": 5, "budget_reserved_by_this_preparation": False,
            "native_source_revision": "27d04ee8203cd5b2f20c3997d13836e5f5b64238",
            "source_sha256": "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755",
            "dispatch_gate": "Eight offline checks passed; require free resource claims, verified >120s proxy profile, sufficient finite client lifetime and checkpointed exact inputs before submission.",
            "assessment": "Assess unchanged final native output only; a rejected result receives no task edits or external repair feedback.",
        }
        payload = json.dumps(manifest, indent=2) + "\n"
        (destination / "dispatch-inputs.json").write_text(payload)
        (BASE / (recipe + "-saved-stage-01-dispatch-manifest.json")).write_text(payload)
        print(json.dumps({"recipe": recipe, "files": len(records), "pending_first_builds": 1, "remote_launches": 0}))


if __name__ == "__main__":
    freeze(Path(sys.argv[1]))
