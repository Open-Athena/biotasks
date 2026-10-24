"""Independent historical input/contract comparison; no transport or execution."""

import json
from pathlib import Path

import handoff
from biotasks.validation import bridge, controller
from biotasks.validation.files import inventory, read_json, require, sha, write_json

ROOT = Path(__file__).resolve().parent


def main():
    config = read_json(ROOT / "historical-handoff-config.json")
    acquisition = read_json(ROOT / "historical-acquisition.json")
    native = handoff.source_api(
        Path(config["upstream_source"]),
        Path(config["upstream_manifest"]),
        Path(config["upstream_extra_modules"]),
    )
    output = Path(config["output_directory"])
    before = inventory(output)
    native.prepare_dataset_for_push = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Completed preparation cannot rerun exporter")
    )
    result = handoff.prepare(config, native)
    require(inventory(output) == before, "Completed invocation changed historical preparation")
    bridge.call = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("No SDK transport permitted")
    )
    plan_root = ROOT / "inputs-private/historical-validation-plan"
    plan = controller.verify_plan(plan_root)
    require(
        len(plan["tasks"]) == acquisition["tasks"] == 12 and not plan["unsupported"],
        "Historical planning incomplete",
    )
    old = {row["path"]: row for row in acquisition["raw_files"]}
    new = {row["path"]: row for row in result["prepared_files"]}
    require(set(old) == set(new) and len(old) == 120, "Historical file inventory differs")
    require(
        all(old[name]["mode"] == new[name]["mode"] for name in old),
        "Original executable/file mode changed",
    )
    changed = sorted(name for name in old if old[name] != new[name])
    require(
        len(changed) == 24
        and all(name.endswith(("/environment/Dockerfile", "/task.toml")) for name in changed),
        "Unexpected historical file changes",
    )
    details = []
    for group in plan["tasks"]:
        task = group["task"]
        source = Path(config["raw_exports"]) / task["task"]
        prepared = output / "handoff/prepared" / task["task"]
        require(
            handoff.grading_contract(source / "task.toml")
            == handoff.grading_contract(prepared / "task.toml"),
            "Historical grading contract differs",
        )
        prefix = task["relative_directory"] + "/"
        require(
            all(row["path"].startswith(prefix) for row in task["files"]),
            "Unexpected validator package paths",
        )
        snapshot = [{**row, "path": row["path"].removeprefix(prefix)} for row in task["files"]]
        require(snapshot == inventory(prepared), "Validator did not snapshot prepared bytes/modes")
        require(
            task["expected_f2p"] == len(read_json(source / "tests/f2p.json"))
            and task["expected_p2p"] == len(read_json(source / "tests/p2p.json")),
            "Tracked test IDs changed",
        )
        details.append(
            {
                "task": task["task"],
                "base_commit": task["base_commit"],
                "expected_f2p": task["expected_f2p"],
                "expected_p2p": task["expected_p2p"],
                "verifier_seconds": task["verifier_seconds"],
                "agent_seconds": task["agent_seconds"],
                "source_identity": task["source_identity"],
            }
        )
    ledger = Path(config["validation_template"]["budget_ledger"])
    budget = read_json(ledger)
    require(
        budget["new_model_calls"] == 0 and budget["outstanding_cpu_hour_reservations"] == 0,
        "Historical planning admitted execution",
    )
    write_json(
        ROOT / "historical-handoff-proof.json",
        {
            "kind": "Historical raw/cache -> unchanged local exporter -> real supported validator planning; no fresh generation or controls",
            "input_checkpoint": "2ab7fc56",
            "source_acquisition_sha256": sha(ROOT / "historical-acquisition.json"),
            "handoff_sha256": sha(output / "handoff/handoff.json"),
            "handoff_code_sha256": sha(ROOT / "handoff.py"),
            "validation_plan_identity": plan["plan_identity"],
            "validation_code_identity": plan["code_identity"],
            "historical_tasks": len(details),
            "raw_files": len(old),
            "changed_files": changed,
            "all_file_modes_preserved": True,
            "grading_assets_and_settings_preserved": True,
            "completed_preparation_reinvocation_inert": True,
            "completed_plan_verification_no_transport": True,
            "unsupported": plan["unsupported"],
            "new_model_calls": 0,
            "remote_jobs": 0,
            "budget_ledger_sha256": sha(ledger),
            "tasks": details,
        },
    )
    print(
        json.dumps(
            {
                "historical_tasks_prepared_and_planned": len(details),
                "modes_and_grading_preserved": True,
                "completed_reinvocation_inert": True,
                "new_model_calls": 0,
                "remote_jobs": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
