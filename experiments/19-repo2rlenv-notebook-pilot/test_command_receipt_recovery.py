"""Lost command responses may be reconciled, never blindly executed again."""

import asyncio
import hashlib
import json
import time

import pytest
from repo2rlenv.execution.base import CommandResult
from run_reference_setup import Remote


class DaytonaConnectionError(ConnectionError):
    pass


class Worker:
    def __init__(self, *, loss=False, missing=False, mismatched=False, corrupt=False):
        self.loss = loss
        self.missing = missing
        self.mismatched = mismatched
        self.corrupt = corrupt
        self.executions = 0
        self.files = {}

    def upload(self, *args):
        pass

    def exec(self, command, *, timeout):
        self.executions += 1
        offset = command.index("execute")
        argv = json.loads(command[offset + 1])
        seconds, cwd, nonce = command[offset + 2 : offset + 5]
        log = b"one completed synthetic operation\n"
        receipt = {
            "argv": ["another-operation"] if self.mismatched else argv,
            "directory": cwd,
            "label": nonce,
            "timeout_seconds": int(seconds),
            "exit_code": 0,
            "timed_out": False,
            "log_sha256": hashlib.sha256(log).hexdigest(),
        }
        if not self.missing:
            self.files["/work/logs/" + nonce + ".json"] = json.dumps(receipt).encode()
            self.files["/work/logs/" + nonce + ".log"] = b"corrupt" if self.corrupt else log
        if self.loss:
            raise DaytonaConnectionError("synthetic lost completion response")
        return CommandResult(0, json.dumps(receipt))

    def download(self, remote, local):
        if remote not in self.files:
            raise FileNotFoundError(remote)
        local.write_bytes(self.files[remote])


@pytest.mark.parametrize("loss", [False, True])
def test_completed_command_is_verified_without_reexecution(tmp_path, loss):
    worker = Worker(loss=loss)
    remote = Remote(worker, None, tmp_path, time.time() + 60, 1)
    output = asyncio.run(remote.command(["synthetic-mutation"], 10, "same-human-label"))
    assert output["exit_code"] == 0
    assert output["log"] == "one completed synthetic operation\n"
    assert worker.executions == 1
    assert not remote.uncertain
    record = json.loads((tmp_path / "operations/0001/operation.json").read_text())
    assert record["state"] == "returned"
    assert ("transport_recovery" in record) is loss
    if loss:
        assert record["transport_recovery"]["command_reexecuted"] is False


@pytest.mark.parametrize("defect", ["missing", "mismatched", "corrupt"])
def test_unverifiable_completion_stays_uncertain_and_blocks_more_work(tmp_path, defect):
    worker = Worker(loss=True, **{defect: True})
    remote = Remote(worker, None, tmp_path, time.time() + 60, 1)
    with pytest.raises(DaytonaConnectionError):
        asyncio.run(remote.command(["synthetic-mutation"], 10, "same-human-label"))
    with pytest.raises(RuntimeError, match="uncertain"):
        asyncio.run(remote.command(["synthetic-mutation"], 10, "another-label"))
    assert worker.executions == 1
    record = json.loads((tmp_path / "operations/0001/operation.json").read_text())
    assert record["state"] == "uncertain"
    assert record["error_type"] == "DaytonaConnectionError"
    assert "recovery_error_type" in record


def test_repeated_human_labels_receive_distinct_completion_nonces(tmp_path):
    worker = Worker()
    remote = Remote(worker, None, tmp_path, time.time() + 60, 1)
    asyncio.run(remote.command(["synthetic-mutation"], 10, "human-label"))
    asyncio.run(remote.command(["synthetic-mutation"], 10, "human-label"))
    records = [
        json.loads((tmp_path / f"operations/{number:04d}/operation.json").read_text())
        for number in (1, 2)
    ]
    assert records[0]["remote_label"] != records[1]["remote_label"]
    assert worker.executions == 2
