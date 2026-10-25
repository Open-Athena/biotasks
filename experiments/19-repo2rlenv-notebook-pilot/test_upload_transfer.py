"""Exercise the real SDK error translation without a network or scientific run."""

import asyncio
import json
import time
from types import SimpleNamespace

import httpx
import pytest
from daytona._sync.filesystem import FileSystem
from daytona.common.errors import DaytonaError
from repo2rlenv.execution.daytona import DaytonaWorker
from run_reference_setup import OperationBudgetExceeded, Remote


class UploadAPI:
    def _upload_files_serialize(self, *args):
        return None, "https://unit.invalid/files", {}, None


class UploadHTTP:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.deliveries = []
        self.files = {}

    def post(self, url, *, data, files, headers, timeout):
        target = data["files[0].path"]
        content = next(iter(files.values()))[1].read()
        self.deliveries.append((target, content))
        # The first response can be lost AFTER the same bytes were written.
        self.files[target] = content
        return httpx.Response(next(self.statuses), json={"errors": ["synthetic"]})


def configured_remote(tmp_path, http, *, deadline=None):
    sandbox = SimpleNamespace(id="synthetic", fs=FileSystem(UploadAPI(), http))
    worker = DaytonaWorker(None, sandbox)
    return Remote(worker, sandbox, tmp_path, deadline or time.time() + 60, 1)


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_502_after_delivery_reuses_frozen_bytes_without_executing_commands(tmp_path, status):
    source = tmp_path / "source.py"
    source.write_bytes(b"print('synthetic input')\n")
    http = UploadHTTP([status, 200])
    remote = configured_remote(tmp_path, http)
    asyncio.run(remote.upload(source, "/work/independent.py"))
    assert http.deliveries == [("/work/independent.py", source.read_bytes())] * 2
    assert http.files["/work/independent.py"] == source.read_bytes()
    assert remote.operation == 0 and not remote.uncertain
    receipt = json.loads((tmp_path / "uploads/0001/upload.json").read_text())
    assert receipt["state"] == "uploaded"
    assert receipt["attempts"][0]["http_status"] == status
    assert len(receipt["attempts"]) == 2
    assert not list((tmp_path / "uploads/0001").glob("snapshot-*"))


def test_client_transport_error_is_not_reclassified_by_message_text(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("synthetic")

    class LostConnection(UploadHTTP):
        def post(self, *args, **kwargs):
            super().post(*args, **kwargs)
            raise httpx.ReadTimeout("502 in message is not a structured HTTP response")

    http = LostConnection([200, 200])
    remote = configured_remote(tmp_path, http)
    with pytest.raises(DaytonaError):
        asyncio.run(remote.upload(source, "/work/input.txt"))
    assert len(http.deliveries) == 1 and remote.uncertain


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_nonregular_source_is_refused_before_upload(tmp_path, kind):
    regular = tmp_path / "regular.txt"
    regular.write_text("synthetic")
    source = tmp_path / "source"
    if kind == "directory":
        source.mkdir()
    else:
        source.symlink_to(regular)
    http = UploadHTTP([200])
    remote = configured_remote(tmp_path, http)
    with pytest.raises(ValueError, match="regular"):
        asyncio.run(remote.upload(source, "/work/input.txt"))
    assert not http.deliveries and not remote.uncertain


@pytest.mark.parametrize("status", [400, 401, 403, 404, 408, 409, 429])
def test_other_http_failures_are_not_blindly_retried(tmp_path, status):
    source = tmp_path / "input.txt"
    source.write_text("synthetic")
    http = UploadHTTP([status, 200])
    remote = configured_remote(tmp_path, http)
    with pytest.raises(DaytonaError) as caught:
        asyncio.run(remote.upload(source, "/work/input.txt"))
    assert caught.value.status_code == status
    assert len(http.deliveries) == 1 and remote.uncertain
    with pytest.raises(RuntimeError, match="uncertain"):
        remote.remaining(1)


def test_source_changes_cannot_change_retry_bytes(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("original")

    class ChangingSource(UploadHTTP):
        def post(self, *args, **kwargs):
            reply = super().post(*args, **kwargs)
            source.write_text("later unrelated mutation")
            return reply

    http = ChangingSource([503, 200])
    remote = configured_remote(tmp_path, http)
    asyncio.run(remote.upload(source, "/work/input.txt"))
    assert http.deliveries == [("/work/input.txt", b"original")] * 2
    assert source.read_text() == "later unrelated mutation"


def test_persistent_server_errors_preserve_all_attempts_and_block_continuation(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("original")
    http = UploadHTTP([502, 503, 504, 200])
    remote = configured_remote(tmp_path, http)
    with pytest.raises(DaytonaError) as caught:
        asyncio.run(remote.upload(source, "/work/input.txt"))
    assert caught.value.status_code == 504 and len(http.deliveries) == 3
    receipt = json.loads((tmp_path / "uploads/0001/upload.json").read_text())
    assert receipt["state"] == "incomplete" and remote.uncertain
    assert [a["http_status"] for a in receipt["attempts"]] == [502, 503, 504]
    assert not list((tmp_path / "uploads/0001").glob("snapshot-*"))


def test_expired_stage_does_not_dispatch_an_upload(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("original")
    http = UploadHTTP([200])
    remote = configured_remote(tmp_path, http, deadline=time.time() + 10)
    with pytest.raises(OperationBudgetExceeded):
        asyncio.run(remote.upload(source, "/work/input.txt"))
    assert not http.deliveries and not remote.uncertain


def test_cancellation_blocks_commands_even_if_upload_finishes_later(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("original")
    import threading

    started, release = threading.Event(), threading.Event()
    http = UploadHTTP([200])

    class Delayed(UploadHTTP):
        def post(self, *args, **kwargs):
            started.set()
            assert release.wait(5)
            return http.post(*args, **kwargs)

    remote = configured_remote(tmp_path, Delayed([]))

    async def run():
        upload = asyncio.create_task(remote.upload(source, "/work/input.txt"))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            upload.cancel()
            with pytest.raises(asyncio.CancelledError):
                await upload
            assert remote.uncertain and remote.operation == 0
        finally:
            release.set()

    asyncio.run(run())
    assert len(http.deliveries) == 1


def test_command_budget_is_rechecked_after_upload_before_dispatch(tmp_path, monkeypatch):
    import run_reference_setup

    clock = [1000.0]
    monkeypatch.setattr(run_reference_setup.time, "time", lambda: clock[0])

    class SlowUpload:
        executions = 0

        def upload(self, *args):
            clock[0] += 10

        def exec(self, *args, **kwargs):
            self.executions += 1
            raise AssertionError("No command has enough remaining time")

    worker = SlowUpload()
    remote = Remote(worker, None, tmp_path, 1035, 1)
    with pytest.raises(OperationBudgetExceeded):
        asyncio.run(remote.command(["synthetic-scientific-work"], 15, "bounded"))
    assert worker.executions == 0 and not remote.uncertain
    record = json.loads((tmp_path / "operations/0001/operation.json").read_text())
    assert record["state"] == "not_dispatched"
