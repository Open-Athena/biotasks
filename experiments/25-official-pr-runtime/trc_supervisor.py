"""Persistent bounded controller; native execution requires an explicit go file.

Only authenticated Iris task exec may stage the checkpointed native command.
No token values belong in commands, logs, files, or result artifacts.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ["IRIS_OUTPUT_DIR"])
RUN = os.environ["BIOTASKS_INSTALL_RUN_ID"]
TOOLS = Path("/opt/biotasks25-tools")
DOCKER = TOOLS / "docker"
CONTROLLER = RUN + "-controller"


def docker(*args, timeout=120, **kwargs):
    return subprocess.run([str(DOCKER), *args], timeout=timeout, check=True, **kwargs)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TOOLS.mkdir(parents=True, exist_ok=True)
    report = {"run_id": RUN, "started": time.time(), "native_started": False}
    created = False
    try:
        archive = TOOLS / "docker.tgz"
        with urllib.request.urlopen("https://download.docker.com/linux/static/stable/x86_64/docker-23.0.6.tgz", timeout=60) as source, archive.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        with archive.open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == "544262f4a3621222afb79960bfad4d486935dab80893478b5cc9cf8ebaf409ae"
        with tarfile.open(archive) as bundle:
            DOCKER.write_bytes(bundle.extractfile("docker/docker").read())
        DOCKER.chmod(0o755)
        image = "python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
        docker("pull", image)
        docker("create", "--name", CONTROLLER, "--cpus=1", "--memory=4g", "--memory-swap=4g",
               "--network=iris-egress", "--label", f"biotasks.controller={RUN}",
               "-v", "/var/run/docker.sock:/var/run/docker.sock", "-w", "/work",
               "-e", "OPENROUTER_API_KEY", "-e", f"BIOTASKS_INSTALL_RUN_ID={RUN}",
               "-e", f"BIOTASKS_RUN_ID={RUN}", "-e", "BIOTASKS_REAL_DOCKER=/work/real/docker",
               "-e", "BIOTASKS_DOCKER_GUARD_LOCK=/work/docker.lock",
               "-e", "PATH=/work/bin:/work/upstream/.venv/bin:/usr/local/bin:/usr/bin:/bin",
               image, "sleep", "infinity", stdout=subprocess.DEVNULL)
        created = True
        docker("start", CONTROLLER, stdout=subprocess.DEVNULL)
        docker("exec", CONTROLLER, "mkdir", "-p", "/work/inputs", "/work/bin", "/work/real", "/work/evidence")
        for path, destination in [(DOCKER, "/work/real/docker"), (ROOT / "docker_resource_wrapper.py", "/work/bin/docker"),
                                  (ROOT / "install_controller.sh", "/work/install.sh")]:
            docker("cp", str(path), f"{CONTROLLER}:{destination}")
        docker("cp", str(ROOT / "proposed-configs") + "/.", f"{CONTROLLER}:/work/inputs")
        with (OUT / "installation.log").open("w") as log:
            docker("exec", CONTROLLER, "bash", "/work/install.sh", timeout=1500, stdout=log, stderr=subprocess.STDOUT)
        print("BIOTASKS25_AUTH_START", flush=True)
        docker("exec", "-i", CONTROLLER, "gh", "auth", "login", "--hostname", "github.com",
               "--git-protocol", "https", "--web", timeout=900, input="\n", text=True)
        print("BIOTASKS25_AUTH_READY", flush=True)
        report["authenticated"] = True
        # No native model call can happen before the checkpointed command is
        # explicitly staged and enabled through the supported Iris exec API.
        wait_until = time.monotonic() + 3600
        while time.monotonic() < wait_until:
            ready = subprocess.run([str(DOCKER), "exec", CONTROLLER, "test", "-f", "/work/go"], timeout=15).returncode == 0
            if ready:
                report["native_started"] = True
                docker("exec", CONTROLLER, "bash", "/work/run-official.sh", timeout=27000)
                break
            time.sleep(10)
        else:
            report["stop_reason"] = "authenticated_but_no_native_command_staged_within_one_hour"
    except Exception as error:
        # Do not serialize process environment or output containing credentials.
        report["error_type"] = type(error).__name__
        print("BIOTASKS25_SUPERVISOR_ERROR " + type(error).__name__, flush=True)
        raise
    finally:
        if created:
            try:
                docker("cp", f"{CONTROLLER}:/work/evidence/.", str(OUT))
            except Exception as error:
                report["artifact_copy_error"] = type(error).__name__
            for label in [f"biotasks.run={RUN}", f"biotasks.controller={RUN}"]:
                ids = docker("ps", "-aq", "--filter", f"label={label}", capture_output=True, text=True).stdout.split()
                if ids:
                    docker("rm", "-f", *ids, stdout=subprocess.DEVNULL)
            images = docker("image", "ls", "-aq", "--filter", f"label=biotasks.run={RUN}", capture_output=True, text=True).stdout.split()
            if images:
                docker("image", "rm", "-f", *sorted(set(images)), stdout=subprocess.DEVNULL)
            report["remaining_containers"] = docker("ps", "-aq", "--filter", f"label=biotasks.run={RUN}", capture_output=True, text=True).stdout.split()
            report["remaining_controllers"] = docker("ps", "-aq", "--filter", f"label=biotasks.controller={RUN}", capture_output=True, text=True).stdout.split()
            report["remaining_images"] = docker("image", "ls", "-aq", "--filter", f"label=biotasks.run={RUN}", capture_output=True, text=True).stdout.split()
        report["finished"] = time.time()
        (OUT / "supervisor-result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
