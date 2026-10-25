"""Session observation is bounded and never causes a second command submission."""

import asyncio
import inspect
import json
import shlex
import time
from types import SimpleNamespace

import pytest
from daytona._async.process import AsyncProcess
from daytona.common.errors import DaytonaNotFoundError
from daytona_session import session_command
from daytona_toolbox_api_client_async.models.command import Command
from repo2rlenv.execution.base import RemoteCommandError
from run_reference_setup import Remote
from test_command_receipt_recovery import Worker


class Process:
    def __init__(self, *, fast=False, stream_loss=False, pending=False, fail=None):
        self.fast, self.stream_loss, self.pending, self.fail = fast, stream_loss, pending, fail
        self.events, self.submissions, self.streams = [], [], 0
        self.exit_code = 0
        self.logs = SimpleNamespace(stdout="receipt\n", stderr="", output="receipt\n")

    async def create_session(self, session, **kwargs):
        self.events.append("create")
        if self.fail == "create":
            raise ConnectionError("create response lost")

    async def execute_session_command(self, session, req, **kwargs):
        self.events.append("submit")
        self.submissions.append(req)
        assert req.run_async and req.suppress_input_echo
        assert 0 < kwargs["timeout"] <= 30
        if self.fail == "submit":
            raise ConnectionError("submit response lost")
        return SimpleNamespace(cmd_id="one-original-command")

    async def get_session_command(self, session, command, **kwargs):
        assert command == "one-original-command"
        self.events.append("status")
        return Command(
            id=command,
            command=self.submissions[0].command,
            exit_code=self.exit_code if self.fast or (self.streams and not self.pending) else None,
        )

    async def get_session_command_logs_async(self, session, command, stdout, stderr):
        self.events.append("stream")
        self.streams += 1
        await stdout("partial observation\n")
        if self.fail == "cancel":
            raise asyncio.CancelledError
        if self.fail == "hang":
            await asyncio.sleep(60)
        if self.stream_loss:
            raise ConnectionError("stream disconnected")

    async def get_session_command_logs(self, session, command, **kwargs):
        self.events.append("logs")
        return self.logs

    async def delete_session(self, session, **kwargs):
        self.events.append("delete")
        if self.fail == "delete":
            raise ConnectionError("cleanup response lost")


class CreationLoss(Process):
    def __init__(
        self,
        *,
        absence=False,
        repeated_loss=False,
        lookup_failure=False,
        wrong_identity=False,
        existing_commands=False,
    ):
        super().__init__(fast=True)
        self.creations, self.lookups = 0, 0
        self.absence, self.repeated_loss = absence, repeated_loss
        self.lookup_failure, self.wrong_identity = lookup_failure, wrong_identity
        self.existing_commands = existing_commands

    async def create_session(self, session, **kwargs):
        self.creations += 1
        self.events.append("create")
        if self.creations == 1 or self.repeated_loss:
            raise ConnectionError("creation acknowledgement lost")

    async def get_session(self, session, **kwargs):
        self.lookups += 1
        self.events.append("lookup")
        assert 0 < kwargs["request_timeout"] <= 30
        if self.lookup_failure:
            raise ConnectionError("lookup outcome unknown")
        if self.absence:
            raise DaytonaNotFoundError("No session")
        return SimpleNamespace(
            session_id="different" if self.wrong_identity else session,
            commands=["unexpected command"] if self.existing_commands else [],
        )


@pytest.mark.parametrize("absence", [False, True])
def test_creation_loss_is_reconciled_before_the_only_command_submission(tmp_path, absence):
    process = CreationLoss(absence=absence)
    result = asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert result.returncode == 0
    assert process.creations == (2 if absence else 1) and process.lookups == 1
    assert len(process.submissions) == 1
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert receipt["submission_attempts"] == 1 and not receipt["command_reexecuted"]
    assert receipt["creation_recovery"] == (
        "created_after_confirmed_absence" if absence else "existing_empty_session"
    )
    assert receipt["creation_reconciliation"][0]["state"] == (
        "confirmed_absent" if absence else "same_empty_session_verified"
    )


