#!/usr/bin/env python3
"""Resource/image/network plumbing for unchanged Harbor Docker controls."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def tagged_recipe(raw, run_id):
    lines = raw.splitlines(keepends=True)
    positions = [i for i, line in enumerate(lines) if line.upper().startswith(b"FROM ")]
    assert len(positions) == 1, "This ownership adaptation supports one stage only"
    i = positions[0] + 1
    lines.insert(i, ("LABEL biotasks.run=" + run_id + "\n").encode())
    return b"".join(lines)


def capture_identity(real, image, run_id, digest):
    manifest = json.loads(Path("/work/cold-worker-inputs.json").read_text())
    script = ("import json,subprocess,sys,platform; print(json.dumps(dict("
              "git_head=subprocess.check_output([\"git\",\"-C\",\"/workspace\",\"rev-parse\",\"HEAD\"],text=True).strip(),"
              "python=sys.version,platform=platform.platform(),"
              "packages=subprocess.check_output([sys.executable,\"-m\",\"pip\",\"--disable-pip-version-check\",\"freeze\"],text=True).splitlines())))")
    result = subprocess.run([real, "run", "--rm", "--name", run_id + "-identity",
        "--cpus=1", "--memory=256m", "--memory-swap=256m", "--network=none",
        "--label", "biotasks.run=" + run_id, "--entrypoint", "/usr/local/bin/python", image, "-c", script],
        capture_output=True, text=True, timeout=90, check=True)
    record = json.loads(result.stdout)
    record.update(image=image, dockerfile_sha256=digest, captured=time.time())
    with Path("/work/evidence/image-identities.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    assert record["git_head"] == manifest["base_commit"], "Actual image is not at frozen PR base"



def main():
    real = os.environ["BIOTASKS_REAL_DOCKER"]
    run_id = os.environ["BIOTASKS_RUN_ID"]
    args = sys.argv[1:]
    if not args or args[0] != "compose":
        if any(value in {"run", "create", "build"} for value in args[:2]):
            raise SystemExit("Direct container/build operations must use the bounded path")
        os.execv(real, [real, *args])
    if args[1:] == ["version"]:
        os.execv(real, [real, *args])
    context = Path(os.environ["CONTEXT_DIR"]).resolve()
    assert any(context.is_relative_to(Path(p)) for p in ["/work/published", "/work/outputs"])
    assert context.name == "environment" and (context / "Dockerfile").is_file()
    digest = hashlib.sha256((context / "Dockerfile").read_bytes()).hexdigest()
    image = f"{run_id}-{context.parent.name.lower()}:{digest[:12]}"
    commands = {"build", "up", "down", "ps", "exec", "cp", "logs", "config", "stop", "rm"}
    index = 1
    while index < len(args) and args[index] not in commands:
        assert args[index] in {"--project-name", "--project-directory", "-f"}, args[index]
        index += 2
    assert index < len(args)
    command = args[index]
    infra = Path("/work/infra"); infra.mkdir(exist_ok=True)
    overlay = infra / (digest + ".json")
    overlay.write_text(json.dumps({"services": {"main": {
        "image": image, "build": None, "pull_policy": "never",
        "cpus": 1.0, "mem_limit": "6g", "memswap_limit": "6g",
        "network_mode": "iris-egress", "labels": {"biotasks.run": run_id},
    }}}, indent=2) + "\n")
    if command == "build":
        assert args[index:] == ["build"]
        found = subprocess.run([real, "image", "inspect", image], capture_output=True, text=True)
        if found.returncode == 0:
            value = json.loads(found.stdout)[0]
            assert value["Config"]["Labels"]["biotasks.run"] == run_id
            with Path("/work/evidence/bounded-builds.jsonl").open("a") as handle:
                handle.write(json.dumps(dict(image=image, image_id=value["Id"], cached=True, dockerfile_sha256=digest, finished=time.time(), exit_code=0)) + "\n")
            return 0
        raw = (context / "Dockerfile").read_bytes()
        effective = tagged_recipe(raw, run_id)
        recipe = infra / (digest + ".Dockerfile")
        recipe.write_bytes(effective)
        build = [real, "build", "--force-rm", "--cpu-period=100000", "--cpu-quota=150000",
                 "--memory=6g", "--memory-swap=6g", "--network=iris-egress",
                 "--label", "biotasks.run=" + run_id, "--tag", image, "-f", str(recipe), str(context)]
        environment = os.environ.copy(); environment["DOCKER_BUILDKIT"] = "0"
        started = time.time()
        with (Path("/work/evidence") / "build-starts.jsonl").open("a") as handle:
            handle.write(json.dumps({"image": image, "started": started, "dockerfile_sha256": digest}) + "\n")
        result = subprocess.run(build, env=environment, check=False)
        row = {"context": str(context), "dockerfile_sha256": digest, "image": image,
               "started": started, "finished": time.time(), "exit_code": result.returncode,
               "effective_dockerfile_sha256": hashlib.sha256(effective).hexdigest(),
               "ownership_label_only": True, "cpu_limit": 1.5, "memory_bytes": 6 * 1024**3}
        if result.returncode == 0:
            value = json.loads(subprocess.check_output([real, "image", "inspect", image]))[0]
            row["image_id"] = value["Id"]
        with (Path("/work/evidence") / "bounded-builds.jsonl").open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        return result.returncode
    routed = args[:index] + ["-f", str(overlay)] + args[index:]
    if command == "up":
        capture_identity(real, image, run_id, digest)
        routed += ["--no-build", "--pull", "never"]
    os.execv(real, [real, *routed])


if __name__ == "__main__":
    sys.exit(main())
