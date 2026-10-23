"""Synthetic process cleanup regressions; no biology, model or remote execution."""

import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

import grading_remote as remote
import pytest

HERE = Path(__file__).parent


def test_role_discovery_excludes_other_users_and_zombies(tmp_path):
    for pid, uids, state in [
        (11, "18001 18001 18001 18001", "S"),
        (12, "18002 18002 18002 18002", "S"),
        (13, "0 0 0 0", "S"),
        (14, "18001 18001 18001 18001", "Z"),
        (15, "1000 18001 1000 1000", "S"),
        (16, "18001 0 0 0", "S"),
    ]:
        folder = tmp_path / str(pid)
        folder.mkdir()
        (folder / "status").write_text(f"Name:\tfixture\nState:\t{state}\nUid:\t{uids}\n")
    (tmp_path / "self").mkdir()
    (tmp_path / "17").mkdir()  # Process exited before its status was read.
    assert set(remote.role_processes(remote.AUTHOR, tmp_path)) == {11, 15, 16}
    with pytest.raises(ValueError, match="dedicated"):
        remote.role_processes(os.getuid(), tmp_path)


@pytest.mark.parametrize("uid,root", [(0, True), (1000, True), (remote.AUTHOR, False)])
def test_role_cleanup_refuses_shared_node_users(monkeypatch, uid, root):
    monkeypatch.setattr(remote.os, "geteuid", lambda: 0 if root else 1000)
    killed = []
    monkeypatch.setattr(remote.os, "kill", lambda *args: killed.append(args))
    with pytest.raises(RuntimeError, match="sandbox"):
        remote.stop_role_processes(uid)
    with pytest.raises(RuntimeError, match="sandbox"):
        remote.run_as(uid, ["must-not-run"], Path.cwd(), 1)
    assert killed == []


def test_role_cleanup_verifies_absence_or_fails_closed(monkeypatch):
    monkeypatch.setattr(remote.os, "geteuid", lambda: 0)
    states = iter([[123], []])
    monkeypatch.setattr(remote, "role_processes", lambda uid: next(states))
    killed = []
    monkeypatch.setattr(remote.os, "kill", lambda *args: killed.append(args))
    monkeypatch.setattr(remote.time, "sleep", lambda seconds: None)
    remote.stop_role_processes(remote.AUTHOR)
    assert killed == [(123, signal.SIGKILL)]
    monkeypatch.setattr(remote, "role_processes", lambda uid: [123])
    clock = iter([0, 3])
    monkeypatch.setattr(remote.time, "monotonic", lambda: next(clock))
    with pytest.raises(RuntimeError, match="could not be verified"):
        remote.stop_role_processes(remote.AUTHOR)


@pytest.mark.parametrize("mode", ["timeout", "success", "interruption"])
def test_nested_process_group_is_stopped_without_pipe_hang(tmp_path, mode):
    pid_file = tmp_path / "child.json"
    child = (
        "import os,time,json;from pathlib import Path;Path("
        + repr(str(pid_file))
        + ").write_text(json.dumps({'pid':os.getpid(),'group':os.getpgrp()}));"
        + "print('child-ready',flush=True);time.sleep(20)"
    )
    command = "timeout 15 " + shlex.quote(sys.executable) + " -c " + shlex.quote(child)
    if mode == "success":
        command += " & while [ ! -s " + shlex.quote(str(pid_file)) + " ]; do sleep .01; done"
    # Actual forked processes and GNU timeout create/escape groups. Only UID
    # discovery is injected: local tests cannot allocate the sandbox's role IDs.
    # The selector returns this test's exact recorded child, never another user.
    wrapper = f"""
import os,sys,json
from pathlib import Path
sys.path.insert(0,{str(HERE)!r})
import grading_remote as r
os.setgroups=lambda _:None
os.setgid=lambda _:None
os.setuid=lambda _:None
os.geteuid=lambda:0
def owned(uid):
    p=Path({str(pid_file)!r})
    if not p.exists():return []
    pid=json.loads(p.read_text())['pid']
    try:state=Path('/proc/'+str(pid)+'/status').read_text()
    except FileNotFoundError:return []
    return [] if any(s.startswith('State:') and s.split()[1]=='Z' for s in state.splitlines()) else [pid]
r.role_processes=owned
try:
    print(json.dumps(r.run_as(r.AUTHOR,['sh','-c',{command!r}],{str(tmp_path)!r},{20 if mode == "interruption" else 1})))
except TimeoutError:
    print(json.dumps({{'outer_interrupted':True}}))
"""
    process = subprocess.Popen(
        [sys.executable, "-c", wrapper],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    started = time.monotonic()
    try:
        until = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < until:
            time.sleep(0.01)
        assert pid_file.exists()
        child_info = json.loads(pid_file.read_text())
        assert child_info["group"] != process.pid
        if mode == "interruption":
            process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        record = json.loads(stdout)
        if mode == "interruption":
            assert record == {"outer_interrupted": True}
        else:
            assert record["timed_out"] == (mode == "timeout")
            assert record["role_process_cleanup_verified"]
            assert "child-ready" in record["stdout"]
        status = Path(f"/proc/{child_info['pid']}/status")
        if status.exists():
            assert any(
                line.startswith("State:") and line.split()[1] == "Z"
                for line in status.read_text().splitlines()
            )
        assert time.monotonic() - started < 5
    finally:
        if pid_file.exists():
            child_info = json.loads(pid_file.read_text())
            try:
                os.killpg(child_info["group"], signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
