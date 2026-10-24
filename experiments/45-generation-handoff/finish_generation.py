"""Consume a completed generation once: audited local export then native controls.

This connector never starts or restarts generation. It waits on the existing
source-bound journal, then uses the same recorded raw/cache bytes. The handoff's
base manifest remains immutable; a separate execution-policy manifest adds the
already reviewed notices/publication policy before the ordinary validator plans.
"""

import argparse
import copy
import time
from pathlib import Path

import handoff
import run_generation
from biotasks.validation import controller, planning
from biotasks.validation.archives import records
from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json
from biotasks.validation.journal import STAGES
from generation_pipeline import GenerationPipeline

ROOT = Path(__file__).resolve().parent


def verify_generation_source(directory, readback):
    expected = [{**row, "mode": oct(row["mode"])[2:]} for row in readback["source_members"]]
    require(
        inventory(directory / "generation-source") == expected,
        "Extracted raw/cache lineage differs from verified original generation",
    )


def generation_ready(root):
    plan = run_generation.verify(root)
    directory = root / "runs" / plan["group"]["id"]
    held = directory / "held.json"
    if held.exists():
        return {"state": "held", "reason": read_json(held)["reason"]}
    path = directory / "journal.json"
    if not path.exists() or [s["stage"] for s in read_json(path)["stages"]] != list(STAGES):
        return {"state": "waiting_for_existing_generation", "run_id": plan["group"]["run_id"]}
    pipeline = GenerationPipeline(root, plan, plan["group"])
    require(pipeline.step() == "complete", "Generation journal is not independently complete")
    readback = read_json(directory / "readback.json")
    if not readback["model_billing"]["complete"] or any(
        (directory / name).exists()
        for name in (
            "budget-hold.json",
            "model-budget-hold.json",
            "cleanup/budget-hold.json",
            "stop/budget-hold.json",
        )
    ):
        return {"state": "held", "reason": "Generation accounting hold; preserve the original run"}
    if readback["exported_tasks"]:
        verify_generation_source(directory, readback)
    bindings = {
        name: sha(directory / name)
        for name in (
            "journal.json",
            "readback.json",
            "cleanup-proof.json",
            "preserved/manifest.json",
            "publication.json",
            "cleanup/preserved/manifest.json",
            "cleanup/publication.json",
        )
    }
    return {
        "state": "ready",
        "plan": plan,
        "readback": readback,
        "directory": directory,
        "binding": {
            "generation_plan_sha256": sha(root / "plan.json"),
            "generation_evidence": bindings,
            "connector_sha256": sha(Path(__file__)),
        },
    }


