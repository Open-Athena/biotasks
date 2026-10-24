"""Lost command responses may be reconciled, never blindly executed again."""

import asyncio
import hashlib
import json
import time

import pytest
import run_reference_setup
from repo2rlenv.execution.base import CommandResult, RemoteCommandError
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


def test_failed_controller_response_is_preserved_privately_without_retry(tmp_path):
    class FailedWrapper(Worker):
        def exec(self, command, *, timeout):
            self.executions += 1
            return CommandResult(1, "partial private response\n", "private wrapper traceback\n")

    worker = FailedWrapper()
    remote = Remote(worker, None, tmp_path, time.time() + 60, 1)
    with pytest.raises(RemoteCommandError) as captured:
        asyncio.run(remote.command(["synthetic-operation"], 10, "failed-wrapper"))
    assert "private" not in str(captured.value)
    assert captured.value.result.stderr == "private wrapper traceback\n"
    directory = tmp_path / "operations/0001"
    evidence = json.loads((directory / "controller-result.json").read_text())
    assert evidence == {
        "returncode": 1,
        "stdout": "partial private response\n",
        "stderr": "private wrapper traceback\n",
    }
    record = json.loads((directory / "operation.json").read_text())
    assert record["error_type"] == "RemoteCommandError"
    assert record["controller_failure"] == {
        "returncode": 1,
        "result_path": "controller-result.json",
    }
    assert record["state"] == "uncertain" and remote.uncertain
    assert not (directory / "output.log").exists()
    with pytest.raises(RuntimeError, match="uncertain"):
        asyncio.run(remote.command(["synthetic-operation"], 10, "do-not-repeat"))
    assert worker.executions == 1


@pytest.mark.parametrize("case,deadline", [("on_time", 1300), ("late", 1300), ("campaign", 1045)])
def test_sdk_http_timeout_leaves_only_bounded_receipt_reconciliation(
    tmp_path, monkeypatch, case, deadline
):
    clock = [1000.0]
    monkeypatch.setattr(run_reference_setup.time, "time", lambda: clock[0])

    class SlowLoss(Worker):
        def exec(self, command, *, timeout):
            # The completion receipt exists, but the SDK loses its response at
            # the normal HTTP timeout (server wait+5), after the old window.
            super().exec(command, timeout=timeout)
            clock[0] += timeout + (35 if case == "late" else 5)
            raise DaytonaConnectionError("synthetic lost SDK timeout response")

    worker = SlowLoss()
    remote = Remote(worker, None, tmp_path, deadline, 1)
    if case != "on_time":
        with pytest.raises(DaytonaConnectionError):
            asyncio.run(remote.command(["synthetic-mutation"], 10, "delayed-response"))
        assert remote.uncertain
    else:
        result = asyncio.run(remote.command(["synthetic-mutation"], 10, "delayed-response"))
        assert result["exit_code"] == 0 and not remote.uncertain
    assert worker.executions == 1 and remote.deadline == deadline
    record = json.loads((tmp_path / "operations/0001/operation.json").read_text())
    assert record["reconciliation_deadline"] == min(1065, deadline - 15)
    assert ("transport_recovery" in record) is (case == "on_time")
