"""Remote CPU worker for one offline Harbor/Pi integration job.

Receives private service credentials through the approved runtime environment.
Records source/lock hashes, preserves evidence before deleting owned sandboxes,
and exports small text records independently through job logs.
"""

import base64
import gzip
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

import fsspec
from iris.client.client import iris_ctx
from iris.cluster.types import JobName

HARBOR_REVISION = "9f7b8b404711445b6022f72ff7e5715eb0d1a316"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def command(args, *, cwd, timeout, log, env=None):
    started = time.monotonic()
    with log.open("ab") as out:
        result = subprocess.Popen(
            args, cwd=cwd, env=env, stdout=out, stderr=out, start_new_session=True
        )
        try:
            result.wait(timeout=timeout)
        finally:
            if result.returncode is None:
                os.killpg(result.pid, signal.SIGKILL)
                result.wait()
    print(
        "BIOTASKS_PHASE "
        + json.dumps(
            {
                "log": log.name,
                "exit_code": result.returncode,
                "seconds": round(time.monotonic() - started, 3),
            }
        ),
        flush=True,
    )
    if result.returncode:
        raise RuntimeError(f"Command failed; see {log.name}")


def main():
    root = Path.cwd()
    records = root / "records"
    records.mkdir()
    owned = root / "owned-sandboxes.jsonl"
    os.environ["BIOTASKS_OWNED_SANDBOXES"] = str(owned)
    prefix = os.environ["BIOTASKS_ARTIFACT_PREFIX"].rstrip("/")
    assert prefix.startswith("s3://")
    upstream = (
        iris_ctx()
        .client.resolver_for_job(JobName.from_string(os.environ.pop("GLM_ENDPOINT_JOB")))
        .resolve("glm-5.3")
        .endpoints[0]
        .url.rstrip("/")
    )
    os.environ["GLM_API_BASE"] = upstream if upstream.endswith("/v1") else upstream + "/v1"
    model_key = os.environ.pop("GLM_BULK_TOKEN")
    daytona_key = os.environ.pop("DAYTONA_API_KEY")
    secrets = [model_key, daytona_key, upstream]
    python = None
    outcome = {"stage": "harbor_pi_integration", "biological_task": False}
    started = time.monotonic()
    try:
        with zipfile.ZipFile(root / "harbor-input.zip") as archive:
            for member in archive.infolist():
                if not (root / member.filename).resolve().is_relative_to(root):
                    raise ValueError("Unsafe input path")
            archive.extractall(root)
        archive_path = root / "harbor.tar.gz"
        urllib.request.urlretrieve(
            f"https://codeload.github.com/marin-community/harbor/tar.gz/{HARBOR_REVISION}",
            archive_path,
        )
        with tarfile.open(archive_path) as archive:
            archive.extractall(root, filter="data")
        harbor = root / ("harbor-" + HARBOR_REVISION)
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("uv is required by the remote setup")
        command(
            [uv, "sync", "--locked", "--no-dev", "--extra", "daytona"],
            cwd=harbor,
            timeout=600,
            log=records / "harbor-install.txt",
        )
        python = harbor / ".venv/bin/python"
        command(
            [uv, "pip", "freeze", "--python", str(python)],
            cwd=root,
            timeout=30,
            log=records / "python-packages.txt",
        )
        node_version = "v24.14.0"
        node_archive = root / f"node-{node_version}-linux-x64.tar.xz"
        node_base = f"https://nodejs.org/dist/{node_version}/"
        urllib.request.urlretrieve(node_base + node_archive.name, node_archive)
        checksums = urllib.request.urlopen(node_base + "SHASUMS256.txt", timeout=30).read().decode()
        expected = next(
            line.split()[0]
            for line in checksums.splitlines()
            if line.split()[-1] == node_archive.name
        )
        assert digest(node_archive) == expected
        with tarfile.open(node_archive) as archive:
            archive.extractall(root, filter="data")
        node_bin = root / node_archive.name.removesuffix(".tar.xz") / "bin"
        os.environ["PATH"] = str(node_bin) + ":" + os.environ["PATH"]
        pi = root / "pi-runtime"
        pi.mkdir()
        command(
            [
                str(node_bin / "npm"),
                "install",
                "--prefix",
                str(pi),
                "--no-audit",
                "--no-fund",
                "--save-exact",
                "@earendil-works/pi-coding-agent@1.1.0",
            ],
            cwd=root,
            timeout=300,
            log=records / "pi-install.txt",
        )
        shutil.copyfile(pi / "package-lock.json", records / "pi-package-lock.json")
        os.environ["BIOTASKS_PI_COMMAND"] = str(pi / "node_modules/.bin/pi")
        # Pi loads the explicit extension beside its dependency package.
        (root / "node_modules").symlink_to(pi / "node_modules", target_is_directory=True)
        os.environ["PYTHONPATH"] = str(root)
        config = {
            "job_name": "pi-offline-001",
            "jobs_dir": str(root / "jobs"),
            "n_attempts": 1,
            "n_concurrent_trials": 1,
            "quiet": True,
            "retry": {"max_retries": 0},
            "trial_attempt_timeout_sec": 1800,
            "environment": {
                "import_path": "retained_daytona:RetainedDaytona",
                "delete": False,
                "kwargs": {"network_policy": {"mode": "block_all"}, "auto_stop_interval_mins": 10},
            },
            "agents": [
                {
                    "import_path": "harbor_pi_remote:PiRemoteAgent",
                    "model_name": "biotasks/glm-5.3",
                    "max_timeout_sec": 300,
                    "override_setup_timeout_sec": 60,
                }
            ],
            "tasks": [{"path": str(root / "pi-offline-task")}],
        }
        (root / "harbor-job.json").write_text(json.dumps(config, indent=2))
        (records / "pins.json").write_text(
            json.dumps(
                {
                    "harbor_revision": HARBOR_REVISION,
                    "harbor_archive_sha256": digest(archive_path),
                    "harbor_uv_lock_sha256": digest(harbor / "uv.lock"),
                    "node_archive_sha256": expected,
                    "pi_version": "1.1.0",
                    "input_sha256": digest(root / "harbor-input.zip"),
                },
                indent=2,
            )
        )
        command(
            [str(python), str(root / "harbor_job.py")],
            cwd=root,
            timeout=1900,
            log=records / "harbor-run.txt",
            env=os.environ | {"GLM_BULK_TOKEN": model_key, "DAYTONA_API_KEY": daytona_key},
        )
        outcome["orchestration_finished"] = True
    except Exception as error:
        outcome.update(
            orchestration_finished=False, error_type=type(error).__name__, error=str(error)
        )
    finally:
        outcome["seconds_before_export"] = round(time.monotonic() - started, 3)
        for name in ["harbor-job.json", "harbor-result.json", "owned-sandboxes.jsonl"]:
            if (root / name).exists():
                shutil.copyfile(root / name, records / name)
        if (root / "jobs").exists():
            shutil.copytree(root / "jobs", records / "jobs")
        (records / "outcome.json").write_text(json.dumps(outcome, indent=2))
        # No env/config credential files enter records. Scrub known secrets from text logs.
        for path in records.rglob("*"):
            if not path.is_file():
                continue
            try:
                value = path.read_text()
            except UnicodeError:
                continue
            for secret in secrets:
                value = value.replace(secret, "[REDACTED]")
            path.write_text(value)
        manifest = []
        for path in records.rglob("*"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(records))
            destination = prefix + "/records/" + relative
            with path.open("rb") as source, fsspec.open(destination, "wb").open() as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
            # Verify read-back bytes before permitting sandbox teardown.
            check = hashlib.sha256()
            with fsspec.open(destination, "rb").open() as source:
                while chunk := source.read(1024 * 1024):
                    check.update(chunk)
            assert check.hexdigest() == digest(path), "Durable evidence verification failed"
            manifest.append(
                {"path": relative, "sha256": check.hexdigest(), "size": path.stat().st_size}
            )
        with fsspec.open(prefix + "/manifest.json", "wt").open() as target:
            json.dump(manifest, target, indent=2)
        if python is not None and owned.exists():
            try:
                command(
                    [str(python), str(root / "harbor_job.py"), "cleanup"],
                    cwd=root,
                    timeout=180,
                    log=records / "cleanup-log.txt",
                    env=os.environ | {"DAYTONA_API_KEY": daytona_key},
                )
            finally:
                if (root / "cleanup.json").exists():
                    shutil.copyfile(root / "cleanup.json", records / "cleanup.json")
                    with fsspec.open(prefix + "/cleanup.json", "wt").open() as target:
                        target.write((root / "cleanup.json").read_text())
        export = {
            str(p.relative_to(records)): p.read_text(errors="replace")
            for p in records.rglob("*")
            if p.is_file()
            and p.stat().st_size < 512 * 1024
            and p.suffix in {".json", ".jsonl", ".txt", ".log"}
        }
        packed = gzip.compress(json.dumps(export).encode())
        encoded = base64.b64encode(packed).decode()
        chunks = [encoded[i : i + 6000] for i in range(0, len(encoded), 6000)]
        print(
            "BIOTASKS_SMOKE_ARCHIVE "
            + json.dumps({"chunks": len(chunks), "sha256": hashlib.sha256(packed).hexdigest()}),
            flush=True,
        )
        for index, chunk in enumerate(chunks):
            print(f"BIOTASKS_SMOKE_CHUNK {index} {chunk}", flush=True)
        print("BIOTASKS_HARBOR_RESULT " + json.dumps(outcome), flush=True)


if __name__ == "__main__":
    main()
