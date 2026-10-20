"""Bounded remote installation check. No credentials, login, or LLM calls.

Runs only on the approved reserved TRC worker. All heavy installation occurs
inside a one-CPU, four-GiB container. Preserve native installation failures.
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
RUN = "biotasks25-install-001"
REV = "27d04ee8203cd5b2f20c3997d13836e5f5b64238"
SOURCE_SHA = "9c09729e909766366d8761e71a3585a64f656d1d3c64909b0656a0af28b402e9"
TOOLS = Path("/opt/biotasks25-install-tools")
DOCKER = TOOLS / "docker"


def command(args, **kwargs):
    return subprocess.run(args, check=True, timeout=120, **kwargs)


def docker(*args, **kwargs):
    return command([str(DOCKER), *args], **kwargs)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TOOLS.mkdir(parents=True, exist_ok=True)
    report = {"run_id": RUN, "started": time.time(), "model_calls": 0,
              "upstream_revision": REV, "source_modifications": []}
    container = RUN + "-controller"
    created = False
    try:
        archive = TOOLS / "docker.tgz"
        with urllib.request.urlopen(
            "https://download.docker.com/linux/static/stable/x86_64/docker-23.0.6.tgz",
            timeout=60,
        ) as response, archive.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        report["docker_archive_sha256"] = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
        with tarfile.open(archive) as bundle:
            DOCKER.write_bytes(bundle.extractfile("docker/docker").read())
        DOCKER.chmod(0o755)
        report["docker_version"] = docker("version", "--format", "{{json .}}", capture_output=True, text=True).stdout
        docker("network", "inspect", "iris-egress", stdout=subprocess.DEVNULL)
        docker("pull", "python:3.12-slim")
        report["controller_image"] = docker("image", "inspect", "python:3.12-slim", "--format", "{{.Id}}", capture_output=True, text=True).stdout.strip()
        docker("create", "--name", container, "--cpus=1", "--memory=4g", "--memory-swap=4g",
               "--network=iris-egress", "--label", f"biotasks.controller={RUN}",
               "-v", "/var/run/docker.sock:/var/run/docker.sock", "-w", "/work",
               report["controller_image"], "sleep", "infinity", stdout=subprocess.DEVNULL)
        created = True
        docker("start", container, stdout=subprocess.DEVNULL)
        docker("exec", container, "mkdir", "-p", "/work/inputs", "/work/bin", "/work/real")
        docker("cp", str(DOCKER), f"{container}:/work/real/docker")
        docker("cp", str(ROOT / "docker_resource_wrapper.py"), f"{container}:/work/bin/docker")
        docker("cp", str(ROOT / "proposed-configs") + "/.", f"{container}:/work/inputs")
        # This setup installs the upstream controller, never target-repository dependencies.
        setup = '''set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git ca-certificates curl
python -m pip install --no-cache-dir uv==0.11.31
curl --fail --location --max-time 120 https://github.com/huggingface/Repo2RLEnv/archive/REV.tar.gz -o /work/source.tar.gz
echo 'SOURCE_SHA  /work/source.tar.gz' | sha256sum -c -
mkdir /work/upstream
tar -xzf /work/source.tar.gz -C /work/upstream --strip-components=1
cd /work/upstream
uv sync --frozen --no-dev --extra harbor
curl --fail --location --max-time 120 https://github.com/cli/cli/releases/download/v2.97.0/gh_2.97.0_linux_amd64.tar.gz -o /work/gh.tar.gz
tar -xzf /work/gh.tar.gz -C /work
cp /work/gh_2.97.0_linux_amd64/bin/gh /work/bin/gh
chmod +x /work/bin/docker
export PATH=/work/bin:/work/upstream/.venv/bin:$PATH
export BIOTASKS_REAL_DOCKER=/work/real/docker BIOTASKS_RUN_ID=biotasks25-install-001 BIOTASKS_DOCKER_GUARD_LOCK=/work/docker.lock
repo2rlenv --version
gh --version
harbor --version
python -V
/work/upstream/.venv/bin/python -c 'from pathlib import Path; from repo2rlenv.config import load_generation_input; [load_generation_input(p) for p in Path("/work/inputs").glob("*.json")]; print("All five native configurations validated")'
docker run -d --name biotasks25-install-001-slot1 python:3.12-slim sleep 120
docker run -d --name biotasks25-install-001-slot2 python:3.12-slim sleep 120
if docker run -d --name biotasks25-install-001-slot3 python:3.12-slim sleep 120; then exit 91; fi
docker inspect biotasks25-install-001-slot1 biotasks25-install-001-slot2 --format '{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}} {{.HostConfig.MemorySwap}} {{.HostConfig.NetworkMode}}'
docker rm -f biotasks25-install-001-slot1 biotasks25-install-001-slot2
'''.replace("SOURCE_SHA", SOURCE_SHA).replace("REV", REV)
        (TOOLS / "setup.sh").write_text(setup)
        docker("cp", str(TOOLS / "setup.sh"), f"{container}:/work/setup.sh")
        with (OUT / "installation.log").open("w") as log:
            result = subprocess.run([str(DOCKER), "exec", container, "bash", "/work/setup.sh"],
                                    stdout=log, stderr=subprocess.STDOUT, timeout=1500)
        report["installation_exit_code"] = result.returncode
        print("BIOTASKS25_INSTALL " + json.dumps({"exit_code": result.returncode}), flush=True)
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if DOCKER.exists():
            for label in [f"biotasks.run={RUN}", f"biotasks.controller={RUN}"]:
                ids = docker("ps", "-aq", "--filter", f"label={label}", capture_output=True, text=True).stdout.split()
                if ids:
                    docker("rm", "-f", *ids, stdout=subprocess.DEVNULL)
            report["remaining_containers"] = docker("ps", "-aq", "--filter", f"label=biotasks.run={RUN}", capture_output=True, text=True).stdout.split()
            report["remaining_controllers"] = docker("ps", "-aq", "--filter", f"label=biotasks.controller={RUN}", capture_output=True, text=True).stdout.split()
        report["finished"] = time.time()
        (OUT / "installation-result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