@pytest.mark.parametrize(
    "mode", ["lookup_failure", "wrong_identity", "existing_commands", "repeated_loss"]
)
def test_unresolved_creation_or_nonempty_session_never_dispatches_a_command(tmp_path, mode):
    kwargs = {mode: True}
    if mode == "repeated_loss":
        kwargs["absence"] = True
    process = CreationLoss(**kwargs)
    with pytest.raises(
        ConnectionError if mode in {"lookup_failure", "repeated_loss"} else ValueError
    ):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert process.creations == (2 if mode == "repeated_loss" else 1)
    assert process.submissions == [] and "delete" not in process.events
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert receipt["submission_attempts"] == 0 and receipt["session_cleanup"] == "owner_required"


def test_recovered_creation_does_not_retry_a_lost_execute_response(tmp_path):
    process = CreationLoss()
    process.fail = "submit"
    with pytest.raises(ConnectionError, match="submit response lost"):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert process.creations == 1 and process.lookups == 1
    assert len(process.submissions) == 1


def test_creation_recovery_keeps_the_original_deadline(tmp_path, monkeypatch):
    import daytona_session

    clock = [0]
    monkeypatch.setattr(
        daytona_session,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock[0],
            time=time.time,
        ),
    )

    class ExpiredCreation(CreationLoss):
        async def get_session(self, session, **kwargs):
            result = await super().get_session(session, **kwargs)
            clock[0] = 11
            return result

    process = ExpiredCreation()
    with pytest.raises(TimeoutError, match="original allowance"):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert process.creations == 1 and process.lookups == 1 and not process.submissions


@pytest.mark.parametrize("fast", [False, True])
def test_single_submission_preserves_quoting_and_uses_real_completion_status(tmp_path, fast):
    process = Process(fast=fast)
    argv = ["python", "-c", "print('$(MUST_NOT_RUN) `nor this`')", "with spaces"]
    result = asyncio.run(session_command(process, argv, timeout=10, directory=tmp_path))
    assert shlex.split(process.submissions[0].command) == argv
    assert result.returncode == 0 and result.stdout == "receipt\n"
    assert len(process.submissions) == 1 and process.streams == (0 if fast else 1)
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert receipt["state"] == "completed" and receipt["session_cleanup"] == "deleted"
    assert not receipt["command_reexecuted"]
    assert not any("MUST_NOT_RUN" in p.name for p in tmp_path.iterdir())


def test_lost_stream_can_be_reconciled_by_the_same_command_status(tmp_path):
    process = Process(stream_loss=True)
    result = asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert result.returncode == 0 and len(process.submissions) == 1
    assert process.events == ["create", "submit", "status", "stream", "status", "logs", "delete"]
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert receipt["stream_error_type"] == "ConnectionError"
    assert (tmp_path / "session-stream-stdout.txt").read_text() == "partial observation\n"


def test_pinned_async_sdk_is_recognized_and_sync_sdk_is_refused_before_mutation(tmp_path):
    assert inspect.iscoroutinefunction(AsyncProcess.create_session)

    class SyncProcess:
        def create_session(self, *args, **kwargs):
            raise AssertionError("Must not invoke the synchronous transport")

    with pytest.raises(TypeError, match="asynchronous Daytona SDK"):
        asyncio.run(session_command(SyncProcess(), ["original"], timeout=10, directory=tmp_path))
    assert not (tmp_path / "session-transport.json").exists()


def test_other_command_status_cannot_close_or_accept_this_session(tmp_path):
    class WrongIdentity(Process):
        async def get_session_command(self, *args, **kwargs):
            return Command(id="another-command", command="another science", exit_code=0)

    process = WrongIdentity(fast=True)
    with pytest.raises(ValueError, match="command identity"):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert len(process.submissions) == 1 and "delete" not in process.events


@pytest.mark.parametrize("stream_loss", [False, True])
def test_stream_end_is_not_proof_of_execution_completion(tmp_path, stream_loss):
    process = Process(stream_loss=stream_loss, pending=True)
    with pytest.raises(ConnectionError if stream_loss else RuntimeError):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert len(process.submissions) == 1 and "delete" not in process.events
    assert "logs" not in process.events
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert (
        receipt["state"] == "observation_failed" and receipt["session_cleanup"] == "owner_required"
    )


