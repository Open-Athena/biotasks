import asyncio
import base64
import json
import shlex
import time
from types import SimpleNamespace

import pytest

from biotasks.sandbox_tools import SandboxTools


def test_file_paths_are_data_not_host_shell_commands():
    received = []

    async def execute(**kwargs):
        received.append(kwargs)
        return SimpleNamespace(return_code=0, stdout='{"data":"eA=="}', stderr="")

    tools = SandboxTools(execute, time.monotonic() + 10)
    path = "/output/$(touch /host-canary); 'x'"
    result = asyncio.run(tools.dispatch({"operation": "read", "path": path}))
    args = shlex.split(received[0]["command"])
    assert args[:2] == ["python3", "-c"]
    assert json.loads(base64.b64decode(args[3]))["path"] == path
    assert result == {"data": "eA=="}
    assert tools.records[0]["status"] == "completed"


def test_transport_failure_never_falls_back_to_host():
    async def execute(**kwargs):
        raise ConnectionError("offline")

    tools = SandboxTools(execute, time.monotonic() + 10)
    with pytest.raises(ConnectionError):
        asyncio.run(tools.dispatch({"operation": "read", "path": "/etc/passwd"}))
    assert tools.records[0]["status"] == "failed"


def test_expired_deadline_does_not_execute():
    async def execute(**kwargs):
        raise AssertionError("Must not execute after deadline")

    with pytest.raises(TimeoutError):
        asyncio.run(
            SandboxTools(execute, time.monotonic() - 1).dispatch(
                {"operation": "bash", "command": "true", "cwd": "/workspace"}
            )
        )


def test_shell_timeout_and_cwd_are_enforced_in_remote_command():
    received = []

    async def execute(**kwargs):
        received.append(kwargs)
        return SimpleNamespace(return_code=124, stdout="partial", stderr="")

    tools = SandboxTools(execute, time.monotonic() + 300)
    result = asyncio.run(
        tools.dispatch(
            {"operation": "bash", "command": "sleep 30", "cwd": "/workspace space", "timeout": 1}
        )
    )
    assert "cd '/workspace space'" in received[0]["command"]
    assert "timeout --kill-after=1s 1.000s bash -lc 'sleep 30'" in received[0]["command"]
    assert result["exitCode"] == 124
    assert result["stdout"] == "partial"
