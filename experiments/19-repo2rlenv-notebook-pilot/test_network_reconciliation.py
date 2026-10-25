"""Reconcile idempotent network settings without replaying scientific commands."""

import asyncio
import json
import time

import pytest
import run_reference_setup
from preflight import TARGETS
from run_reference_setup import Remote


class DaytonaConnectionError(ConnectionError):
    pass


class Forbidden(ConnectionError):
    status_code = 403


class Sandbox:
    def __init__(self, blocked, *, updates=(), reads=()):
        self.network_block_all = blocked
        self.updates, self.reads = list(updates), list(reads)
        self.calls = []

    def update_network_settings(self, *, network_block_all, request_timeout):
        self.calls.append(("set", network_block_all, request_timeout))
        effect, error = self.updates.pop(0) if self.updates else (True, None)
        if effect:
            self.network_block_all = network_block_all
        if error:
            raise error

    def refresh_data(self, *, request_timeout):
        self.calls.append(("read", request_timeout))
        if self.reads:
            error = self.reads.pop(0)
            if error:
                raise error


class ProbedRemote(Remote):
    def __init__(self, sandbox, root, *, bad_probe=False):
        super().__init__(None, sandbox, root, time.time() + 120, 1)
        self.probe_commands = []
        self.bad_probe = bad_probe

    async def command(self, argv, seconds, label, *, cwd="/work"):
        self.remaining(seconds)
        self.probe_commands.append(argv)
        return {
            "exit_code": 0,
            "log": json.dumps(
                [
                    {
                        "host": h,
                        "port": p,
                        "reachable": self.bad_probe == self.sandbox.network_block_all,
                    }
                    for h, p in TARGETS
                ]
            ),
        }


def receipt(root):
    paths = list((root / "network").glob("control-*.json"))
    assert len(paths) == 1
    return json.loads(paths[0].read_text())


