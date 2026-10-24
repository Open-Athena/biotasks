"""Bounded native worker: seal evidence, stop execution, retain until readback.

The cleanup operation is a separate fixed-handle job, admitted before execution
and sent only after the controller has verified the primary archive. No SDK,
model or publication credential is needed inside either worker operation.
"""

import json
import os
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from biotasks.validation.files import require
from biotasks.validation.worker.common import checkpoint, sha, unpack


class Supervisor:
    def __init__(self, root: Path, out: Path, config: dict[str, Any]):
        self.root, self.out, self.config = root, out, config
        self.run = config["run_id"]
        self.tools = root / "tools"
        self.controller = self.run + "-controller"
        self.volume = self.run + "-work"
        self.report: dict[str, Any] = {
            "schema_version": 1,
            "run_id": self.run,
            "worker_id": os.environ["IRIS_WORKER_ID"],
            "operation": config["operation"],
            "started": time.time(),
            "creation_started": False,
            "controller_created": False,
            "controls_started": False,
            "model_calls": 0,
            "new_capacity": False,
            "task_repairs": 0,
            "stage": "startup",
        }

    def save(self) -> None:
        checkpoint(self.out / "work-state.json", self.report)

    def docker(
        self, *args: str, timeout: float = 90, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.tools / "docker"), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )

    def fetch(self, url: str, path: Path, expected: str) -> None:
        with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                require(total <= 100 * 1024**2, "Tool download exceeds bound")
                output.write(chunk)
        require(sha(path) == expected, "Tool download hash changed")

    def tools_ready(self) -> None:
        self.tools.mkdir()
        pins = self.config["tools"]
        self.fetch(pins["docker_url"], self.tools / "docker.tgz", pins["docker_sha256"])
        with tarfile.open(self.tools / "docker.tgz") as archive:
            stream = archive.extractfile("docker/docker")
            require(stream is not None, "Missing Docker executable")
            assert stream is not None
            (self.tools / "docker").write_bytes(stream.read(100 * 1024**2))
        (self.tools / "docker").chmod(0o755)

    def validate(self) -> None:
        require(
            os.environ["BIOTASKS_RUN_ID"] == self.run
            and os.environ["BIOTASKS_EXPECTED_WORKER"] == os.environ["IRIS_WORKER_ID"],
            "Worker/run binding changed",
        )
        require(
            not any(
                os.environ.get(k)
                for k in (
                    "OPENROUTER_API_KEY",
                    "GH_TOKEN",
                    "GITHUB_TOKEN",
                    "CW_KEY_ID",
                    "CW_KEY_SECRET",
                    "HF_TOKEN",
                )
            ),
            "Credentials must not enter the worker",
        )
        payload = json.loads((self.root / "payload.json").read_text())
        for name, value in payload["sha256"].items():
            require(sha(self.root / name) == value, "Payload changed: " + name)
        self.report.update(payload_sha256=payload["sha256"], configuration_verified=True)
        if self.config["operation"] == "execute":
            require(
                self.config["resources"]["cpus"] == 2
                and self.config["resources"]["memory_gib"] == 12,
                "Unsupported profile",
            )
            require(
                sha(self.root / "tasks.tar.gz") == self.config["package"]["sha256"],
                "Task package changed",
            )
            unpack(self.root / "tasks.tar.gz", self.config["package"]["files"])
            shutil.copyfile(self.root / "tasks.tar.gz", self.out / "input-package.tar.gz")
        self.report["stage"] = "validated"
        self.save()

    def logged(
        self, name: str, args: list[str], seconds: float
    ) -> subprocess.CompletedProcess[str]:
        with (self.out / name).open("w") as output:
            return subprocess.run(
                [str(self.tools / "docker"), "exec", *args],
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=seconds,
                text=True,
                check=False,
            )

    def work(self) -> None:
        self.tools_ready()
        pins = self.config["tools"]
        self.fetch(pins["compose_url"], self.tools / "docker-compose", pins["compose_sha256"])
        (self.tools / "docker-compose").chmod(0o755)
        resources = self.config["resources"]
        deadline = time.time() + resources["work_deadline_seconds"]
        require(
            not self.docker(
                "ps", "-aq", "--filter", "label=biotasks.run=" + self.run
            ).stdout.split(),
            "Owned task resources already exist",
        )
        require(
            self.docker("volume", "inspect", self.volume, check=False).returncode != 0,
            "Owned volume already exists",
        )
        self.report.update(creation_started=True, stage="volume_creation")
        self.save()  # Persist and log *before* the first creation request.
        self.docker("volume", "create", "--label", "biotasks.run=" + self.run, self.volume)
        mountpoint = json.loads(self.docker("volume", "inspect", self.volume).stdout)[0][
            "Mountpoint"
        ]
        self.docker("pull", pins["controller_image"], timeout=240)
        self.docker(
            "create",
            "--name",
            self.controller,
            "--cpus=0.5",
            "--memory=4g",
            "--memory-swap=4g",
            "--network=" + self.config["network"],
            "--label",
            "biotasks.controller=" + self.run,
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            self.volume + ":/work",
            "-v",
            self.volume + ":" + mountpoint,
            "-w",
            "/work",
            "-e",
            "BIOTASKS_RUN_ID=" + self.run,
            "-e",
            "BIOTASKS_SHARED_ROOT=" + mountpoint,
            "-e",
            "BIOTASKS_REAL_DOCKER=/work/real/docker",
            "-e",
            "BIOTASKS_WORKER_NETWORK=" + self.config["network"],
            "-e",
            "BIOTASKS_BOUNDED_SUPERVISOR=1",
            "-e",
            "DOCKER_CONFIG=/work/docker-config",
            "-e",
            "PYTHONPATH=/work",
            pins["controller_image"],
            "sleep",
            str(resources["timeout_seconds"]),
        )
        self.report["controller_created"] = True
        self.save()
        self.docker("start", self.controller)
        self.docker(
            "exec",
            self.controller,
            "mkdir",
            "-p",
            "/work/real",
            "/work/evidence",
            "/work/harbor-bin",
            "/work/docker-config/cli-plugins",
            "/work/infra",
        )
        for name in (
            "family.json",
            "tasks.tar.gz",
            "bootstrap-prefix.Dockerfile",
            "setup_controller.sh",
        ):
            self.docker("cp", str(self.root / name), self.controller + ":/work/" + name)
        self.docker("cp", str(self.root / "biotasks"), self.controller + ":/work/biotasks")
        self.docker(
            "cp", str(self.root / "docker-launcher"), self.controller + ":/work/harbor-bin/docker"
        )
        self.docker("exec", self.controller, "chmod", "+x", "/work/harbor-bin/docker")
        self.docker("cp", str(self.tools / "docker"), self.controller + ":/work/real/docker")
        self.docker(
            "cp",
            str(self.tools / "docker-compose"),
            self.controller + ":/work/docker-config/cli-plugins/docker-compose",
        )
        self.docker("exec", self.controller, "tar", "-xzf", "/work/tasks.tar.gz", "-C", "/work")
        self.docker("pull", self.config["task"]["public_base_ref"], timeout=240)
        image = json.loads(
            self.docker("image", "inspect", self.config["task"]["public_base_ref"]).stdout
        )[0]
        self.report["protected_base"] = {
            "run_id": self.run,
            "ref": self.config["task"]["public_base_ref"],
            "image_id": image["Id"],
            "repo_digests": image["RepoDigests"],
        }
        self.docker(
            "create",
            "--name",
            self.run + "-base-reference",
            "--cpus=0.05",
            "--memory=64m",
            "--memory-swap=64m",
            "--network=none",
            "--label",
            "biotasks.controller=" + self.run,
            self.config["task"]["public_base_ref"],
            "true",
        )
        context = "/work/" + self.config["task"]["relative_directory"] + "/environment"
        require(
            time.time() + resources["bootstrap_build_timeout_seconds"] + 300 < deadline,
            "Insufficient build reserve",
        )
        self.report["stage"] = "bootstrap_build_running"
        self.save()
        built = self.logged(
            "bootstrap-build.log",
            [
                self.controller,
                "python",
                "-m",
                "biotasks.validation.worker.docker_bridge",
                "prefix-build",
                context,
            ],
            resources["bootstrap_build_timeout_seconds"],
        )
        self.report["bootstrap_build_exit"] = built.returncode
        if built.returncode:
            self.report["stage"] = "bootstrap_build_failed"
            return
        require(
            time.time() + resources["setup_timeout_seconds"] + 300 < deadline,
            "Insufficient setup reserve",
        )
        self.report["stage"] = "controller_setup"
        self.save()
        setup = self.logged(
            "setup.log",
            [self.controller, "bash", "/work/setup_controller.sh"],
            resources["setup_timeout_seconds"],
        )
        self.report["setup_exit"] = setup.returncode
        require(setup.returncode == 0, "Controller setup failed")
        self.report["stage"] = "task_image_build"
        self.save()
        built = self.logged(
            "task-build.log",
            [
                "-e",
                "CONTEXT_DIR=" + context,
                self.controller,
                "python",
                "-m",
                "biotasks.validation.worker.docker_bridge",
                "compose",
                "build",
            ],
            resources["bootstrap_build_timeout_seconds"],
        )
        self.report["task_build_exit"] = built.returncode
        if built.returncode:
            self.report["stage"] = "task_build_failed"
            return
        require(
            time.time() + 2 * resources["wrapper_seconds"] + 300 < deadline,
            "Insufficient full native control reserve",
        )
        self.report.update(stage="controls_running", controls_started=True)
        self.save()
        executed = self.logged(
            "controls-driver.log",
            [
                "-e",
                "PATH=/work/harbor-bin:/work/harbor066/bin:/usr/local/bin:/usr/bin:/bin",
                "-e",
                "BIOTASKS_DEADLINE=" + str(deadline),
                self.controller,
                "python",
                "-m",
                "biotasks.validation.worker.controls",
            ],
            2 * resources["wrapper_seconds"] + 60,
        )
        self.report.update(stage="controls_returned", controls_exit=executed.returncode)

    def stop_execution(self) -> dict[str, Any]:
        """Stop exact owner containers, preserving filesystems for archival."""
        seen = set()
        for _ in range(3):
            ids = set()
            for label in ("biotasks.run=", "biotasks.controller="):
                ids.update(
                    self.docker("ps", "-q", "--filter", "label=" + label + self.run).stdout.split()
                )
            if not ids:
                return {"verified_stopped": True, "stopped_containers": sorted(seen)}
            seen.update(ids)
            self.docker("stop", "--time", "10", *sorted(ids), timeout=60, check=False)
        remaining = []
        for label in ("biotasks.run=", "biotasks.controller="):
            remaining += self.docker(
                "ps", "-q", "--filter", "label=" + label + self.run
            ).stdout.split()
        return {
            "verified_stopped": not remaining,
            "remaining_running": remaining,
            "stopped_containers": sorted(seen),
        }

    def stop_only(self) -> None:
        self.tools_ready()
        require(
            self.config["target_worker_id"] == os.environ["IRIS_WORKER_ID"], "Stop worker mismatch"
        )
        self.report["stop"] = self.stop_execution()
        self.report["stage"] = "stop_only_returned"
        require(self.report["stop"]["verified_stopped"], "Owned execution remains running")

    def finish(self) -> None:
        if (self.tools / "docker").exists() and self.report["creation_started"]:
            try:
                self.report["stop"] = self.stop_execution()
                require(
                    self.report["stop"]["verified_stopped"],
                    "Cannot seal while execution is running",
                )
                if self.report["controller_created"]:
                    # Restart only the trusted sleep process after cancelling all
                    # exec sessions. This does not rerun the task or controls.
                    self.docker("start", self.controller)
                    self.docker(
                        "exec",
                        self.controller,
                        "tar",
                        "-czf",
                        "/work/evidence/control-artifacts.tar.gz",
                        "-C",
                        "/work",
                        "outputs",
                        "infra",
                        timeout=120,
                    )
                    # Jobs use the host mountpoint, which aliases this same volume.
                    jobs = self.docker(
                        "exec", self.controller, "test", "-d", "/work/jobs", check=False
                    )
                    if jobs.returncode == 0:
                        self.docker(
                            "exec",
                            self.controller,
                            "tar",
                            "-czf",
                            "/work/evidence/control-artifacts.tar.gz",
                            "-C",
                            "/work",
                            "outputs",
                            "infra",
                            "jobs",
                            timeout=120,
                        )
                    self.docker(
                        "cp", self.controller + ":/work/evidence/.", str(self.out), timeout=120
                    )
                    self.report["archive_copied"] = True
            except Exception as error:
                self.report["archive_error"] = type(error).__name__ + ": " + str(error)[:400]
            finally:
                try:
                    self.report["stop"] = self.stop_execution()
                except Exception as error:
                    self.report["stop"] = {"verified_stopped": False, "error": str(error)[:400]}
            self.report["retained_resources"] = {
                "controller": self.controller,
                "volume": self.volume,
                "reason": "Stopped execution; retain until controller verifies durable archive/readback",
            }
        elif self.config["operation"] == "execute" and self.report.get("configuration_verified"):
            self.report["cleanup"] = {
                "verified_no_creation": True,
                "reason": "Bound code stopped before first creation request",
            }
        if self.tools.exists():
            shutil.rmtree(self.tools)
        self.report["finished"] = time.time()
        self.report["output_sha256"] = {
            p.relative_to(self.out).as_posix(): sha(p)
            for p in self.out.rglob("*")
            if p.is_file() and p.name not in ("result.json", "work-state.json")
        }
        checkpoint(self.out / "result.json", self.report)

    def cleanup(self) -> None:
        self.tools_ready()
        require(
            self.config.get("archival_verified") is True, "Archive readback must precede cleanup"
        )
        require(
            self.config["target_worker_id"] == os.environ["IRIS_WORKER_ID"],
            "Cleanup worker mismatch",
        )
        expected = self.config.get("control_archive_sha256")
        if expected:
            inspected = self.docker("inspect", self.controller, check=False)
            if inspected.returncode == 0:
                item = json.loads(inspected.stdout)[0]
                require(
                    item["Config"]["Labels"].get("biotasks.controller") == self.run,
                    "Controller ownership changed",
                )
                source = self.root / "retained-control-artifacts.tar.gz"
                self.docker(
                    "cp",
                    self.controller + ":/work/evidence/control-artifacts.tar.gz",
                    str(source),
                    timeout=120,
                )
                require(sha(source) == expected, "Retained evidence differs; preserve volume")
            else:
                volume = self.docker("volume", "inspect", self.volume, check=False)
                require(
                    volume.returncode != 0,
                    "Controller missing while volume remains; preserve for salvage",
                )
        from biotasks.validation.worker.cleanup import cleanup

        self.report["cleanup"] = cleanup(
            self.tools / "docker", self.run, self.config.get("protected_base")
        )
        self.report["stage"] = "cleanup_returned"
        require(self.report["cleanup"]["verified_empty"], "Owned resources remain")


def main() -> None:
    root = Path(os.environ["IRIS_WORKDIR"])
    out = Path(os.environ["IRIS_OUTPUT_DIR"])
    out.mkdir(parents=True, exist_ok=True)
    runner = None
    try:
        config = json.loads((root / "family.json").read_text())
        runner = Supervisor(root, out, config)
        runner.validate()

        def interrupted(signum: int, frame: Any) -> None:
            raise RuntimeError("Worker interrupted: " + str(signum))

        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        if config["operation"] == "cleanup":
            runner.cleanup()
        elif config["operation"] == "stop":
            runner.stop_only()
        else:
            require(config["operation"] == "execute", "Unknown worker operation")
            runner.work()
    except Exception as error:
        if runner is not None:
            runner.report.update(error_type=type(error).__name__, error=str(error)[:600])
        else:
            checkpoint(
                out / "startup-failure.json",
                {
                    "stage": "startup_failure",
                    "error_type": type(error).__name__,
                    "error": str(error)[:600],
                    "creation_started": False,
                },
            )
    finally:
        if runner is not None:
            runner.finish()


if __name__ == "__main__":
    main()
