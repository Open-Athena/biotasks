"""Source-bound local export from a completed generation; no runtime repairs."""

import copy
from pathlib import Path

from biotasks.validation.files import inventory, json_sha, read_json, require, sha, write_json


def prepare_handoff(manifest, case, ready, output):
    from biotasks.generation.planning import adapter, directory_ref, file_ref

    _, _, handoff = adapter(manifest)
    require(ready["state"] == "ready", "Only completed, billed, cleaned generation")
    plan, readback, source = ready["plan"], ready["readback"], ready["directory"]
    require(
        plan["backend"] == manifest["backend"]
        and plan["budget_ledger"] == manifest["budget_ledger"],
        "Imported infrastructure/accounting policy differs",
    )
    binding = {
        "generation": ready["binding"],
        "case": case,
        "source": manifest["source"],
        "archive": manifest["archive"],
        "connector_sha256": sha(Path(__file__)),
    }
    if output.exists():
        require(
            read_json(output / "generation-binding.json") == binding,
            "Generation/handoff identity changed",
        )
    else:
        output.mkdir(parents=True, mode=0o700)
        write_json(output / "generation-binding.json", binding)
    if not readback["exported_tasks"]:
        result = {
            "state": "zero_exports",
            "generation_workflow_complete": True,
            "model_billing": readback["model_billing"],
            "new_exports": 0,
            "native_control_jobs": 0,
            "new_model_calls_in_connector": 0,
        }
        if (output / "result.json").exists():
            require(read_json(output / "result.json") == result, "Zero-export result changed")
        else:
            write_json(output / "result.json", result)
        return result
    raw = source / "generation-source/outputs/raw"
    cache = source / "generation-source/upstream/workspace/bootstrap"
    acquisition = manifest["source"]
    config = {
        "upstream_source": str(directory_ref(acquisition["directory"])),
        "upstream_manifest": str(file_ref(acquisition["acquisition"])),
        "upstream_manifest_sha256": acquisition["acquisition"]["sha256"],
        "upstream_extra_modules": str(directory_ref(acquisition["extra_modules"])),
        "upstream_extra_modules_sha256": acquisition["extra_modules"]["inventory_sha256"],
        "raw_exports": str(raw),
        "bootstrap_cache": str(cache),
        "raw_inventory_sha256": json_sha(inventory(raw)),
        "cache_inventory_sha256": json_sha(inventory(cache)),
        "output_directory": str(output / "prepared-local"),
        "publication": {"eligible": False},
        "validation_template": {
            "schema_version": 1,
            "id": manifest["id"] + "-" + case["id"],
            "repo2rlenv_revision": manifest["repo2rlenv_revision"],
            "backend": manifest["backend"],
            "budget_ledger": manifest["budget_ledger"],
            "max_cpu_hours_per_task": 6,
            "archive": {"kind": "local"},
        },
    }
    path = output / "handoff-config.json"
    if path.exists():
        require(read_json(path) == config, "Local export input binding changed")
    else:
        write_json(path, config)
    native = handoff.source_api(
        Path(config["upstream_source"]),
        Path(config["upstream_manifest"]),
        Path(config["upstream_extra_modules"]),
    )
    result = handoff.prepare(config, native)
    require(
        result["task_count"] == len(readback["exported_tasks"]), "Native/local export counts differ"
    )
    prepared = output / "prepared-local/handoff"
    execution = copy.deepcopy(read_json(prepared / "validation-manifest.json"))
    execution["archive"] = manifest["archive"]
    notices = directory_ref(case["notices"])
    # Freeze notices separately; never point a plan at mutable operator inputs.
    notice_dir = output / "notices"
    if notice_dir.exists():
        require(inventory(notice_dir) == inventory(notices), "Frozen notice bundle changed")
    else:
        import shutil

        shutil.copytree(notices, notice_dir)
    for export in execution["exports"]:
        export["path"] = str((prepared / export["path"]).resolve())
        export["publication"] = case["publication"]
        export["notices"] = [str(notice_dir / row["path"]) for row in inventory(notice_dir)]
    execution_path = output / "validation-execution-manifest.json"
    if execution_path.exists():
        require(read_json(execution_path) == execution, "Frozen validation policy changed")
    else:
        write_json(execution_path, execution)
    result = {
        "state": "local_export_prepared",
        "new_exports": result["task_count"],
        "validation_manifest": str(execution_path),
        "validation_manifest_sha256": sha(execution_path),
        "immutable_base_manifest_sha256": sha(prepared / "validation-manifest.json"),
        "generation_mode": case["mode"],
        "new_model_calls_in_connector": 0,
        "native_control_jobs": 0,
        "controls_not_yet_executed": True,
        "default_native_emitter_unchanged": True,
        "task_repairs": False,
    }
    if (output / "result.json").exists():
        require(read_json(output / "result.json") == result, "Prepared result changed")
    else:
        write_json(output / "result.json", result)
    return result
