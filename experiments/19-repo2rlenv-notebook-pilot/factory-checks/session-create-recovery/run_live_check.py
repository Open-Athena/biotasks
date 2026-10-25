"""Explicit synthetic compatibility check; no model or biological computation."""

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "daytona-session-transport/run_live_check.py"
spec = importlib.util.spec_from_file_location("session_check_base", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class CreationLoss:
    def __init__(self, process, *, after_creation):
        self.process, self.after_creation = process, after_creation
        self.creations = 0

    def __getattr__(self, name):
        return getattr(self.process, name)

    async def create_session(self, session, **kwargs):
        self.creations += 1
        if self.creations == 1:
            if self.after_creation:
                await self.process.create_session(session, **kwargs)
            raise ConnectionError("Synthetic pre-submission creation response loss")
        return await self.process.create_session(session, **kwargs)


async def checks(remote, root):
    original = remote.session_process
    results = []
    for name, after_creation in [
        ("existing-empty", True),
        ("confirmed-absent", False),
        ("lost-execute-ack", None),
    ]:
        if after_creation is None:
            process = base.LoseAcknowledgement(
                original, root / "injected-execute-loss.json", remote.deadline
            )
        else:
            process = CreationLoss(original, after_creation=after_creation)
        remote.session_process = process
        observed = await remote.command(["python", "-c", base.program(name, 0)], 20, name)
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
        if after_creation is None:
            assert operation["transport_recovery"]["completion_receipt_verified"]
            recovery = "original_command_receipt_reconciled_without_resubmission"
        else:
            recovery = (
                "existing_empty_session" if after_creation else "created_after_confirmed_absence"
            )
            assert session["creation_recovery"] == recovery
            assert process.creations == (1 if after_creation else 2)
        results.append(
            {
                "name": name,
                "passed": True,
                "observed_executions": 1,
                "command_submission_attempts": 1,
                "creation_attempts": session["creation_attempts"],
                "recovery": recovery,
                "original_nonce_and_log_hash_verified": True,
            }
        )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    value = asyncio.run(base.run(json.loads(args.config.read_text()), args.root, checks=checks))
    print(json.dumps(value))
