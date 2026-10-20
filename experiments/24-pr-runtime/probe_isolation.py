"""Check the documented Iris sandbox profile without repository or model code."""

import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path


def main():
    report = {
        "model_calls": 0,
        "target_code_executed": False,
        "uid": os.getuid(),
        "python": shutil.which("python"),
        "git_available": shutil.which("git") is not None,
        "pip_available": shutil.which("pip") is not None,
        "docker_socket_present": Path("/var/run/docker.sock").exists(),
        "inherited_secret_names_present": [
            name for name in (
                "HF_TOKEN", "WANDB_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
                "OPENAI_API_KEY", "OPENROUTER_API_KEY", "AWS_SECRET_ACCESS_KEY",
            ) if os.environ.get(name)
        ],
        "controller_env_present": bool(os.environ.get("IRIS_CONTROLLER_ADDRESS")),
    }
    if shutil.which("unshare"):
        proc = subprocess.run(
            ["unshare", "--user", "--map-root-user", "true"],
            capture_output=True, text=True, timeout=10,
        )
        report["user_namespace_exit_code"] = proc.returncode
        report["user_namespace_stderr"] = proc.stderr[:200]
    try:
        with urllib.request.urlopen("https://pypi.org/simple/pip/", timeout=15) as response:
            report["public_package_index_status"] = response.status
            response.read(128)
    except Exception as exc:
        report["public_package_index_error_type"] = type(exc).__name__
    output = Path(os.environ["IRIS_OUTPUT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    (output / "isolation-capabilities.json").write_bytes(raw)
    print("BIOTASKS24_ISOLATION " + json.dumps(report, sort_keys=True), flush=True)
    print("BIOTASKS24_ISOLATION_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
