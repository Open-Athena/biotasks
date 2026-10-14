"""Run only inside the disposable sandbox; record bounded plain-script evidence."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def stage_inputs(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    root = Path("/inputs")
    root.mkdir(exist_ok=True)
    records = []
    for item in manifest["data_source"]["files"]:
        name = item["name"]
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("Input inventory requires plain filenames")
        path = root / name
        sha256, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
        with urllib.request.urlopen(item["url"], timeout=60) as response, path.open("xb") as output:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > item["bytes"]:
                    raise ValueError("Input exceeds recorded size")
                output.write(chunk)
                sha256.update(chunk)
                md5.update(chunk)
        if size != item["bytes"] or md5.hexdigest() != item["provider_md5"]:
            raise ValueError("Input inventory checksum or size mismatch")
        records.append(
            {
                **item,
                "local_path": str(path),
                "sha256": sha256.hexdigest(),
                "provider_checksum_verified": True,
            }
        )
    Path("/work/staged-inputs.json").write_text(json.dumps({"files": records}, indent=2))
    print(json.dumps({"files": records}), flush=True)


def verify_inputs():
    records = json.loads(Path("/work/staged-inputs.json").read_text())["files"]
    for item in records:
        with Path(item["local_path"]).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != item["sha256"]:
            raise ValueError("Original staged input changed")
    print(json.dumps({"original_inputs_unchanged": True, "files": len(records)}), flush=True)


def execute(argv, timeout, directory, label):
    log = Path("/work/logs") / (label + ".log")
    log.parent.mkdir(exist_ok=True)
    started = time.time()
    with log.open("wb") as stream:
        process = subprocess.Popen(
            argv, cwd=directory, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True
        )
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = process.returncode
        finally:
            # Do not leave a background child from setup or analysis alive.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    record = {
        "argv": argv,
        "started": started,
        "finished": time.time(),
        "exit_code": code,
        "timed_out": timed_out,
        "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "rss_limitations": "Maximum child RSS, not aggregate sandbox or simultaneous-process memory",
    }
    record["elapsed_seconds"] = record["finished"] - started
    Path("/work/logs", label + ".json").write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


def inventory(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    results = []
    for artifact in plan["artifacts"]:
        path = Path("/work/outputs") / artifact["path"]
        item = {"path": artifact["path"], "exists": path.is_file()}
        if path.is_symlink() or not path.resolve().is_relative_to(Path("/work/outputs")):
            raise ValueError("Artifacts must be regular files within the output directory")
        if item["exists"]:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            item.update(bytes=path.stat().st_size, sha256=digest.hexdigest())
        results.append(item)
    print(
        json.dumps(
            {
                "artifacts": results,
                "declared_artifacts_present": all(
                    row["exists"] and row["bytes"] > 0 for row in results
                ),
                "semantic_fidelity_validated": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    if sys.argv[1] == "stage-inputs":
        stage_inputs(sys.argv[2])
    elif sys.argv[1] == "verify-inputs":
        verify_inputs()
    elif sys.argv[1] == "inventory":
        inventory(sys.argv[2])
    else:
        execute(json.loads(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