@pytest.mark.parametrize("failure", ["create", "submit"])
def test_lost_mutating_response_is_never_retried(tmp_path, failure):
    process = Process(fail=failure)
    with pytest.raises(ConnectionError):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert len(process.submissions) == (0 if failure == "create" else 1)
    assert "delete" not in process.events


def test_cancelled_stream_retains_uncertainty_and_partial_output(tmp_path):
    process = Process(fail="cancel")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert len(process.submissions) == 1 and "delete" not in process.events
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert (
        receipt["error_type"] == "CancelledError" and receipt["session_cleanup"] == "owner_required"
    )


def test_deadline_cancels_observation_without_another_submission(tmp_path):
    process = Process(fail="hang", pending=True)
    with pytest.raises(TimeoutError):
        asyncio.run(session_command(process, ["original"], timeout=7, directory=tmp_path))
    assert len(process.submissions) == 1 and "delete" not in process.events
    assert (
        json.loads((tmp_path / "session-transport.json").read_text())["state"]
        == "observation_failed"
    )


def test_nonzero_wrapper_and_cleanup_failure_do_not_hide_original_result(tmp_path):
    process = Process(fail="delete")
    process.exit_code = 7
    process.logs = SimpleNamespace(stdout="original stdout", stderr="original stderr", output="")
    result = asyncio.run(session_command(process, ["original"], timeout=10, directory=tmp_path))
    assert result.returncode == 7 and result.stderr == "original stderr"
    receipt = json.loads((tmp_path / "session-transport.json").read_text())
    assert receipt["exit_code"] == 7 and receipt["session_cleanup_error_type"] == "ConnectionError"


@pytest.mark.parametrize("loss", [False, True])
def test_remote_still_verifies_original_nonce_and_log_without_sync_fallback(tmp_path, loss):
    worker = Worker()
    provider_execute = worker.exec

    def no_sync(*args, **kwargs):
        raise AssertionError("Synchronous fallback would risk duplicate execution")

    worker.exec = no_sync

    class ReceiptProcess(Process):
        async def execute_session_command(self, session, req, **kwargs):
            result = provider_execute(shlex.split(req.command), timeout=10)
            self.logs = SimpleNamespace(stdout=result.stdout, stderr=result.stderr, output="")
            response = await super().execute_session_command(session, req, **kwargs)
            if loss:
                raise ConnectionError("Original command submitted; acknowledgement lost")
            return response

    process = ReceiptProcess(fast=True)
    remote = Remote(worker, None, tmp_path, time.time() + 120, 1, session_process=process)
    result = asyncio.run(remote.command(["synthetic-operation"], 10, "same-human-label"))
    assert result["exit_code"] == 0 and worker.executions == 1
    assert len(process.submissions) == 1 and not remote.uncertain
    record = json.loads((tmp_path / "operations/0001/operation.json").read_text())
    assert record["state"] == "returned"
    if loss:
        assert record["transport_recovery"]["completion_receipt_verified"]
        assert not record["transport_recovery"]["command_reexecuted"]


def test_session_wrapper_failure_keeps_private_output_and_closes_remote(tmp_path):
    process = Process(fast=True)
    process.exit_code = 7
    process.logs = SimpleNamespace(
        stdout="private original output", stderr="private error", output=""
    )
    remote = Remote(Worker(), None, tmp_path, time.time() + 120, 1, session_process=process)
    with pytest.raises(RemoteCommandError) as error:
        asyncio.run(remote.command(["synthetic-operation"], 10, "controller-failure"))
    assert "private" not in str(error.value)
    result = json.loads((tmp_path / "operations/0001/controller-result.json").read_text())
    assert result == {
        "returncode": 7,
        "stdout": "private original output",
        "stderr": "private error",
    }
    assert remote.uncertain and len(process.submissions) == 1
    with pytest.raises(RuntimeError, match="uncertain"):
        asyncio.run(remote.command(["do-not-run"], 10, "next"))
    assert len(process.submissions) == 1
