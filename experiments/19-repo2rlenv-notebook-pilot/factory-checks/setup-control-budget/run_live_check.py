"""Synthetic provider checks for the existing cumulative-budget boundary.

Requires separate funding and admission. No model or biological reference runs.
The exhausted counter is deliberate fault injection, not a natural reproduction.
"""

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "setup_budget_compat_base",
    HERE / "factory-checks/daytona-session-transport/run_live_check.py",
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

from reference_setup import SetupControlBudgetExceeded, SetupSession  # noqa: E402


async def checks(remote, root):
    # No reference fields are used: only mandatory workspace control is exercised.
    session = SetupSession(
        prepared=None,
        remote=remote,
        root=root / "session",
        setup_seconds=1800,
        reference_seconds=600,
        max_tests=2,
    )
    init = await remote.command(["mkdir", "-p", "/work/setup"], 30, "synthetic-authoring-directory")
    assert init["exit_code"] == 0 and not init["timed_out"]

    absent = root / "isolation-refused"
    absent.mkdir()
    session.setup_remaining = 0
    before = remote.operation
    try:
        async with session.isolated_authoring_workspace(absent):
            raise AssertionError("Exhausted isolation must not enter its body")
    except SetupControlBudgetExceeded as error:
        assert error.control == "isolation"
    else:
        raise AssertionError("Mandatory control budget boundary was not terminal")
    assert remote.operation == before and not remote.uncertain
    assert json.loads((absent / "workspace-isolation.json").read_text())["state"] == (
        "isolation_not_dispatched_budget_exhausted"
    )

    normal = root / "normal-controls"
    normal.mkdir()
    session.setup_remaining = 1800
    before = remote.operation
    async with session.isolated_authoring_workspace(normal):
        completed = await session.setup_command(["true"], 30, "synthetic-normal-completion")
        assert completed["exit_code"] == 0 and not completed["timed_out"]
    assert remote.operation == before + 3 and not remote.uncertain
    assert 0 < session.setup_remaining < 1800
    assert json.loads((normal / "workspace-isolation.json").read_text())["state"] == "restored"

    exhausted = root / "restoration-refused"
    exhausted.mkdir()
    before = remote.operation
    try:
        async with session.isolated_authoring_workspace(exhausted):
            completed = await session.setup_command(["true"], 30, "synthetic-last-completion")
            assert completed["exit_code"] == 0 and not completed["timed_out"]
            # Deliberately inject exhaustion after the real verified completion.
            session.setup_remaining = 0
    except SetupControlBudgetExceeded as error:
        assert error.control == "restoration"
    else:
        raise AssertionError("Exhausted restoration must terminate the stage")
    assert remote.operation == before + 2 and not remote.uncertain
    assert session.tests == 0 and session.last_pass is None
    assert json.loads((exhausted / "workspace-isolation.json").read_text())["state"] == (
        "restoration_not_dispatched_budget_exhausted"
    )
    # No more commands: the trusted workspace remains isolated until SDK cleanup.
    return [
        {"name": "isolation-budget-refused-without-dispatch", "passed": True},
        {"name": "normal-controls-restore-within-existing-budget", "passed": True},
        {"name": "known-completion-budget-stop-no-restoration-dispatch", "passed": True},
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(base.run(json.loads(args.config.read_text()), args.root, checks=checks))
        )
    )