def execute(root, output, once=False):
    ready = generation_ready(root)
    if ready["state"] != "ready":
        return ready
    plan, readback, source = ready["plan"], ready["readback"], ready["directory"]
    output.mkdir(parents=True, exist_ok=True)
    binding_file = output / "generation-binding.json"
    if binding_file.exists():
        require(
            read_json(binding_file) == ready["binding"], "Generation/connector identity changed"
        )
    else:
        require(not any(output.iterdir()), "Unowned connector output is not empty")
        write_json(binding_file, ready["binding"])
    if not readback["exported_tasks"]:
        result = {
            "state": "zero_exports",
            "generation_workflow_complete": True,
            "model_billing": readback["model_billing"],
            "new_exports": 0,
            "native_control_jobs": 0,
            "no_regeneration_or_repair": True,
        }
        write_json(output / "result.json", result)
        return result
    raw = source / "generation-source/outputs/raw"
    cache = source / "generation-source/upstream/workspace/bootstrap"
    recorded = read_json(ROOT / "historical-handoff-config.json")
    config = {
        key: recorded[key]
        for key in (
            "upstream_source",
            "upstream_manifest",
            "upstream_manifest_sha256",
            "upstream_extra_modules",
            "upstream_extra_modules_sha256",
        )
    }
    config.update(
        raw_exports=str(raw),
        bootstrap_cache=str(cache),
        raw_inventory_sha256=json_sha(inventory(raw)),
        cache_inventory_sha256=json_sha(inventory(cache)),
        output_directory=str(output / "prepared-local"),
        publication={"eligible": False},
        validation_template={
            "schema_version": 1,
            "id": "issue45-fresh",
            "repo2rlenv_revision": plan["repo2rlenv_revision"],
            "backend": plan["backend"],
            "budget_ledger": plan["budget_ledger"],
            "max_cpu_hours_per_task": 6,
            "archive": {"kind": "local"},
        },
    )
    path = output / "handoff-config.json"
    if path.exists():
        require(read_json(path) == config, "Prepared raw/cache/config identity changed")
    else:
        write_json(path, config)
    native = handoff.source_api(
        Path(config["upstream_source"]),
        Path(config["upstream_manifest"]),
        Path(config["upstream_extra_modules"]),
    )
    result = handoff.prepare(config, native)
    require(
        result["task_count"] == len(readback["exported_tasks"]),
        "Local export count differs from native generation",
    )
    prepared = Path(config["output_directory"]) / "handoff"
    manifest = copy.deepcopy(read_json(prepared / "validation-manifest.json"))
    manifest["archive"] = plan["archive"]
    notice_data = records(root / plan["group"]["notices"]["path"], "tar.gz")
    notice_dir = output / "notices"
    notice_dir.mkdir(exist_ok=True)
    for name, row in notice_data.items():
        target = notice_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            require(sha(target) == row["sha256"], "Reviewed notice changed")
        else:
            target.write_bytes(row["data"])
            target.chmod(row["mode"])
    for export in manifest["exports"]:
        export["path"] = str((prepared / export["path"]).resolve())
        export["publication"] = plan["group"]["publication"]
        export["notices"] = [str(notice_dir / name) for name in sorted(notice_data)]
    execution_manifest = output / "validation-execution-manifest.json"
    if execution_manifest.exists():
        require(
            read_json(execution_manifest) == manifest, "Frozen validation execution policy changed"
        )
    else:
        write_json(execution_manifest, manifest)
    validation = output / "validation"
    if not validation.exists():
        planning.prepare(execution_manifest, validation)
    else:
        controller.verify_plan(validation)
    state = controller.run(validation, once=once)
    if state["state"] != "complete":
        return {
            "state": state["state"],
            "validation": state,
            "generation_workflow_complete": True,
            "no_regeneration_or_repair": True,
        }
    frozen = controller.verify_plan(validation)
    outcomes = []
    for group in frozen["tasks"]:
        directory = validation / "runs" / group["id"]
        outcome = read_json(directory / "readback.json")
        outcomes.append(
            {
                "task": group["task"]["task"],
                "readback": outcome,
                "primary_publication": read_json(directory / "publication.json"),
                "cleanup": read_json(directory / "cleanup-proof.json"),
                "cleanup_publication": read_json(directory / "cleanup/publication.json"),
            }
        )
    result = {
        "state": "complete",
        "generation_workflow_complete": True,
        "model_billing": readback["model_billing"],
        "new_exports": result["task_count"],
        "validation": state,
        "outcomes": outcomes,
        "no_regeneration_or_repair": True,
        "new_model_calls_in_connector": 0,
        "validation_manifest_sha256": sha(execution_manifest),
        "validation_plan_identity": frozen["plan_identity"],
    }
    write_json(output / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    root, output = args.generation_root.resolve(), args.output.resolve()
    require(
        not output.is_relative_to(root),
        "Connector outputs must be separate from the generation evidence",
    )
    while True:
        result = execute(root, output, args.once)
        if result["state"] != "waiting_for_existing_generation" or not args.wait:
            print(__import__("json").dumps(result, indent=2))
            return
        time.sleep(300)


if __name__ == "__main__":
    main()
