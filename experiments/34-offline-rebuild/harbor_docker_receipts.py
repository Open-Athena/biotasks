#!/usr/bin/env python3
"""Resource/image/network plumbing for unchanged Harbor Docker controls."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from capture_build_receipt import capture


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
            receipt = capture(real, run_id, image, Path("/work/evidence"))
            with Path("/work/evidence/build-receipts.jsonl").open("a") as handle:
                handle.write(json.dumps(receipt) + "\n")
            return 0
        build = [real, "build", "--force-rm", "--cpu-period=100000", "--cpu-quota=150000",
                 "--memory=6g", "--memory-swap=6g", "--network=iris-egress",
                 "--label", "biotasks.run=" + run_id, "--tag", image, str(context)]
        environment = os.environ.copy(); environment["DOCKER_BUILDKIT"] = "0"
        started = time.time()
        with (Path("/work/evidence") / "build-starts.jsonl").open("a") as handle:
            handle.write(json.dumps({"image": image, "started": started, "dockerfile_sha256": digest}) + "\n")
        result = subprocess.run(build, env=environment, check=False)
        row = {"context": str(context), "dockerfile_sha256": digest, "image": image,
               "started": started, "finished": time.time(), "exit_code": result.returncode,
               "cpu_limit": 1.5, "memory_bytes": 6 * 1024**3}
        if result.returncode == 0:
            value = json.loads(subprocess.check_output([real, "image", "inspect", image]))[0]
            row["image_id"] = value["Id"]
            receipt = capture(real, run_id, image, Path("/work/evidence"))
            with Path("/work/evidence/build-receipts.jsonl").open("a") as handle:
                handle.write(json.dumps(receipt) + "\n")
        with (Path("/work/evidence") / "bounded-builds.jsonl").open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        return result.returncode
    routed = args[:index] + ["-f", str(overlay)] + args[index:]
    if command == "up":
        routed += ["--no-build", "--pull", "never"]
    os.execv(real, [real, *routed])


if __name__ == "__main__":
    sys.exit(main())
