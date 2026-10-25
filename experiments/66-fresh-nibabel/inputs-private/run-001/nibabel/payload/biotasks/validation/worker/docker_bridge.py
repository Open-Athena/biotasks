#!/usr/bin/env python3
"""Generic bounded Docker/Compose transport; original tasks stay byte-identical."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from biotasks.validation.files import require
from biotasks.validation.recipes import tagged_recipe
from biotasks.validation.worker.common import content_sha, native_prefix


def append(path, row):
    with Path(path).open("a") as handle:
        handle.write(json.dumps(row) + "\n")


def build_image(real, owner, context, raw, kind, task=None):
    digest = content_sha(raw)
    require(kind == "bootstrap" or task is not None, "Task build needs an identity")
    tag = (
        owner
        + "-"
        + ("bootstrap" if kind == "bootstrap" else str(task).lower())
        + ":"
        + digest[:12]
    )
    found = subprocess.run([real, "image", "inspect", tag], capture_output=True, text=True)
    started = time.time()
    row = dict(kind=kind, task=task, image=tag, dockerfile_sha256=digest, started=started)
    history = Path("/work/evidence/bounded-builds.jsonl")
    if kind == "task" and history.exists():
        previous = [json.loads(line) for line in history.read_text().splitlines()]
        failed = [
            r
            for r in previous
            if r["kind"] == "task" and r["dockerfile_sha256"] == digest and r["exit_code"] != 0
        ]
        if failed:
            row.update(
                exit_code=failed[0]["exit_code"],
                finished=time.time(),
                blocked_by_prior_build_failure=True,
                source_failure_started=failed[0]["started"],
            )
            append(history, row)
            return row
    if found.returncode == 0:
        image = json.loads(found.stdout)[0]
        require(
            image["Config"]["Labels"]["biotasks.run"] == owner,
            "Worker contract failed at worker/docker_bridge.py:53",
        )
        row.update(cached=True, exit_code=0, image_id=image["Id"], finished=time.time())
    else:
        require("No such image" in found.stderr, "Do not mistake daemon errors for image absence")
        effective = tagged_recipe(raw, owner)
        recipe = Path("/work/infra") / (digest + ".Dockerfile")
        recipe.write_bytes(effective)
        command = [
            real,
            "build",
            "--force-rm",
            "--cpu-period=100000",
            "--cpu-quota=150000",
            "--memory=6g",
            "--memory-swap=6g",
            "--network=" + os.environ["BIOTASKS_WORKER_NETWORK"],
            "--label",
            "biotasks.run=" + owner,
            "--tag",
            tag,
            "-f",
            str(recipe),
            str(context),
        ]
        append("/work/evidence/build-starts.jsonl", row)
        result = subprocess.run(command, env=dict(os.environ, DOCKER_BUILDKIT="0"), check=False)
        row.update(
            exit_code=result.returncode,
            finished=time.time(),
            ownership_label_only=True,
            effective_dockerfile_sha256=content_sha(effective),
            cpu_limit=1.5,
            memory_bytes=6 * 1024**3,
        )
        if result.returncode == 0:
            row["image_id"] = json.loads(subprocess.check_output([real, "image", "inspect", tag]))[
                0
            ]["Id"]
    append("/work/evidence/bounded-builds.jsonl", row)
    return row


def capture_identity(real, owner, image, task, digest):
    inspected = json.loads(subprocess.check_output([real, "image", "inspect", image]))[0]
    require(
        inspected["Config"]["Labels"]["biotasks.run"] == owner,
        "Worker contract failed at worker/docker_bridge.py:97",
    )
    image_id = inspected["Id"]
    script = """import json,sys,platform,subprocess,shutil
tools={}
for name in ('python3','node','npm','pnpm'):
    path=shutil.which(name);row={'path':path}
    if path and name!='pnpm':
        result=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=15)
        row.update(exit_code=result.returncode,stdout=result.stdout.strip(),stderr=result.stderr.strip())
    tools[name]=row
