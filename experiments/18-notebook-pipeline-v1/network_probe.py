"""Run inside a task/verifier sandbox; emit evidence, never a benchmark reward."""

import glob
import json
import os
import socket
import urllib.request
from pathlib import Path

probes = {}
for label, host in [("ip1", "1.1.1.1"), ("ip2", "8.8.8.8")]:
    try:
        with socket.create_connection((host, 443), timeout=3):
            probes[label] = "reachable"
    except OSError as error:
        probes[label] = type(error).__name__
try:
    with urllib.request.urlopen("https://example.com", timeout=3):
        probes["https"] = "reachable"
except Exception as error:
    probes["https"] = type(error).__name__

resources = {}
for name in ["cpu.max", "memory.max", "memory.peak"]:
    path = Path("/sys/fs/cgroup") / name
    resources[name] = path.read_text().strip() if path.exists() else None

result = {
    "probes": probes,
    "network_denied": "reachable" not in probes.values(),
    "inference_credentials_present": any(
        os.environ.get(k)
        for k in ("GLM_BULK_TOKEN", "BIOTASKS_MODEL_KEY", "OPENAI_API_KEY", "DAYTONA_API_KEY")
    ),
    "resources": resources,
    "gpu_devices": glob.glob("/dev/nvidia[0-9]*"),
}
print(json.dumps(result))
