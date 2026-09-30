"""Linux shared-node guard for this research study; estimate MiB then command."""

import datetime
import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


def available_mib():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024
    raise RuntimeError("MemAvailable unavailable")


def now():
    return datetime.datetime.now(datetime.UTC).isoformat()


estimate = int(sys.argv[1])
command = sys.argv[2:]
lock = open("/tmp/exe-codex-local-heavy.lock", "a")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit("Shared heavy-work lock is held; aborting without waiting.")
available = available_mib()
load = os.getloadavg()[0]
if estimate > 500 or available < 2560 or available - estimate < 2048 or load >= 1.5:
    sys.exit(
        f"Resource gate: estimate={estimate} MiB, available={available:.0f} MiB, load={load:.2f}"
    )
env = os.environ.copy()
for name in (
    "POLARS_MAX_THREADS",
    "RAYON_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "UV_CONCURRENT_BUILDS",
    "UV_CONCURRENT_INSTALLS",
):
    env[name] = "1"
env["UV_CONCURRENT_DOWNLOADS"] = "1"
env["UV_CACHE_DIR"] = "/tmp/biotasks-uv-cache"
env["PRE_COMMIT_HOME"] = "/tmp/biotasks-pre-commit"
report = tempfile.NamedTemporaryFile(prefix="biotasks-resources-", suffix=".txt", delete=False)
report.close()
print(
    json.dumps(
        {
            "start": now(),
            "estimate_mib": estimate,
            "available_mib": round(available),
            "load": load,
            "report": report.name,
            "command": command,
        }
    ),
    flush=True,
)
process = subprocess.Popen(
    [
        "nice",
        "-n",
        "10",
        "ionice",
        "-c",
        "2",
        "-n",
        "7",
        "/usr/bin/time",
        "-v",
        "-o",
        report.name,
        *command,
    ],
    env=env,
    start_new_session=True,
)
reason = None
try:
    while True:
        try:
            result = process.wait(timeout=2)
            break
        except subprocess.TimeoutExpired:
            if available_mib() < 2048 or os.getloadavg()[0] > 2.5:
                reason = "Shared-node stop threshold exceeded"
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                result = 125
                break
except BaseException:
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    raise
finally:
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        pass
    else:
        os.killpg(process.pid, signal.SIGKILL)
        reason = reason or "Stopped remaining task-owned subprocesses"
print(json.dumps({"end": now(), "exit_status": result, "reason": reason}), flush=True)
for line in Path(report.name).read_text().splitlines():
    if "Maximum resident set size" in line or "Elapsed (wall clock)" in line:
        print(line.strip(), flush=True)
sys.exit(result)
