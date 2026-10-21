#!/usr/bin/env python3
"""Approved infrastructure guard; does not alter Repo2RLEnv source or tests."""

import fcntl
import os
import subprocess
import sys
from pathlib import Path


def bounded_arguments(arguments, run_id):
    if not arguments:
        return arguments, False
    offset = 1 if arguments[0] == "container" else 0
    if len(arguments) <= offset or arguments[offset] not in {"run", "create"}:
        return arguments, False
    forbidden = (
        "--cpus", "--cpu-", "--cpuset", "--memory", "--network", "--net",
        "--privileged", "--cgroup", "--label", "-l=",
    )
    if any(arg.startswith(forbidden) or arg in {"-m", "-l"} for arg in arguments[offset + 1:]):
        raise ValueError("Conflicting Docker resource, network, privilege or ownership option")
    caps = [
        "--cpus=1.5", "--memory=6g", "--memory-swap=6g",
        "--network=iris-egress", f"--label=biotasks.run={run_id}",
    ]
    return arguments[:offset + 1] + caps + arguments[offset + 1:], True


def main():
    binary = os.environ["BIOTASKS_REAL_DOCKER"]
    run_id = os.environ["BIOTASKS_RUN_ID"]
    args, creates = bounded_arguments(sys.argv[1:], run_id)
    if not creates:
        os.execv(binary, [binary, *args])
    lock = Path(os.environ["BIOTASKS_DOCKER_GUARD_LOCK"])
    with lock.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        # Count created containers too: a stopped container must be removed
        # before another slot is allocated, avoiding unbounded queued starts.
        result = subprocess.run(
            [binary, "ps", "-aq", "--filter", f"label=biotasks.run={run_id}"],
            check=True, text=True, capture_output=True,
        )
        if len(result.stdout.split()) >= 2:
            raise RuntimeError("Two owned pipeline containers already exist")
        return subprocess.run([binary, *args], check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
