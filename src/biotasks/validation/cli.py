"""Explicit planning, execution and read-only status commands."""

import json
from pathlib import Path

from cyclopts import App

from biotasks.validation import budget, controller, planning

app = App(
    name="validate", help="Validate existing native-inline PR task exports on reserved Iris CPUs."
)


@app.command
def plan(manifest: Path, *, work_dir: Path) -> None:
    """Freeze exports and execution policy. Does not submit jobs or call models."""
    value = planning.prepare(manifest, work_dir)
    print(
        json.dumps(
            {
                "plan_identity": value["plan_identity"],
                "tasks": len(value["tasks"]),
                "unsupported": value["unsupported"],
                "work_dir": str(work_dir.absolute()),
            },
            indent=2,
        )
    )


@app.command
def run(work_dir: Path, *, once: bool = False) -> None:
    """Resume validation and cleanup. Default watch interval is five minutes.

    --once advances one journal transition and returns for external scheduling.
    """
    value = controller.run(work_dir, once)
    print(json.dumps(value, indent=2))
    if value["state"] in ("held", "unsupported"):
        raise SystemExit(2)


@app.command
def status(work_dir: Path) -> None:
    """Inspect immutable plans and local journal evidence without remote queries."""
    print(json.dumps(controller.status(work_dir), indent=2))


@app.command(name="init-budget")
def init_budget(path: Path, *, cpu_hours: float) -> None:
    """Create a CPU ledger; this does not authorize capacity or model spending."""
    budget.create(path, cpu_hours)
    print(str(path.absolute()))
