"""Source-bound held evidence retention, independent of scientific acceptance."""

import json
import time
from pathlib import Path

from cyclopts import App

from biotasks.retention import actor
from biotasks.validation.files import read_json

app = App(name="retain", help=__doc__)


@app.command
def plan(original: Path, *, work_dir: Path, prefix: str | None = None) -> None:
    """Freeze an original validation plan and separate retention directory offline."""
    print(json.dumps(actor.prepare(original.resolve(), work_dir.resolve(), prefix), indent=2))


@app.command
def status(work_dir: Path) -> None:
    """Verify source/code bindings and read sidecar journals without transport."""
    work_dir = work_dir.resolve()
    value, _ = actor.verify(work_dir)
    print(
        json.dumps(
            {
                "plan_identity": value["plan_identity"],
                "cases": {
                    task: read_json(work_dir / "cases" / task / "journal.json")
                    if (work_dir / "cases" / task / "journal.json").exists()
                    else None
                    for task in value["task_ids"]
                },
            },
            indent=2,
        )
    )


@app.command
def run(
    work_dir: Path,
    *,
    once: bool = False,
    allow_publication: bool = False,
    allow_cleanup: bool = False,
) -> None:
    """Advance retention; flags preserve original eligibility, worker and ledger gates."""
    while True:
        value = actor.run(work_dir.resolve(), publish=allow_publication, cleanup=allow_cleanup)
        state = value["state"]
        if (
            once
            or state in {"retention_complete", "held_unsupported", "nothing_to_retain"}
            or "not admitted" in state
        ):
            print(json.dumps(value, indent=2))
            if state == "held_unsupported":
                raise SystemExit(2)
            return
        if state.startswith(("recovering:cleanup_terminal", "performed:cleanup_terminal")):
            if not (work_dir / "cases" / value["task_id"] / "cleanup_terminal.json").exists():
                time.sleep(300)
