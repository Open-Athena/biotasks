"""Inject delayed creation visibility; observe the provider's actual retry conflict.

No model or biology runs. Reuse the existing bounded three-case infrastructure
runner and its resource, deadline, ownership and cleanup checks.
"""

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path

from daytona.common.errors import DaytonaConflictError, DaytonaProcessNotFoundError

BASE = Path(__file__).resolve().parents[1] / "session-create-recovery/run_live_check.py"
spec = importlib.util.spec_from_file_location("creation_check_base", BASE)
creation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creation)


class LateVisibility(creation.CreationLoss):
    def __init__(self, process):
        super().__init__(process, after_creation=True)
        self.lookups = 0
        self.actual_retry_conflict = False

    async def create_session(self, session, **kwargs):
        try:
            return await super().create_session(session, **kwargs)
        except DaytonaConflictError:
            self.actual_retry_conflict = True
            raise

    async def get_session(self, session, **kwargs):
        self.lookups += 1
        if self.lookups == 1:
            raise DaytonaProcessNotFoundError("Injected single stale absence observation")
        return await self.process.get_session(session, **kwargs)


async def checks(remote, root):
    original = remote.session_process
    results = []
    for name, process in [
        ("existing-empty", creation.CreationLoss(original, after_creation=True)),
        ("confirmed-absent", creation.CreationLoss(original, after_creation=False)),
        ("late-visible-conflict", LateVisibility(original)),
    ]:
        remote.session_process = process
        observed = await remote.command(["python", "-c", creation.base.program(name, 0)], 30, name)
        assert observed["exit_code"] == 0 and not observed["timed_out"]
        assert json.loads(observed["log"]) == {"case": name, "synthetic": True}
        count = root / (name + "-execution-count.txt")
        await remote.download("/work/probe-counts/" + name + ".txt", count)
        assert count.read_text().splitlines() == ["ran"]
        directory = root / "operations" / f"{remote.operation:04d}"
        operation = json.loads((directory / "operation.json").read_text())
        session = json.loads((directory / "session-transport.json").read_text())
        assert operation["state"] == "returned" and not remote.uncertain
        assert session["submission_attempts"] == 1 and not session["command_reexecuted"]
        recovery = (
            "created_after_confirmed_absence"
            if name == "confirmed-absent"
            else "existing_empty_session"
        )
        assert session["creation_recovery"] == recovery
        if name == "late-visible-conflict":
            assert process.actual_retry_conflict and process.creations == process.lookups == 2
            assert session["creation_reconciliation"][1]["error_type"] == "DaytonaConflictError"
        results.append(
            {
                "name": name,
                "passed": True,
                "observed_executions": 1,
                "command_submission_attempts": 1,
                "creation_attempts": session["creation_attempts"],
                "recovery": recovery,
                "original_nonce_and_log_hash_verified": True,
                "actual_provider_conflict": name == "late-visible-conflict",
                "injected_faults": "creation acknowledgement loss; one stale404 in late-visibility case",
            }
        )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    value = asyncio.run(
        creation.base.run(json.loads(args.config.read_text()), args.root, checks=checks)
    )
    print(json.dumps(value))