packages=subprocess.run([sys.executable,'-m','pip','--disable-pip-version-check','freeze'],capture_output=True,text=True,timeout=30)
print(json.dumps(dict(git_head=subprocess.check_output(['git','-C','/workspace','rev-parse','HEAD'],text=True).strip(),python=sys.version,platform=platform.platform(),tools=tools,python_packages=packages.stdout.splitlines() if packages.returncode==0 else None)))
"""
    result = subprocess.run(
        [
            real,
            "run",
            "--rm",
            "--name",
            owner + "-identity",
            "--cpus=1",
            "--memory=256m",
            "--memory-swap=256m",
            "--network=none",
            "--label",
            "biotasks.run=" + owner,
            "--entrypoint",
            "python3",
            image_id,
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    record = json.loads(result.stdout)
    record.update(
        task=task["task"],
        image=image,
        image_id=image_id,
        dockerfile_sha256=digest,
        captured=time.time(),
    )
    append("/work/evidence/image-identities.jsonl", record)
    require(
        record["git_head"] == task["base_commit"],
        "Worker contract failed at worker/docker_bridge.py:143",
    )
    return image_id


def main():
    real = os.environ["BIOTASKS_REAL_DOCKER"]
    owner = os.environ["BIOTASKS_RUN_ID"]
    family = json.loads(Path("/work/family.json").read_text())
    require(family["run_id"] == owner, "Worker contract failed at worker/docker_bridge.py:151")
    args = sys.argv[1:]
    if args and args[0] == "prefix-build":
        require(len(args) == 2, "Worker contract failed at worker/docker_bridge.py:154")
        context = Path(args[1]).resolve()
        require(
            context.is_relative_to(Path("/work/outputs")) and context.name == "environment",
            "Worker contract failed at worker/docker_bridge.py:156",
        )
        raw = Path("/work/bootstrap-prefix.Dockerfile").read_bytes()
        require(
            content_sha(raw) == family["bootstrap_prefix_sha256"],
            "Worker contract failed at worker/docker_bridge.py:158",
        )
        require(
            native_prefix((context / "Dockerfile").read_bytes())[0] == raw,
            "Worker contract failed at worker/docker_bridge.py:159",
        )
        Path("/work/infra").mkdir(exist_ok=True)
        return build_image(real, owner, context, raw, "bootstrap")["exit_code"]
    if not args or args[0] != "compose":
        require(
            not any(v in {"run", "create", "build"} for v in args[:2]), "Use bounded execution path"
        )
        os.execv(real, [real, *args])
    if args[1:] == ["version"]:
        os.execv(real, [real, *args])
    context = Path(os.environ["CONTEXT_DIR"]).resolve()
    require(
        context.is_relative_to(Path("/work/outputs")) and context.name == "environment",
        "Worker contract failed at worker/docker_bridge.py:170",
    )
    task = next(t for t in [family["task"]] if t["task"] == context.parent.name)
    raw = (context / "Dockerfile").read_bytes()
    digest = content_sha(raw)
    spec = next(f for f in task["files"] if f["path"].endswith("/environment/Dockerfile"))
    require(digest == spec["sha256"], "Worker contract failed at worker/docker_bridge.py:175")
    image = owner + "-" + task["task"].lower() + ":" + digest[:12]
    commands = {"build", "up", "down", "ps", "exec", "cp", "logs", "config", "stop", "rm"}
    index = 1
    while index < len(args) and args[index] not in commands:
        require(
            args[index] in {"--project-name", "--project-directory", "-f"},
            "Worker contract failed at worker/docker_bridge.py:180",
        )
        index += 2
    require(index < len(args), "Worker contract failed at worker/docker_bridge.py:182")
    command = args[index]
    if command == "build":
        require(args[index:] == ["build"], "Worker contract failed at worker/docker_bridge.py:185")
        return build_image(real, owner, context, raw, "task", task["task"])["exit_code"]
    if command == "up":
        image = capture_identity(real, owner, image, task, digest)
    infra = Path("/work/infra")
    infra.mkdir(exist_ok=True)
    overlay = infra / (digest + ".json")
    overlay.write_text(
        json.dumps(
            dict(
                services=dict(
                    main=dict(
                        image=image,
                        build=None,
                        pull_policy="never",
                        cpus=1.0,
                        mem_limit="6g",
                        memswap_limit="6g",
                        network_mode=family["task_network"],
                        labels={"biotasks.run": owner},
                    )
                )
            )
        )
        + "\n"
    )
    routed = args[:index] + ["-f", str(overlay)] + args[index:]
    if command == "up":
        routed += ["--no-build", "--pull", "never"]
    os.execv(real, [real, *routed])


if __name__ == "__main__":
    raise SystemExit(main())
