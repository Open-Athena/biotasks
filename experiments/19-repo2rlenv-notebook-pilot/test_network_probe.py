"""DNS must not outlive the probe; failed probes never establish isolation."""

import json
import os
import subprocess
import sys
import time

import preflight
import pytest


def run_probe(code, targets):
    return subprocess.run(
        [sys.executable, "-c", "TARGETS = " + repr(targets) + "\n" + code],
        capture_output=True,
        text=True,
        timeout=5,
    )


def test_stalled_lookup_is_bounded_and_child_reaped(tmp_path):
    pid_path = tmp_path / "connector.pid"
    connector = (
        "import os,socket,time\nfrom pathlib import Path\n"
        "def blocked_lookup(*args, **kwargs):\n"
        f"    Path({str(pid_path)!r}).write_text(str(os.getpid()))\n"
        "    time.sleep(30)\n"
        "socket.getaddrinfo = blocked_lookup\n" + preflight.CONNECT_CODE
    )
    start = time.monotonic()
    result = run_probe(preflight.probe_source(connector, timeout_seconds=0.5), [("unused", 443)])
    assert result.returncode == 0 and time.monotonic() - start < 5
    assert json.loads(result.stdout) == [{"host": "unused", "port": 443, "reachable": False}]
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_path.read_text()), 0)


@pytest.mark.parametrize("exit_code,reachable", [(0, True), (10, False)])
def test_completed_connector_outcomes(exit_code, reachable):
    result = run_probe(preflight.probe_source(f"raise SystemExit({exit_code})"), [("unused", 443)])
    assert result.returncode == 0
    assert json.loads(result.stdout) == [{"host": "unused", "port": 443, "reachable": reachable}]


@pytest.mark.parametrize("exit_code", [1, 2, -9])
def test_unexpected_connector_failure_is_not_offline_evidence(exit_code):
    # Negative statuses are simulated by a real signal, not normalized to an
    # ordinary known-unreachable result.
    source = (
        f"raise SystemExit({exit_code})"
        if exit_code >= 0
        else "import os,signal;os.kill(os.getpid(),signal.SIGKILL)"
    )
    result = run_probe(preflight.probe_source(source), [("unused", 443)])
    assert result.returncode != 0 and not result.stdout.strip()
