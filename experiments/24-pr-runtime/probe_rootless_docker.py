"""Bounded rootless Docker smoke test entirely inside an Iris SANDBOX guest."""

import hashlib
import json
import os
import pwd
import signal
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

VERSION = "27.5.1"  # gVisor documents Docker 27 compatibility.
USER = "bt24rootless"
UID = 24024
GUEST_HOME = Path("/home/bt24rootless")
OUTPUT = Path(os.environ["IRIS_OUTPUT_DIR"])
REPORT = {"model_calls": 0, "target_code_executed": False, "steps": [], "downloads": []}


def run(label, arguments, timeout=60, check=True):
    started = time.monotonic()
    with (OUTPUT / f"{label}.log").open("w") as log:
        process = subprocess.Popen(
            arguments, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            code = 124
    REPORT["steps"].append({
        "name": label, "exit_code": code, "elapsed_seconds": round(time.monotonic() - started, 3),
    })
    if check and code:
        raise RuntimeError(f"{label}: exit {code}")
    return code


def user_command(*arguments):
    return [
        "runuser", "-u", USER, "--", "env", "-i",
        f"HOME={GUEST_HOME}", f"USER={USER}", f"PATH={GUEST_HOME}/bin:/usr/bin:/bin",
        f"XDG_RUNTIME_DIR={GUEST_HOME}/run", f"DOCKER_HOST=unix://{GUEST_HOME}/run/docker.sock",
        "DOCKER_BUILDKIT=0", *arguments,
    ]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    created_user = False
    daemon = None
    daemon_log = None
    try:
        assert not Path("/var/run/docker.sock").exists(), "Refuse host Docker socket"
        assert os.getuid() == 0, "Requires guest root for guest package installation only"
        assert not any(p.pw_uid == UID or p.pw_name == USER for p in pwd.getpwall())
        run("package-index", ["apt-get", "update"], timeout=90)
        run("install-guest-prerequisites", [
            "apt-get", "install", "-y", "--no-install-recommends",
            "uidmap", "slirp4netns", "dbus-user-session", "ca-certificates",
            "procps", "iptables",
        ], timeout=120)
        run("create-guest-user", ["useradd", "-m", "-u", str(UID), "-s", "/bin/sh", USER])
        created_user = True
        for file in ("/etc/subuid", "/etc/subgid"):
            assert any(
                line.startswith(USER + ":") and int(line.split(":")[2]) >= 65536
                for line in Path(file).read_text().splitlines()
            ), "Missing guest subordinate ID allocation"
        binary_dir = GUEST_HOME / "bin"
        binary_dir.mkdir()
        (GUEST_HOME / "run").mkdir(mode=0o700)
        for package in ("docker", "docker-rootless-extras"):
            url = f"https://download.docker.com/linux/static/stable/x86_64/{package}-{VERSION}.tgz"
            archive = Path("/tmp") / f"{package}-{VERSION}.tgz"
            digest = hashlib.sha256()
            size = 0
            with urllib.request.urlopen(url, timeout=30) as response, archive.open("wb") as target:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    assert size <= 150 * 1024**2
                    digest.update(chunk)
                    target.write(chunk)
            REPORT["downloads"].append({
                "url": url, "sha256": digest.hexdigest(), "bytes": size,
                "digest_kind": "observed download digest, not an independently supplied signature",
            })
            with tarfile.open(archive) as bundle:
                for member in bundle:
                    if member.isfile():
                        assert member.size < 200 * 1024**2
                        destination = binary_dir / Path(member.name).name
                        with bundle.extractfile(member) as src, destination.open("wb") as dst:
                            while chunk := src.read(1024 * 1024):
                                dst.write(chunk)
                        destination.chmod(0o755)
            archive.unlink()
        run("own-guest-home", ["chown", "-R", f"{UID}:{UID}", str(GUEST_HOME)])
        run("client-version", user_command("docker", "--version"))
        daemon_log = (OUTPUT / "daemon.log").open("w")
        daemon = subprocess.Popen(
            user_command(
                "dockerd-rootless.sh", "--storage-driver=vfs",
                "--iptables=false", "--ip6tables=false",
            ),
            stdout=daemon_log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        socket = GUEST_HOME / "run/docker.sock"
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not socket.exists() and daemon.poll() is None:
            time.sleep(0.5)  # Remote guest startup check, bounded to 30 seconds.
        assert socket.exists(), "Rootless daemon did not create its guest-local socket"
        run("daemon-info", user_command("docker", "info", "--format", "{{json .}}"))
        info = json.loads((OUTPUT / "daemon-info.log").read_text())
        assert any("rootless" in entry for entry in info["SecurityOptions"])
        REPORT["rootless_confirmed"] = True
        context = GUEST_HOME / "smoke"
        context.mkdir()
        (context / "Dockerfile").write_text(
            "FROM alpine:3.22\nRUN printf 'biotasks24-rootless-ok\\n' > /probe.txt\n"
            'CMD ["cat", "/probe.txt"]\n'
        )
        run("own-smoke-context", ["chown", "-R", f"{UID}:{UID}", str(context)])
        run("build", user_command("docker", "build", "-t", "biotasks24-rootless-smoke", str(context)), 120)
        run("image-identity", user_command("docker", "image", "inspect", "biotasks24-rootless-smoke"))
        run("container-run", user_command("docker", "run", "--rm", "biotasks24-rootless-smoke"), 30)
        assert (OUTPUT / "container-run.log").read_text().strip() == "biotasks24-rootless-ok"
        REPORT["disposition"] = "rootless_build_and_run_succeeded"
    except Exception as exc:
        REPORT["disposition"] = "probe_failed"
        REPORT["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if created_user:
            run("stop-owned-user-processes", ["pkill", "-TERM", "-u", str(UID)], check=False)
            time.sleep(1)
            run("kill-remaining-owned-user-processes", ["pkill", "-KILL", "-u", str(UID)], check=False)
            remaining = run("remaining-owned-processes", ["pgrep", "-u", str(UID)], check=False)
            REPORT["owned_process_cleanup_verified"] = remaining == 1
        if daemon is not None:
            try:
                daemon.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(daemon.pid, signal.SIGKILL)
                daemon.wait()
        if daemon_log is not None:
            daemon_log.close()
        REPORT["elapsed_seconds"] = round(time.monotonic() - started, 3)
        REPORT["docker_version"] = VERSION
        REPORT["container_profile"] = "SANDBOX"
        raw = (json.dumps(REPORT, indent=2, sort_keys=True) + "\n").encode()
        (OUTPUT / "rootless-probe.json").write_bytes(raw)
        print("BIOTASKS24_ROOTLESS " + json.dumps(REPORT, sort_keys=True), flush=True)
        print("BIOTASKS24_ROOTLESS_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