@pytest.fixture
def control_clock(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(run_reference_setup.time, "time", lambda: clock[0])

    async def pause(seconds):
        assert seconds > 0
        clock[0] += seconds

    monkeypatch.setattr(run_reference_setup.asyncio, "sleep", pause)
    return clock


@pytest.mark.parametrize("blocked", [True, False])
@pytest.mark.parametrize("applied", [True, False])
def test_lost_update_is_read_back_before_one_possible_repeat(tmp_path, blocked, applied):
    sandbox = Sandbox(not blocked, updates=[(applied, DaytonaConnectionError())])
    remote = ProbedRemote(sandbox, tmp_path)
    original_deadline = remote.deadline
    asyncio.run(remote.network(blocked))
    kinds = [call[0] for call in sandbox.calls]
    assert kinds == (["set", "read"] if applied else ["set", "read", "set", "read"])
    assert sandbox.network_block_all is blocked
    assert len(remote.probe_commands) == 1
    assert remote.probe_commands[0][:2] == ["python", "-c"]
    assert not remote.uncertain and remote.deadline == original_deadline
    evidence = receipt(tmp_path)
    assert evidence["state"] == "verified"
    assert evidence["events"][0]["error_type"] == "DaytonaConnectionError"
    assert evidence["probes"]


def test_second_lost_response_can_be_confirmed_without_a_third_update(tmp_path):
    sandbox = Sandbox(
        False, updates=[(False, DaytonaConnectionError()), (True, DaytonaConnectionError())]
    )
    remote = ProbedRemote(sandbox, tmp_path)
    asyncio.run(remote.network(True))
    assert [call[0] for call in sandbox.calls] == ["set", "read", "set", "read"]
    assert receipt(tmp_path)["state"] == "verified"


@pytest.mark.parametrize("defect", ["permission", "mismatch", "lost_twice", "unreadable"])
def test_unconfirmed_policy_blocks_all_further_execution(tmp_path, defect):
    cases = {
        "permission": {"updates": [(False, Forbidden())]},
        "mismatch": {"updates": [(False, None)]},
        "lost_twice": {"updates": [(False, DaytonaConnectionError())] * 2},
        "unreadable": {
            "updates": [(True, DaytonaConnectionError())],
            "reads": [DaytonaConnectionError()] * 2,
        },
    }
    sandbox = Sandbox(False, **cases[defect])
    remote = ProbedRemote(sandbox, tmp_path)
    with pytest.raises((ConnectionError, RuntimeError)):
        asyncio.run(remote.network(True))
    assert not remote.probe_commands
    with pytest.raises(RuntimeError, match="uncertain"):
        remote.remaining(1)
    assert receipt(tmp_path)["state"] == "uncertain"
    if defect in {"permission", "mismatch"}:
        assert sum(call[0] == "set" for call in sandbox.calls) == 1


def test_read_loss_is_bounded_and_does_not_repeat_a_confirmed_update(tmp_path):
    sandbox = Sandbox(False, reads=[DaytonaConnectionError(), None])
    remote = ProbedRemote(sandbox, tmp_path)
    asyncio.run(remote.network(True))
    assert [call[0] for call in sandbox.calls] == ["set", "read", "read"]
    assert receipt(tmp_path)["state"] == "verified"


def test_unknown_readback_is_not_treated_as_a_confirmed_mismatch(tmp_path):
    class UnknownSandbox(Sandbox):
        def refresh_data(self, **kwargs):
            super().refresh_data(**kwargs)
            self.network_block_all = None

    sandbox = UnknownSandbox(False, updates=[(False, DaytonaConnectionError())])
    remote = ProbedRemote(sandbox, tmp_path)
    with pytest.raises(RuntimeError, match="boolean network policy"):
        asyncio.run(remote.network(True))
    assert [call[0] for call in sandbox.calls] == ["set", "read"]
    assert not remote.probe_commands and remote.uncertain


def test_provider_readback_never_substitutes_for_actual_probes(tmp_path, control_clock):
    remote = ProbedRemote(Sandbox(False), tmp_path, bad_probe=True)
    with pytest.raises(TimeoutError, match="original allowance"):
        asyncio.run(remote.network(True))
    assert len(remote.probe_commands) > 1 and remote.uncertain
    assert control_clock[0] <= 1045
    assert receipt(tmp_path)["state"] == "uncertain"


@pytest.mark.parametrize("blocked", [True, False])
def test_completed_probes_may_converge_within_original_allowance(tmp_path, control_clock, blocked):
    class ConvergingRemote(ProbedRemote):
        async def command(self, *args, **kwargs):
            self.bad_probe = len(self.probe_commands) < 2
            control_clock[0] += 0.25
            return await super().command(*args, **kwargs)

    sandbox = Sandbox(not blocked)
    remote = ConvergingRemote(sandbox, tmp_path)
    original_deadline = remote.deadline
    asyncio.run(remote.network(blocked))
    evidence = receipt(tmp_path)
    assert evidence["state"] == "verified" and not remote.uncertain
    assert [row["operation"] for row in evidence["events"]] == [
        "update_network_settings",
        "refresh_data",
    ]
    assert len(evidence["probe_attempts"]) == len(remote.probe_commands) == 3
    assert evidence["probe_attempts"][0]["probes"] != evidence["probes"]
    assert evidence["probe_attempts"][-1]["probes"] == evidence["probes"]
    assert evidence["control_deadline"] == 1045 > evidence["finished"]
    assert remote.deadline == original_deadline


def test_success_returned_after_control_deadline_is_not_accepted(tmp_path, control_clock):
    class LateRemote(ProbedRemote):
        async def command(self, *args, **kwargs):
            result = await super().command(*args, **kwargs)
            control_clock[0] += 46
            return result

    remote = LateRemote(Sandbox(False), tmp_path)
    with pytest.raises(TimeoutError, match="original allowance"):
        asyncio.run(remote.network(True))
    assert remote.uncertain and len(remote.probe_commands) == 1
    assert receipt(tmp_path)["state"] == "uncertain"


@pytest.mark.parametrize("defect", ["missing_target", "non_boolean", "unknown_target"])
def test_malformed_completed_probe_is_not_a_convergence_retry(tmp_path, control_clock, defect):
    class MalformedRemote(ProbedRemote):
        async def command(self, *args, **kwargs):
            result = await super().command(*args, **kwargs)
            rows = json.loads(result["log"])
            if defect == "missing_target":
                rows.pop()
            elif defect == "non_boolean":
                rows[0]["reachable"] = 0
            else:
                rows[0]["host"] = "unrequested.invalid"
            result["log"] = json.dumps(rows)
            return result

    remote = MalformedRemote(Sandbox(False), tmp_path)
    with pytest.raises(RuntimeError, match="Network probe"):
        asyncio.run(remote.network(True))
    assert remote.uncertain and len(remote.probe_commands) == 1
    assert receipt(tmp_path)["state"] == "uncertain"


def test_cancelled_convergence_wait_keeps_execution_blocked(tmp_path, control_clock, monkeypatch):
    async def cancel(seconds):
        raise asyncio.CancelledError()

    monkeypatch.setattr(run_reference_setup.asyncio, "sleep", cancel)
    remote = ProbedRemote(Sandbox(False), tmp_path, bad_probe=True)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(remote.network(True))
    assert remote.uncertain and len(remote.probe_commands) == 1
    assert receipt(tmp_path)["error_type"] == "CancelledError"


def test_recovery_cannot_extend_original_control_or_campaign_deadline(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(run_reference_setup.time, "time", lambda: clock[0])

    class SlowSandbox(Sandbox):
        def update_network_settings(self, **kwargs):
            super().update_network_settings(**kwargs)
            clock[0] += 45
            raise DaytonaConnectionError()

    sandbox = SlowSandbox(False)
    remote = ProbedRemote(sandbox, tmp_path)
    original_deadline = remote.deadline
    with pytest.raises(TimeoutError, match="original allowance"):
        asyncio.run(remote.network(True))
    assert [call[0] for call in sandbox.calls] == ["set"]
    assert not remote.probe_commands and remote.uncertain
    evidence = receipt(tmp_path)
    assert evidence["control_deadline"] == 1045
    assert remote.deadline == original_deadline


@pytest.mark.parametrize(
    "result",
    [
        {"exit_code": -15, "timed_out": True, "log": ""},
        {"exit_code": 1, "log": ""},
        {"exit_code": 0, "log": "not JSON"},
        {"exit_code": 0, "log": None},
    ],
)
def test_incomplete_probe_is_preserved_and_never_json_success(tmp_path, result):
    class IncompleteRemote(ProbedRemote):
        async def command(self, *args, **kwargs):
            self.probe_commands.append(args)
            return result

    remote = IncompleteRemote(Sandbox(False), tmp_path)
    with pytest.raises(RuntimeError, match="Network probe"):
        asyncio.run(remote.network(True))
    evidence = receipt(tmp_path)
    assert evidence["state"] == "uncertain" and remote.uncertain
    assert evidence["probe_exit_code"] == result["exit_code"]
    assert evidence["probe_timed_out"] == result.get("timed_out", False)
    assert len(remote.probe_commands) == 1
    with pytest.raises(RuntimeError, match="uncertain"):
        remote.remaining(1)
