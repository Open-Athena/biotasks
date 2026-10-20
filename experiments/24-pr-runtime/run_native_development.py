"""Bounded native PR validation, with a declared generic Python bootstrap profile.

Run only on authorized reserved TRC Docker capacity. No target code runs in
the controller. All target execution uses public-egress, bounded containers
with no mounts, inherited secrets, or Docker socket.
"""

import dataclasses
import concurrent.futures
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

REVISION = "27d04ee8203cd5b2f20c3997d13836e5f5b64238"
CLIENT_HASH = "4f798b3ee1e0140eab5bf30b0edc4e84f4cdb53255a429dc3bbae9524845d640"
ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ["IRIS_OUTPUT_DIR"])
OUT.mkdir(parents=True, exist_ok=True)


def prepare():
    """Install pinned trusted runner code; never install the target repo here."""
    # Iris mounts /tmp as scratch tmpfs; install executables in the guest
    # filesystem rather than assuming the scratch mount permits execution.
    tools = Path("/opt/biotasks24-tools")
    tools.mkdir()
    (OUT / "runner-filesystem.json").write_text(json.dumps({
        "tools_directory": str(tools),
        "tmp_mount_options": [
            line.split()[3] for line in Path("/proc/mounts").read_text().splitlines()
            if line.split()[1] == "/tmp"
        ],
    }, indent=2) + "\n")
    archive = tools / "docker.tgz"
    digest = hashlib.sha256()
    with urllib.request.urlopen(
        "https://download.docker.com/linux/static/stable/x86_64/docker-27.5.1.tgz",
        timeout=30,
    ) as response, archive.open("wb") as output:
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            assert total < 100 * 1024**2
            digest.update(chunk)
            output.write(chunk)
    assert digest.hexdigest() == CLIENT_HASH
    with tarfile.open(archive) as bundle:
        (tools / "docker").write_bytes(bundle.extractfile("docker/docker").read())
    (tools / "docker").chmod(0o755)
    archive.unlink()
    with (OUT / "docker-client-version.txt").open("w") as log:
        subprocess.run([str(tools / "docker"), "--version"], stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=15)
    venv = tools / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, timeout=60)
    os.environ["PATH"] = f"{tools}:{venv / 'bin'}:/usr/local/bin:/usr/bin:/bin"
    with (OUT / "runner-install.log").open("w") as log:
        subprocess.run([
            str(venv / "bin/python"), "-m", "pip", "install", "uv_build==0.11.2",
        ], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        subprocess.run([
            str(venv / "bin/python"), "-m", "pip", "install", "--no-build-isolation",
            f"https://github.com/huggingface/Repo2RLEnv/archive/{REVISION}.tar.gz",
        ], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    os.execv(str(venv / "bin/python"), [str(venv / "bin/python"), str(__file__), "--installed"])


def main():
    from repo2rlenv.bootstrap import docker as native_docker
    from repo2rlenv.pipelines.pr_runtime import (
        _files_in_patch, normalize_test_cmds_for_runtime,
        split_patch_and_test_patch, targeted_test_cmds_for_pr,
    )
    from repo2rlenv.pipelines.pr_runtime_validate import validate_pr

    assert hashlib.sha256(Path(inspect.getfile(validate_pr)).read_bytes()).hexdigest() == (
        "1f8349718bc93315bf3e5cbb10d5823c832539a8ef680b5ee169e4562de3ea49"
    )
    manifest = json.loads((ROOT / "development-input.json").read_text())
    (OUT / "development-input.json").write_bytes((ROOT / "development-input.json").read_bytes())
    for filename in ("run_native_development.py", "install_python_profile.py"):
        (OUT / filename).write_bytes((ROOT / filename).read_bytes())
    if manifest.get("verify_exports"):
        (OUT / "verify_export.py").write_bytes((ROOT / "verify_export.py").read_bytes())
        os.environ["DOCKER_BUILDKIT"] = "0"
    with (OUT / "runner-packages.txt").open("w") as packages:
        subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], stdout=packages, check=True)
    assert manifest["cohort"] == "development"
    run_id = manifest["run_id"]
    assert re.fullmatch(r"biotasks24-[a-z0-9-]+", run_id)
    repo = manifest["repository"]
    assert re.fullmatch(r"[\w.-]+/[\w.-]+", repo)
    ref = manifest["bootstrap_ref"]
    base_image = manifest.get("base_image", "python:3.11-slim-bookworm")
    assert re.fullmatch(r"python:3\.(11|12)-slim-bookworm", base_image)
    assert re.fullmatch(r"[a-f0-9]{40}", ref)
    for row in manifest["prs"]:
        assert row["cohort"] == "development"
        assert hashlib.sha256(row["diff"].encode()).hexdigest() == row["diff_sha256"]
    original_run = native_docker._run
    commands = []
    container_ids = set()
    exec_index = 0

    def bounded_run(args, **kwargs):
        nonlocal exec_index
        args = list(args)
        if args[:2] == ["docker", "run"]:
            assert not any(x in args for x in ("--privileged", "-v", "--volume", "--mount"))
            args[2:2] = [
                "--label", f"biotasks24.run={run_id}",
                "--cpus", "2", "--memory", "8g", "--memory-swap", "8g",
                "--pids-limit", "512", "--cap-drop", "NET_RAW", "--rm",
                "--security-opt", "no-new-privileges",
                "--network", "none" if os.environ.get("BIOTASKS24_OFFLINE") else "iris-egress",
                "--dns", "8.8.8.8",
                "-e", "OMP_NUM_THREADS=1", "-e", "OPENBLAS_NUM_THREADS=1",
                "-e", "MKL_NUM_THREADS=1", "-e", "NUMEXPR_NUM_THREADS=1",
            ]
            assert args[-2:] == ["sleep", "infinity"]
            args[-1] = "3000"  # Guest lifetime bound even if the Iris controller is interrupted.
        if args[:2] == ["docker", "exec"]:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(original_run, args, **kwargs)
                while True:
                    try:
                        result = future.result(timeout=30)
                        break
                    except concurrent.futures.TimeoutError:
                        size = original_run(
                            ["docker", "inspect", "--size", "--format", "{{.SizeRw}}", args[2]],
                            timeout=15,
                        )
                        if not size.ok or int(size.stdout.strip()) > 20 * 1024**3:
                            original_run(["docker", "rm", "-f", args[2]], timeout=30)
                            raise RuntimeError("Container storage exceeded bound or could not be measured")
        else:
            result = original_run(args, **kwargs)
        commands.append({
            "operation": args[1] if args[0] == "docker" else args[0],
            "exit_code": result.exit_code, "duration_sec": result.duration_sec,
        })
        if args[:2] == ["docker", "run"] and result.ok:
            container_ids.add(result.stdout.strip())
        if args[:2] == ["docker", "exec"]:
            exec_index += 1
            (OUT / f"exec-{exec_index:03d}.json").write_text(
                json.dumps(dataclasses.asdict(result), indent=2) + "\n"
            )
            if result.exit_code == 124:
                original_run(["docker", "rm", "-f", args[2]], timeout=30)
                raise TimeoutError("Container exec timed out; container removed to stop its processes")
        return result

    native_docker._run = bounded_run
    report = {
        "stage": "development_native_validation",
        "variant": "native validator with generic declarative Python bootstrap",
        "native_revision": REVISION, "model_calls": 0, "repository": repo,
        "run_id": run_id, "bootstrap_ref": ref, "results": [],
        "limits": {"container_cpus": 2, "container_memory_gib": 8, "pids": 512,
                   "setup_seconds": 1200, "validation_stage_seconds": 300,
                   "container_lifetime_seconds": 3000, "writable_layer_gib": 20},
        "limitations": [
            "No held-out execution, final task export/build or solver run.",
            "Generic profile is an explicit adaptation; no model-assisted bootstrap was run.",
        ],
    }
    started = time.monotonic()
    sandbox = None
    bootstrap = None
    bootstrap_tag = f"biotasks24/{run_id}:bootstrap"
    try:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)
            (marker / "install_python_profile.py").write_bytes(
                (ROOT / "install_python_profile.py").read_bytes()
            )
            sandbox = native_docker.DockerSandbox.start(
                base_image=base_image, repo_dir=marker,
            )
        image = original_run([
            "docker", "image", "inspect", base_image,
            "--format", "{{json .RepoDigests}}",
        ], timeout=30)
        report["base_image_repo_digests"] = json.loads(image.stdout) if image.ok else None
        setup = (
            "set -eu\n"
            "mv /workspace/install_python_profile.py /tmp/install_python_profile.py\n"
            "apt-get update\n"
            "apt-get install -y --no-install-recommends git build-essential\n"
            "rm -rf /var/lib/apt/lists/*\n"
            "cd /workspace\n"
            "git init\n"
            f"git remote add origin https://github.com/{repo}.git\n"
            f"git fetch --depth=1 origin {ref}\n"
            "git checkout --detach FETCH_HEAD\n"
            "python /tmp/install_python_profile.py\n"
        )
        result = sandbox.exec(setup, timeout=1200)
        report["bootstrap_exit_code"] = result.exit_code
        if not result.ok:
            raise RuntimeError("Generic Python profile installation failed")
        freeze = sandbox.exec("python -m pip freeze --all", timeout=30)
        (OUT / "target-packages.txt").write_text(freeze.stdout)
        if manifest.get("verify_exports"):
            from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
            digest = sandbox.commit(bootstrap_tag, timeout=300)
            bootstrap = BootstrapResult(
                image_digest=digest, image_tag=bootstrap_tag, language=LanguageHint.PYTHON,
                repo=repo, ref=ref, rebuild_cmds=[],
                test_cmds=["python -m pip install --no-deps --no-build-isolation --no-index -e .",
                           "python -m pytest -vv"],
                smoke_passed=False, iterations=0, build_time_sec=time.monotonic() - started,
                llm_provider="none",
            )
            report["bootstrap_image_id"] = digest
        # Native supplied-Dockerfile metadata has empty test_cmds. Preserve
        # its direct validator rejection independently of the declared profile.
        report["empty_test_commands_control"] = dataclasses.asdict(validate_pr(
            sandbox=sandbox, base_commit=ref, patch="", test_patch="", test_cmds=[],
        ))
        for row in manifest["prs"]:
            patch, tests = split_patch_and_test_patch(row["diff"])
            test_cmds = targeted_test_cmds_for_pr(
                normalize_test_cmds_for_runtime([
                    "python -m pip install --no-deps --no-build-isolation --no-index -e .",
                    "python -m pytest -vv",
                ]), _files_in_patch(tests),
            )
            outcome = validate_pr(
                sandbox=sandbox, base_commit=row["base_sha"], patch=patch,
                test_patch=tests, test_cmds=test_cmds, language="python", timeout=300,
            )
            record = {"number": row["number"], "test_cmds": test_cmds, **dataclasses.asdict(outcome)}
            report["results"].append(record)
            if bootstrap is not None and outcome.status == "verified":
                from verify_export import verify_export
                record["export"] = verify_export(
                    native_docker, manifest, row, outcome, bootstrap, OUT,
                )
            (OUT / "development-result.json").write_text(json.dumps(report, indent=2) + "\n")
        report["disposition"] = "development_validation_completed"
    except Exception as exc:
        report["disposition"] = "development_run_failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if sandbox is not None:
            sandbox.cleanup()
        remaining = original_run([
            "docker", "ps", "-aq", "--filter", f"label=biotasks24.run={run_id}",
        ], timeout=30)
        if remaining.ok:
            for cid in remaining.stdout.split():
                assert re.fullmatch(r"[a-f0-9]{12,64}", cid)
                original_run(["docker", "rm", "-f", cid], timeout=30)
        check = original_run([
            "docker", "ps", "-aq", "--filter", f"label=biotasks24.run={run_id}",
        ], timeout=30)
        report["cleanup_verified"] = check.ok and not check.stdout.strip()
        if bootstrap is not None:
            removal = original_run(["docker", "image", "rm", bootstrap_tag], timeout=30)
            report["bootstrap_tag_removed"] = removal.ok
        report["commands"] = commands
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        raw = (json.dumps(report, indent=2) + "\n").encode()
        (OUT / "development-result.json").write_bytes(raw)
        print("BIOTASKS24_DEVELOPMENT " + json.dumps({
            "disposition": report["disposition"], "cleanup_verified": report["cleanup_verified"],
            "results": [{"number": r["number"], "status": r["status"],
                         "f2p": len(r["fail_to_pass"]), "p2p": len(r["pass_to_pass"])}
                        for r in report["results"]],
            "error": report.get("error"),
        }), flush=True)
        print("BIOTASKS24_DEVELOPMENT_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)


if __name__ == "__main__":
    try:
        if "--installed" not in sys.argv:
            prepare()
        main()
    except Exception as exc:
        (OUT / "runner-failure.json").write_text(json.dumps({
            "error": f"{type(exc).__name__}: {exc}",
            "stage": "runner_initialization_or_unhandled_error",
        }, indent=2) + "\n")
        raise
