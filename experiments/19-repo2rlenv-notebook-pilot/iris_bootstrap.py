"""Install frozen inputs and execute exactly one campaign inside an Iris job.

The submitter supplies archives and hashes, never credentials in these files.
Only the Iris process environment supplies service access and artifact storage.
"""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import select
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
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


class ExportStalled(TimeoutError):
    """The export process stopped reporting I/O progress."""


def wait_for_progress(process, descriptor, *, deadline, idle_seconds):
    last = time.monotonic()
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError("Campaign deadline exhausted")
        idle = idle_seconds - (time.monotonic() - last)
        if idle <= 0:
            raise ExportStalled("Evidence export stopped making progress")
        ready, _, _ = select.select([descriptor], [], [], min(remaining, idle))
        if ready:
            if os.read(descriptor, 4096):
                last = time.monotonic()
            else:
                return process.wait(timeout=max(0.001, deadline - time.time()))


def command(argv, *, cwd, deadline, log, env=None, progress_timeout=None):
    remaining = deadline - time.time()
    if remaining <= 0:
        raise TimeoutError("Campaign deadline exhausted")
    read_fd = write_fd = None
    if progress_timeout is not None:
        if progress_timeout <= 0:
            raise ValueError("Progress timeout must be positive")
        read_fd, write_fd = os.pipe()
        env = {**(os.environ if env is None else env), "BIOTASKS_EXPORT_PROGRESS_FD": str(write_fd)}
    try:
        with log.open("ab") as output:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                pass_fds=(() if write_fd is None else (write_fd,)),
            )
            if write_fd is not None:
                os.close(write_fd)
                write_fd = None
            try:
                code = (
                    process.wait(timeout=remaining)
                    if read_fd is None
                    else wait_for_progress(
                        process, read_fd, deadline=deadline, idle_seconds=progress_timeout
                    )
                )
            except BaseException:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                try:
                    grace = (
                        20 if progress_timeout is None else min(20, max(0, deadline - time.time()))
                    )
                    process.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
            if code:
                raise RuntimeError(
                    f"Campaign subprocess exited with status {code}; inspect its log"
                )
    finally:
        for descriptor in (read_fd, write_fd):
            if descriptor is not None:
                os.close(descriptor)


def export_progress():
    descriptor = os.environ.get("BIOTASKS_EXPORT_PROGRESS_FD")
    if descriptor is not None:
        os.write(int(descriptor), b".")


def export(root, prefix):
    from concurrent.futures import ThreadPoolExecutor

    import fsspec

    secrets = [
        os.environ[key].encode()
        for key in ("GLM_BULK_TOKEN", "DAYTONA_API_KEY", "HF_TOKEN")
        if os.environ.get(key)
    ]
    overlap = max(map(len, secrets), default=0)
    paths = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Do not follow artifact symlinks")
        if path.is_file():
            paths.append(path)

    def transfer(path):
        export_progress()
        # Bounded streaming per file, including with no credentials configured.
        with path.open("rb") as stream:
            tail = b""
            while chunk := stream.read(1024 * 1024):
                combined = tail + chunk
                if any(secret in combined for secret in secrets):
                    raise ValueError("Credential detected in evidence; export requires redaction")
                tail = combined[-overlap:] if overlap else b""
                export_progress()
        relative = path.relative_to(root).as_posix()
        uri = prefix.rstrip("/") + "/" + relative
        expected = digest(path)
        with path.open("rb") as source, fsspec.open(uri, "wb").open() as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
                export_progress()
        value = hashlib.sha256()
        with fsspec.open(uri, "rb").open() as source:
            while chunk := source.read(1024 * 1024):
                value.update(chunk)
                export_progress()
        if value.hexdigest() != expected or digest(path) != expected:
            raise ValueError("Artifact download hash mismatch or source changed")
        export_progress()
        return {
            "path": relative,
            "sha256": expected,
            "bytes": path.stat().st_size,
            "mode": path.stat().st_mode & 0o777,
        }

    # Remote Iris storage I/O only: four bounded transfers, no scientific workers.
    # map preserves manifest order; every object is downloaded and hash checked.
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(transfer, paths))
    with fsspec.open(prefix.rstrip("/") + "/export-manifest.json", "w").open() as stream:
        json.dump({"files": receipts, "download_checked": True}, stream)


def export_on_host(root, prefix, *, deadline, log=None):
    """Use the provisioned storage client without adding it to upstream's lock."""
    for attempt in range(2):
        try:
            command(
                [
                    os.environ.get("BIOTASKS_EXPORT_PYTHON", sys.executable),
                    str(Path(__file__).resolve()),
                    "--export",
                    str(root),
                    prefix,
                ],
                cwd=root.parent,
                deadline=deadline,
                log=log if log is not None else root.parent / "reference-export.log",
                progress_timeout=float(os.environ.get("BIOTASKS_EXPORT_IDLE_SECONDS", "600")),
            )
            return
        except ExportStalled:
            if attempt:
                raise
            # Retry only a stalled transport, never a failed integrity/credential check.
            # The fresh process writes identical source bytes to the unsealed prefix.
            print("Evidence export stalled; retrying once with a fresh storage client.", flush=True)


