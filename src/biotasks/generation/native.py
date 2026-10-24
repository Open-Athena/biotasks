"""Serial native control lifecycle with explicit unaccepted retention outcomes."""

from pathlib import Path

from biotasks.retention import actor
from biotasks.validation import controller
from biotasks.validation.files import lock


def retention_root(validation: Path) -> Path:
    return validation.with_name(validation.name + "-held-retention")


def retained(validation: Path, task_id: str):
    """One sidecar transition, reusing the original pre-reserved cleanup only."""
    output = retention_root(validation)
    if not output.exists():
        actor.prepare(validation, output)
    value = actor.run(output, publish=True, cleanup=True)
    for row in value.get("results", []):
        if row["task_id"] == task_id and row["state"] == "retention_complete":
            return row
    return {
        "state": "held_unsupported" if value["state"] == "held_unsupported" else "retaining",
        "retention": value,
    }


def advance(validation: Path):
    """A retained failure may finish a case, never provide a reward or clear a hold.

    Unstarted groups remain unstarted until each preceding group is either
    natively complete or fully retained/cleaned with admission still open.
    """
    plan = controller.verify_plan(validation)
    states = {}
    with lock(validation / "native-driver.lock"):
        for group in plan["tasks"]:
            directory = validation / "runs" / group["id"]
            if (directory / "held.json").exists():
                state = "held"
            else:
                state = controller.Pipeline(validation, plan, group).step()
            if state == "held" or state.startswith("held:"):
                value = retained(validation, group["id"])
                states[group["id"]] = value
                if value["state"] != "retention_complete":
                    return {
                        "state": value["state"],
                        "tasks": states,
                        "unsupported": plan["unsupported"],
                    }
                if value["admission_closed"]:
                    return {
                        "state": "held",
                        "reason": "Admission remains closed after retention",
                        "tasks": states,
                        "unsupported": plan["unsupported"],
                    }
                continue
            states[group["id"]] = {"state": state}
            if state != "complete":
                return {"state": "in_progress", "tasks": states, "unsupported": plan["unsupported"]}
            if any(
                (directory / name).exists()
                for name in (
                    "budget-hold.json",
                    "cleanup/budget-hold.json",
                    "stop/budget-hold.json",
                )
            ):
                return {
                    "state": "held",
                    "reason": "CPU hold remains after native cleanup",
                    "tasks": states,
                    "unsupported": plan["unsupported"],
                }
    return {
        "state": "complete" if plan["tasks"] else "unsupported",
        "tasks": states,
        "unsupported": plan["unsupported"],
    }
