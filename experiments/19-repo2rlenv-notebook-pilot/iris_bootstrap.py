"""Install frozen inputs and execute exactly one campaign inside an Iris job.

The submitter supplies archives and hashes, never credentials in these files.
Only the Iris process environment supplies service access and artifact storage.
"""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def unpack(archive, destination):
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as source:
        source.extractall(destination, filter="data")


def command(argv, *, cwd, deadline, log, env=None):
    remaining = deadline - time.time()
    if remaining <= 0:
        raise TimeoutError("Campaign deadline exhausted")
    with log.open("ab") as output:
        process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            code = process.wait(timeout=remaining)
        except BaseException:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
        if code:
            raise RuntimeError(f"Campaign subprocess exited with status {code}; inspect its log")


def export(root, prefix):
    import fsspec

    receipts = []
    secrets = [os.environ[key].encode() for key in ("GLM_BULK_TOKEN", "DAYTONA_API_KEY")]
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Do not follow artifact symlinks")
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            tail = b""
            while chunk := stream.read(1024 * 1024):
                combined = tail + chunk
                if any(secret and secret in combined for secret in secrets):
                    raise ValueError("Credential detected in evidence; export requires redaction")
                tail = combined[-max(map(len, secrets)) :]
        relative = path.relative_to(root).as_posix()
        uri = prefix.rstrip("/") + "/" + relative
        with path.open("rb") as source, fsspec.open(uri, "wb").open() as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
        value = hashlib.sha256()
        with fsspec.open(uri, "rb").open() as source:
            while chunk := source.read(1024 * 1024):
                value.update(chunk)
        expected = digest(path)
        if value.hexdigest() != expected:
            raise ValueError("Artifact download hash mismatch")
        receipts.append({"path": relative, "sha256": expected, "bytes": path.stat().st_size})
    with fsspec.open(prefix.rstrip("/") + "/export-manifest.json", "w").open() as stream:
        json.dump({"files": receipts, "download_checked": True}, stream)


def main():
    from iris.client.client import iris_ctx
    from iris.cluster.types import JobName

    inputs = Path.cwd()
    manifest = json.loads((inputs / "inputs.json").read_text())
    deadline = time.time() + 7200
    evidence = Path("/evidence")
    evidence.mkdir(exist_ok=True)
    status = {"started": time.time(), "completed": False}
    try:
        for name, expected in manifest["files"].items():
            if Path(name).name != name or digest(inputs / name) != expected:
                raise ValueError("Frozen input checksum mismatch")
        code = Path("/work/biotasks")
        unpack(inputs / "biotasks.tar", code)
        unpack(inputs / "upstream.tar.gz", Path("/work/upstream-archive"))
        candidates = list(Path("/work/upstream-archive").iterdir())
        if len(candidates) != 1 or not candidates[0].is_dir():
            raise ValueError("Unexpected upstream archive layout")
        upstream = candidates[0]
        os.environ["UV_PROJECT_ENVIRONMENT"] = str(upstream / ".venv")
        experiment = code / "experiments/19-repo2rlenv-notebook-pilot"
        pin = json.loads((experiment / "upstream-pin.json").read_text())
        if digest(upstream / "uv.lock") != pin["upstream_lock_sha256"]:
            raise ValueError("Upstream lock mismatch")
        for item in pin["files"]:
            if digest(upstream / item["path"]) != item["sha256"]:
                raise ValueError("Upstream source mismatch")
        for item in pin["patches"]:
            patch = experiment / item["path"]
            if digest(patch) != item["sha256"]:
                raise ValueError("Patch checksum mismatch")
            command(
                ["patch", "-p1", "--batch", "-i", str(patch)],
                cwd=upstream,
                deadline=deadline,
                log=evidence / "setup.log",
            )
        command(
            [
                "uv",
                "sync",
                "--locked",
                "--no-dev",
                "--extra",
                "harbor",
                "--extra",
                "daytona",
                "--python",
                sys.executable,
            ],
            cwd=upstream,
            deadline=deadline,
            log=evidence / "setup.log",
        )
        command(
            ["uv", "build", "--wheel", "--out-dir", str(evidence / "runtime")],
            cwd=upstream,
            deadline=deadline,
            log=evidence / "setup.log",
        )
        (wheel,) = (evidence / "runtime").glob("*.whl")
        route = (
            iris_ctx()
            .client.resolver_for_job(JobName.from_string(os.environ["GLM_ENDPOINT_JOB"]))
            .resolve("glm-5.3")
            .endpoints
        )
        if not route:
            raise RuntimeError("Approved model route has no available endpoint")
        endpoint = route[0].url.rstrip("/")
        if not endpoint.endswith("/v1"):
            endpoint += "/v1"
        env = {
            **os.environ,
            "PYTHONPATH": str(code / "src") + os.pathsep + str(experiment),
            "BIOTASKS_MODEL_ENDPOINT": endpoint,
            "BIOTASKS_CAMPAIGN_DEADLINE": str(deadline),
            "BIOTASKS_RUNTIME_WHEEL": str(wheel),
            "BIOTASKS_SEED": str(inputs / "seeds.json"),
            "BIOTASKS_CONFIG": str(inputs / "campaign-config.json"),
        }
        shutil.copyfile(inputs / "inputs.json", evidence / "inputs.json")
        command(
            [str(upstream / ".venv/bin/python"), str(experiment / "run_pilot.py")],
            cwd=experiment,
            deadline=deadline,
            env=env,
            log=evidence / "campaign.log",
        )
        status["completed"] = True
    except BaseException as error:
        status["error_type"] = type(error).__name__
        raise
    finally:
        status["finished"] = time.time()
        (evidence / "bootstrap-status.json").write_text(json.dumps(status, indent=2))
        export(evidence, os.environ["BIOTASKS_ARTIFACT_PREFIX"])
        # Return bounded, hash-bound diagnostics through this job's existing log,
        # avoiding a separate recovery job when the operator cannot read S3.
        runpy.run_path(str(inputs / "diagnostics.py"), run_name="__main__")


if __name__ == "__main__":
    main()