def export_final_evidence(evidence, inputs, *, deadline):
    """Keep the active transport log outside the snapshot; always emit diagnostics."""
    try:
        with tempfile.TemporaryDirectory(prefix="biotasks-final-export-") as temporary:
            log = Path(temporary) / "archive.log"
            try:
                export_on_host(
                    evidence, os.environ["BIOTASKS_ARTIFACT_PREFIX"], deadline=deadline, log=log
                )
            except BaseException as error:
                data = log.read_bytes() if log.exists() else b""
                original_sha256 = hashlib.sha256(data).hexdigest()
                for name in ("GLM_BULK_TOKEN", "DAYTONA_API_KEY", "HF_TOKEN"):
                    if secret := os.environ.get(name):
                        data = data.replace(secret.encode(), b"[REDACTED]")
                (evidence / "archive.log").write_bytes(data)
                status_path = evidence / "bootstrap-status.json"
                status = json.loads(status_path.read_text())
                status.update(
                    archive_error_type=type(error).__name__,
                    archive_log_original_sha256=original_sha256,
                )
                status_path.write_text(json.dumps(status, indent=2))
                raise
    finally:
        runpy.run_path(str(inputs / "diagnostics.py"), run_name="__main__")


def main():
    from iris.client.client import iris_ctx
    from iris.cluster.types import JobName

    inputs = Path.cwd()
    manifest = json.loads((inputs / "inputs.json").read_text())
    configuration = json.loads((inputs / "campaign-config.json").read_text())
    entrypoint = configuration.get("entrypoint", "run_pilot.py")
    if entrypoint not in {
        "run_pilot.py",
        "run_reference.py",
        "run_coverage.py",
        "run_preparation.py",
        "run_schema_probe.py",
        "run_reference_setup.py",
        "run_specification.py",
        "run_reference_replay.py",
        "run_notebook_grader.py",
        "run_scientific_native.py",
        "run_autonomous.py",
        "run_roundtrip_diagnostic.py",
    }:
        raise ValueError("Unsupported checkpointed experiment entrypoint")
    deadline = min(time.time() + 7200, configuration.get("absolute_deadline", float("inf")))
    cleanup_deadline = deadline + configuration.get("cleanup_seconds", 300)
    os.environ["BIOTASKS_EXPORT_IDLE_SECONDS"] = str(
        configuration.get("request_timeout_seconds", 600)
    )
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
        if entrypoint == "run_autonomous.py":
            converter = Path("/work/converter")
            command(
                ["uv", "sync", "--locked", "--no-dev", "--python", sys.executable],
                cwd=code,
                deadline=deadline,
                log=evidence / "setup.log",
                env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(converter)},
            )
            os.environ["BIOTASKS_CONVERSION_PYTHON"] = str(converter / "bin/python")
        endpoint = ""
        if entrypoint != "run_reference_replay.py":
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
            "BIOTASKS_EXPORT_PYTHON": sys.executable,
        }
        if (inputs / "continuation.tar.gz").exists():
            unpack(inputs / "continuation.tar.gz", evidence / "continuation")
            env["BIOTASKS_CONTINUATION"] = str(evidence / "continuation")
        shutil.copyfile(inputs / "inputs.json", evidence / "inputs.json")
        if entrypoint == "run_scientific_native.py":
            command(
                [
                    sys.executable,
                    str(experiment / "native_inputs.py"),
                    str(inputs / "campaign-config.json"),
                ],
                cwd=experiment,
                deadline=min(deadline, time.time() + 1800),
                env=env,
                log=evidence / "native-retrieval.log",
            )
        if entrypoint == "run_notebook_grader.py":
            command(
                [
                    sys.executable,
                    str(experiment / "grading_inputs.py"),
                    str(inputs / "campaign-config.json"),
                ],
                cwd=experiment,
                deadline=min(deadline, time.time() + 1800),
                env=env,
                log=evidence / "grading-retrieval.log",
            )
        if entrypoint == "run_coverage.py":
            command(
                [
                    sys.executable,
                    str(experiment / "coverage_inputs.py"),
                    str(inputs / "campaign-config.json"),
                ],
                cwd=experiment,
                deadline=min(deadline, time.time() + 1800),
                env=env,
                log=evidence / "inspection-setup.log",
            )
        command(
            [str(upstream / ".venv/bin/python"), str(experiment / entrypoint)],
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
        export_final_evidence(evidence, inputs, deadline=cleanup_deadline)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--export":
        export(Path(sys.argv[2]), sys.argv[3])
    else:
        main()
