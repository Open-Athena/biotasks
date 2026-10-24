"""Summarize completed native evidence without inferring unique tasks or grades."""

from pathlib import Path
from typing import Any

from biotasks.generation.native import retention_root
from biotasks.retention import actor
from biotasks.validation.controller import Pipeline, verify_plan
from biotasks.validation.files import read_json, require, sha, write_json

FLAGS = (
    "complete_parseable_pair",
    "positive_control_pair",
    "clean_oracle_command",
    "all_p2p_pass_both",
)


def profile_eligible(readback: dict[str, Any]) -> bool:
    """All original collector flags must be true; missing/null evidence fails."""
    return all(readback.get(name) is True for name in FLAGS)


def summarize(validation: Path) -> dict[str, Any]:
    plan = verify_plan(validation)
    rows: list[dict[str, Any]] = []
    for group in plan["tasks"]:
        directory = validation / "runs" / group["id"]
        if (directory / "held.json").exists():
            retained = actor.run(retention_root(validation))
            result = next(
                (row for row in retained.get("results", []) if row["task_id"] == group["id"]), None
            )
            require(
                result is not None and result["state"] == "retention_complete",
                "Held evidence not fully retained/cleaned",
            )
            rows.append(
                {
                    "task": group["task"]["task"],
                    "repo": group["task"]["repo"],
                    "source_identity": group["task"]["source_identity"],
                    "run_id": group["run_id"],
                    "scientific_state": "held_unaccepted",
                    **dict.fromkeys(FLAGS, False),
                    "eligible_for_this_control_profile": False,
                    "retention": result,
                }
            )
            continue
        require(
            Pipeline(validation, plan, group).step() == "complete",
            "Only complete preserved/cleaned controls may enter outcomes",
        )
        readback = read_json(directory / "readback.json")
        rows.append(
            {
                "task": group["task"]["task"],
                "repo": group["task"]["repo"],
                "source_identity": group["task"]["source_identity"],
                "run_id": group["run_id"],
                **{name: readback.get(name, False) for name in FLAGS},
                "eligible_for_this_control_profile": profile_eligible(readback),
                "evidence_sha256": {
                    name: sha(directory / name)
                    for name in (
                        "journal.json",
                        "readback.json",
                        "cleanup-proof.json",
                        "publication.json",
                        "cleanup/publication.json",
                    )
                },
            }
        )
    result = {
        "validation_plan_identity": plan["plan_identity"],
        "tasks": rows,
        "unsupported": plan["unsupported"],
        "eligible_bundle_instances": sum(row["eligible_for_this_control_profile"] for row in rows),
        "new_unique_tasks": "not inferred",
        "dataset_release_authorized": False,
    }
    path = validation.parent / "control-outcomes.json"
    if path.exists():
        require(read_json(path) == result, "Completed native outcome summary changed")
    else:
        write_json(path, result)
    return result
