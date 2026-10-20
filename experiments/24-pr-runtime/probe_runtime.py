"""Bounded CPU-only runtime capability probe; no target code or model calls."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def main():
    report = {
        "python": platform.python_version(),
        "uid": os.getuid(),
        "docker_cli": shutil.which("docker") is not None,
        "docker_socket_present": Path("/var/run/docker.sock").exists(),
        "podman_cli": shutil.which("podman") is not None,
        "runsc_cli": shutil.which("runsc") is not None,
        "bwrap_cli": shutil.which("bwrap") is not None,
        "unshare_cli": shutil.which("unshare") is not None,
        "model_calls": 0,
        "target_code_executed": False,
    }
    for name in ("unprivileged_userns_clone",):
        path = Path("/proc/sys/kernel") / name
        report[name] = path.read_text().strip() if path.exists() else None
    if report["docker_cli"]:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=15,
        )
        report["docker_server_reachable"] = result.returncode == 0
        report["docker_server_version"] = result.stdout.strip() if result.returncode == 0 else None
    else:
        report["docker_server_reachable"] = False
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    (output / "runtime-capabilities.json").write_bytes(raw)
    print("BIOTASKS24_CAPABILITIES " + json.dumps(report, sort_keys=True), flush=True)
    print("BIOTASKS24_CAPABILITIES_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
