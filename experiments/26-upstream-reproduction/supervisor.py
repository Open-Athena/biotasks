"""Bounded phase controller on reserved TRC; no repository/environment repair."""

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
RUN = os.environ["BIOTASKS_RUN_ID"]
PHASE = os.environ["BIOTASKS_PHASE"]
TOOLS = Path("/opt/biotasks26-tools")
DOCKER = TOOLS / "docker"
CONTROLLER = RUN + "-controller"
VOLUME = RUN + "-work"


def docker(*args, **kwargs):
    return subprocess.run([str(DOCKER), *args], check=True, timeout=kwargs.pop("timeout", 120), **kwargs)


def fetch(url, target, expected):
    with urllib.request.urlopen(url, timeout=120) as source, target.open("wb") as output:
        while chunk := source.read(1024 * 1024):
            output.write(chunk)
    with target.open("rb") as handle:
        assert hashlib.file_digest(handle, "sha256").hexdigest() == expected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TOOLS.mkdir(exist_ok=True)
    pins = json.loads((ROOT / "pins.json").read_text())
    runtime = pins["replay_timeout_seconds" if PHASE == "replay" else "generation_timeout_seconds"]
    deadline = time.monotonic() + runtime - 180
    report = {"run_id": RUN, "phase": PHASE, "started": time.time(), "phase_started": False}
    created = volume_created = False
    try:
        fetch(pins["docker_url"], TOOLS / "docker.tgz", pins["docker_sha256"])
        with tarfile.open(TOOLS / "docker.tgz") as archive:
            DOCKER.write_bytes(archive.extractfile("docker/docker").read())
        DOCKER.chmod(0o755)
        fetch(pins["compose_url"], TOOLS / "docker-compose", pins["compose_sha256"])
        (TOOLS / "docker-compose").chmod(0o755)
        daemon = json.loads(docker("info", "--format", "{{json .}}", capture_output=True, text=True).stdout)
        assert daemon["MemoryLimit"] and daemon["CpuCfsQuota"] and daemon["CpuCfsPeriod"]
        report["daemon"] = {key: daemon[key] for key in ["ServerVersion", "MemoryLimit", "SwapLimit", "CpuCfsQuota", "CpuCfsPeriod"]}
        assert subprocess.run([str(DOCKER), "volume", "inspect", VOLUME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
        docker("volume", "create", "--label", "biotasks.run=" + RUN, VOLUME, stdout=subprocess.DEVNULL)
        volume_created = True
        mountpoint = json.loads(docker("volume", "inspect", VOLUME, capture_output=True, text=True).stdout)[0]["Mountpoint"]
        report["shared_volume"] = {"name": VOLUME, "same_absolute_path": True}
        docker("pull", pins["controller_image"], timeout=240, stdout=subprocess.DEVNULL)
        args = ["create", "--name", CONTROLLER, "--cpus=1", "--memory=4g", "--memory-swap=4g",
                "--network=iris-egress", "--label", "biotasks.controller=" + RUN,
                "-v", "/var/run/docker.sock:/var/run/docker.sock", "-v", VOLUME + ":/work",
                "-v", VOLUME + ":" + mountpoint, "-w", "/work",
                "-e", "BIOTASKS_RUN_ID=" + RUN, "-e", "BIOTASKS_PHASE=" + PHASE,
                "-e", "BIOTASKS_SHARED_ROOT=" + mountpoint,
                "-e", "BIOTASKS_REAL_DOCKER=/work/real/docker",
                "-e", "BIOTASKS_DOCKER_GUARD_LOCK=/work/native-docker.lock",
                "-e", "DOCKER_CONFIG=/work/docker-config"]
        if PHASE == "generate":
            args += ["-e", "GH_TOKEN", "-e", "OPENROUTER_API_KEY"]
        args += [pins["controller_image"], "sleep", "infinity"]
        docker(*args, stdout=subprocess.DEVNULL); created = True
        docker("start", CONTROLLER, stdout=subprocess.DEVNULL)
        docker("exec", CONTROLLER, "mkdir", "-p", "/work/bin", "/work/real", "/work/evidence",
               "/work/inputs", "/work/bootstrap", "/work/outputs", "/work/native-bin", "/work/harbor-bin",
               "/work/docker-config/cli-plugins", "/work/jobs", "/work/infra")
        docker("cp", str(ROOT) + "/.", CONTROLLER + ":/work/")
        for source, destination in [(DOCKER, "/work/real/docker"), (TOOLS / "docker-compose", "/work/docker-config/cli-plugins/docker-compose"),
                                    (ROOT / "native_docker.py", "/work/native-bin/docker"),
                                    (ROOT / "harbor_docker.py", "/work/harbor-bin/docker")]:
            docker("cp", str(source), CONTROLLER + ":" + destination)
        docker("cp", str(ROOT / "native-configs") + "/.", CONTROLLER + ":/work/inputs")
        docker("exec", CONTROLLER, "chmod", "+x", "/work/native-bin/docker", "/work/harbor-bin/docker")
        with (OUT / "installation.log").open("w") as log:
            docker("exec", CONTROLLER, "bash", "/work/setup_controller.sh", timeout=1500, stdout=log, stderr=subprocess.STDOUT)
        print("CONTROLLER_READY " + PHASE, flush=True)
        report["phase_started"] = True
        command = ["/usr/local/bin/python", "/work/run_generation.py"] if PHASE == "generate" else [
            "/usr/local/bin/python", "/work/run_controls.py", "--tasks", "/work/published", "--prefix", "published"]
        seconds = max(1, int(deadline - time.monotonic()))
        result = subprocess.run([str(DOCKER), "exec", CONTROLLER, "timeout", "--kill-after=15s", str(seconds), *command], timeout=seconds + 30)
        report["phase_exit_code"] = result.returncode
    except Exception as error:
        report["error_type"] = type(error).__name__
        print("SUPERVISOR_ERROR " + type(error).__name__, flush=True)
        raise
    finally:
        try:
            cleanup(report, created, volume_created)
        except Exception as error:
            report["cleanup_error"] = type(error).__name__
        report["finished"] = time.time()
        (OUT / "supervisor-result.json").write_text(json.dumps(report, indent=2) + "\n")


def cleanup(report, created, volume_created):
    if not DOCKER.exists():
        report["docker_not_installed"] = True
        return
    if created:
        for label in ["biotasks.run=" + RUN]:
            ids = docker("ps", "-aq", "--filter", "label=" + label, capture_output=True, text=True).stdout.split()
            if ids:
                docker("rm", "-f", *ids, stdout=subprocess.DEVNULL)
        try:
            docker("exec", CONTROLLER, "tar", "-czf", "/work/evidence/phase-artifacts.tar.gz", "-C", "/work",
                   "published", "bootstrap", "outputs", "jobs", "infra", timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as error:
            report["archive_error"] = type(error).__name__
        docker("cp", CONTROLLER + ":/work/evidence/.", str(OUT))
        docker("rm", "-f", CONTROLLER, stdout=subprocess.DEVNULL)
        images = docker("image", "ls", "-aq", "--filter", "label=biotasks.run=" + RUN, capture_output=True, text=True).stdout.split()
        if images:
            docker("image", "rm", "-f", *sorted(set(images)), stdout=subprocess.DEVNULL)
    if volume_created:
        docker("volume", "rm", VOLUME, stdout=subprocess.DEVNULL)
    report["remaining_containers"] = docker("ps", "-aq", "--filter", "label=biotasks.run=" + RUN, capture_output=True, text=True).stdout.split()
    report["remaining_controllers"] = docker("ps", "-aq", "--filter", "label=biotasks.controller=" + RUN, capture_output=True, text=True).stdout.split()
    report["remaining_images"] = docker("image", "ls", "-aq", "--filter", "label=biotasks.run=" + RUN, capture_output=True, text=True).stdout.split()
    report["remaining_volumes"] = docker("volume", "ls", "-q", "--filter", "label=biotasks.run=" + RUN, capture_output=True, text=True).stdout.split()

if __name__ == "__main__":
    main()
