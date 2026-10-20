"""Test guest namespace prerequisites under Iris SANDBOX only.

No Docker socket access, package installation, host configuration changes,
repository code, model calls, or elevated Iris profiles.
"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
from pathlib import Path


def check(arguments):
    process = subprocess.Popen(
        arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    return {
        "arguments": arguments, "exit_code": process.returncode,
        "timed_out": timed_out, "stdout": stdout[:1000], "stderr": stderr[:1000],
    }


def main():
    assert not Path("/var/run/docker.sock").exists(), "Refuse host Docker socket exposure"
    tests = {}
    if shutil.which("unshare"):
        for name, flags in [
            ("user", ["--user", "--map-root-user"]),
            ("user_mount", ["--user", "--map-root-user", "--mount"]),
            ("user_mount_pid_proc", [
                "--user", "--map-root-user", "--mount", "--pid", "--fork", "--mount-proc",
            ]),
            ("user_network", ["--user", "--map-root-user", "--net"]),
        ]:
            tests[name] = check(["unshare", *flags, "/bin/true"])
    capabilities = {
        line.split(":", 1)[0]: line.split(":", 1)[1].strip()
        for line in Path("/proc/self/status").read_text().splitlines()
        if line.startswith(("CapEff:", "NoNewPrivs:"))
    }
    report = {
        "container_profile_required": "SANDBOX",
        "model_calls": 0, "target_code_executed": False,
        "host_docker_socket_present": False,
        "guest_capabilities": capabilities,
        "tools": {name: shutil.which(name) is not None for name in (
            "newuidmap", "newgidmap", "rootlesskit", "slirp4netns", "dockerd",
        )},
        "namespace_tests": tests,
        "limitations": "Prerequisites only; does not demonstrate Docker daemon or container execution.",
    }
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    (output / "nested-prerequisites.json").write_bytes(raw)
    print("BIOTASKS24_NESTED " + json.dumps(report, sort_keys=True), flush=True)
    print("BIOTASKS24_NESTED_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
