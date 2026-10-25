"""Reuse the owned compatibility lifecycle; no model or biological computation."""

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "daytona-session-transport/run_live_check.py"
spec = importlib.util.spec_from_file_location("bounded_probe_check_base", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

import preflight  # noqa: E402
import run_reference_setup  # noqa: E402


async def checks(remote, root):
    await remote.network(False)
    await remote.network(True)
    cases = [
        {
            "name": "positive_then_offline_controls",
            "passed": True,
            "same_targets": preflight.TARGETS,
            "provider_readback_and_tcp_probe": True,
        }
    ]
    connector = (
        "import os,socket,time\nfrom pathlib import Path\n"
        "def blocked_lookup(*args, **kwargs):\n"
        "    Path('/work/probe-counts/blocked-dns.pid').write_text(str(os.getpid()))\n"
        "    time.sleep(30)\n"
        "socket.getaddrinfo = blocked_lookup\n" + preflight.CONNECT_CODE
    )
    script = "TARGETS = [('synthetic.invalid', 443)]\n" + preflight.probe_source(connector, 0.5)
    reply = await remote.command(["python", "-c", script], 15, "stalled-dns")
    assert reply["exit_code"] == 0 and not reply["timed_out"]
    assert json.loads(reply["log"]) == [
        {"host": "synthetic.invalid", "port": 443, "reachable": False}
    ]
    check = (
        "import json,os\nfrom pathlib import Path\n"
        "pid=int(Path('/work/probe-counts/blocked-dns.pid').read_text())\n"
        "try:\n os.kill(pid,0)\n reaped=False\n"
        "except ProcessLookupError:\n reaped=True\n"
        "print(json.dumps({'reaped':reaped}))\n"
    )
    observed = await remote.command(["python", "-c", check], 15, "child-reaped")
    assert observed["exit_code"] == 0 and json.loads(observed["log"]) == {"reaped": True}
    cases.append(
        {
            "name": "stalled_resolver",
            "passed": True,
            "synthetic_failure": True,
            "child_killed_and_reaped": True,
        }
    )
    original = run_reference_setup.PROBE
    run_reference_setup.PROBE = preflight.probe_source("raise SystemExit(2)")
    try:
        try:
            await remote.network(True)
        except RuntimeError as error:
            assert "Network probe" in str(error)
        else:
            raise AssertionError("An invalid connector established a network state")
        assert remote.uncertain
        try:
            remote.remaining(1)
        except RuntimeError as error:
            assert "uncertain" in str(error)
        else:
            raise AssertionError("Execution remained allowed after an invalid probe")
    finally:
        run_reference_setup.PROBE = original
    cases.append(
        {
            "name": "invalid_probe_blocks_execution",
            "passed": True,
            "synthetic_failure": True,
            "uncertain_state_retained": True,
        }
    )
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    value = asyncio.run(base.run(json.loads(args.config.read_text()), args.root, checks=checks))
    print(json.dumps(value))
