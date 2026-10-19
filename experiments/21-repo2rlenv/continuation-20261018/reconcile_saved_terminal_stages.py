"""Read retained native receipts to identify unfinished stages without replaying calls."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_models(folder):
    rows = []
    for candidate in sorted((folder / "candidates").iterdir()):
        seed_path = candidate / "seed.json"
        seed = json.loads(seed_path.read_text())
        identity = hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()
        assert identity.startswith(candidate.name)
        models = []
        for path in sorted(candidate.glob("*.json")):
            item = json.loads(path.read_text())
            if isinstance(item, dict) and "operation_id" in item and "status" in item:
                models.append({"file": path.name, "sha256": digest(path),
                               "status": item["status"], "has_response": bool(item.get("response")),
                               "request_sha256": item.get("request_sha256")})
        rows.append({"seed_sha256": identity, "seed_file_sha256": digest(seed_path), "models": models})
    return rows


def reconcile(private):
    recipes = [
        ("seta_seed2synth", "seta-genomic-intervals-v1", "seta-design-01", "seta-build-01",
         "seta-build-recovered/campaign/author-output/runs/seta-build-01"),
        ("seta_evol", "pr2633-parent-v1", "parent-evolution-design-01", "parent-evolution-build-01",
         "parent-evolution-build-01-recovered/campaign/author-output/runs/parent-evolution-build-01"),
    ]
    result = []
    for recipe, cohort, design_run, build_run, relative in recipes:
        design_path = ROOT / "evidence" / design_run / "designs.json"
        designs = json.loads(design_path.read_text())
        design_manifest = ROOT / f"hf-{'seta-design' if recipe == 'seta_seed2synth' else design_run}-snapshot-manifest.json"
        published = json.loads(design_manifest.read_text())
        assert any(f["path"].endswith("designs.json") and f["sha256"] == digest(design_path) for f in published["files"])
        folder = private / relative
        built = read_models(folder)
        begun = {row["seed_sha256"] for row in built}
        records = designs["records"]
        assert len(records) == 3 and begun <= {row["seed_sha256"] for row in records}
        pending = [row["seed_sha256"] for row in records if row["status"] == "designed" and row["seed_sha256"] not in begun]
        assert len(pending) == 1
        all_models = [m for row in built for m in row["models"]]
        assert sum(m["status"] == "dispatched" and not m["has_response"] for m in all_models) == 1
        result.append({
            "recipe": recipe, "cohort": cohort, "declared_input_count": len(records),
            "already_charged_candidates": 3, "new_candidate_charge_for_pending_build": 0,
            "design_source": str(design_path.relative_to(ROOT)), "design_source_sha256": digest(design_path),
            "design_snapshot_manifest": design_manifest.name, "design_snapshot_manifest_sha256": digest(design_manifest),
            "build_snapshot_manifest": f"hf-{build_run}-snapshot-manifest.json",
            "build_snapshot_manifest_sha256": digest(ROOT / f"hf-{build_run}-snapshot-manifest.json"),
            "build_run_state": json.loads((folder / "run.json").read_text())["state"],
            "build_run_state_sha256": digest(folder / "run.json"),
            "prior_native_candidate_receipts": built,
            "pending_first_build_seed_sha256": pending,
            "do_not_replay_seed_sha256": sorted(begun),
            "failed_design_seed_sha256": [row["seed_sha256"] for row in records if row["status"] == "failed"],
            "completed_builder_responses": sum(m["status"] == "completed" and m["has_response"] for m in all_models),
            "uncertain_builder_requests": 1,
            "action": "Continue only the never-built saved design through native build/repair/trial/export; no design regeneration or external feedback.",
        })
    folder = private / "tmax-biological-02-recovered/campaign/author-output/runs/tmax-biological-build-01"
    run = json.loads((folder / "run.json").read_text())
    rows = read_models(folder)
    assert run["state"] == "completed" and len(run["skipped"]) == len(rows) == 3 and not run["tasks"]
    assert set(run["skipped"].values()) == {"design_schema"}
    for row in rows:
        assert len(row["models"]) == 4
        assert all(m["status"] == "completed" and m["has_response"] for m in row["models"])
    selected = ROOT / "seeds/tmax-biological-v1/selected-inputs.json"
    assert {hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest() for seed in json.loads(selected.read_text())} == {row["seed_sha256"] for row in rows}
    result.append({
        "recipe": "tmax", "cohort": "tmax-biological-v1", "declared_input_count": 3,
        "already_charged_candidates": 3, "remaining_numeric_candidate_allowance": 7,
        "pending_first_build_seed_sha256": [], "fresh_declared_inputs_remaining": 0,
        "native_run_state": "completed", "exported_tasks": 0,
        "native_rejection_reasons": run["skipped"], "native_run_state_sha256": digest(folder / "run.json"),
        "selected_inputs": str(selected.relative_to(ROOT)), "selected_inputs_sha256": digest(selected),
        "completed_model_responses": 12, "uncertain_model_requests": 0,
        "prior_native_candidate_receipts": rows,
        "snapshot_manifest": "hf-tmax-biological-02-snapshot-manifest.json",
        "snapshot_manifest_sha256": digest(ROOT / "hf-tmax-biological-02-snapshot-manifest.json"),
        "state": "declared_input_pool_exhausted_below_target",
        "action": "Report the bounded automatic negative result; do not regenerate consumed inputs, reset repairs or manually normalize failed code.",
    })
    return {"stage": "native_receipt_based_pending_stage_reconciliation", "rows": result,
            "manual_task_fixes": 0, "new_model_calls": 0, "new_trials": 0,
            "limits": ["Original private receipts remain private; these are hashes, states and counters only.",
                       "A pending build is an unfinished stage of an already charged candidate, not a new source input.",
                       "Dispatched requests without responses remain uncertain and must not be replayed.",
                       "This audit does not authorize expanding any original input pool or repair limit."]}


if __name__ == "__main__":
    report = reconcile(Path(sys.argv[1]))
    (OUT / "saved-terminal-stage-reconciliation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({row["recipe"]: {"pending_first_builds": len(row["pending_first_build_seed_sha256"]),
                                      "prior_model_responses": row.get("completed_builder_responses", row.get("completed_model_responses"))}
                      for row in report["rows"]}))
