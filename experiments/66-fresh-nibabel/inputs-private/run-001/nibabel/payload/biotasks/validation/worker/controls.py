"""Unchanged-task nop/oracle commands with native deadlines and explicit outer bounds."""

import hashlib
import json
import os
import signal
import subprocess
import time
import tomllib
from pathlib import Path
from typing import Any

from biotasks.validation.files import require, write_json

ROOT = Path("/work")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(config: dict[str, Any]) -> dict[str, str]:
    task = config["task"]
    directory = ROOT / task["relative_directory"]
    actual = {p.relative_to(ROOT).as_posix() for p in directory.rglob("*") if p.is_file()}
    require(actual == {r["path"] for r in task["files"]}, "Task inventory changed")
    hashes = {}
    for row in task["files"]:
        path = ROOT / row["path"]
        require(
            not path.is_symlink()
            and path.stat().st_size == row["bytes"]
            and path.stat().st_mode & 0o777 == int(row["mode"], 8),
            "Task modes/size changed",
        )
        hashes[row["path"]] = digest(path)
        require(hashes[row["path"]] == row["sha256"], "Task bytes changed")
    value = tomllib.loads((directory / "task.toml").read_text())
    require(
        value.get("verifier", {}).get("timeout_sec", 600) == task["verifier_seconds"],
        "Native verifier deadline changed",
    )
    return hashes


def commands(config: dict[str, Any], jobs: Path) -> list[dict[str, Any]]:
    task = config["task"]
    rows = []
    for agent in ("nop", "oracle"):
        name = task["task"] + "-" + agent
        command = [
            "/work/harbor066/bin/harbor",
            "run",
            "-p",
            str(ROOT / task["relative_directory"]),
            "-a",
            agent,
            "--env",
            "docker",
            "-n",
            "1",
            "-k",
            "1",
            "-r",
            "0",
            "--override-cpus",
            "1",
            "--override-memory-mb",
            "6144",
            "--verifier-timeout-multiplier",
            "1",
            "-o",
            str(jobs),
            "--job-name",
            name,
        ]
        rows.append(
            {
                "task": task["task"],
                "agent": agent,
                "name": name,
                "command": command,
                "verifier_timeout_seconds": task["verifier_seconds"],
                "wrapper_allowance_seconds": config["resources"]["wrapper_seconds"],
                "state": "unstarted",
            }
        )
    return rows


def main() -> int:
    config = json.loads((ROOT / "family.json").read_text())
    require(os.environ.get("BIOTASKS_BOUNDED_SUPERVISOR") == "1", "Bounded supervisor required")
    require(
        not any(
            os.environ.get(k)
            for k in (
                "GH_TOKEN",
                "GITHUB_TOKEN",
                "OPENROUTER_API_KEY",
                "CW_KEY_ID",
                "CW_KEY_SECRET",
                "HF_TOKEN",
            )
        ),
        "Credentials must not enter controls",
    )
    before = inspect(config)
    jobs = Path(os.environ["BIOTASKS_SHARED_ROOT"]) / "jobs"
    require(not jobs.exists(), "Never overwrite a prior controls invocation")
    jobs.mkdir()
    evidence = ROOT / "evidence/controls"
    evidence.mkdir()
    rows = commands(config, jobs)
    write_json(evidence / "controls.json", rows)
    try:
        for row in rows:
            allowance = row["wrapper_allowance_seconds"]
            if time.time() + allowance + 300 > float(os.environ["BIOTASKS_DEADLINE"]):
                row["reason"] = "insufficient_full_native_window_and_cleanup_reserve"
                break
            row.update(state="running", started=time.time())
            write_json(evidence / "controls.json", rows)
            process = None
            try:
                with (evidence / (row["name"] + ".log")).open("w") as log:
                    process = subprocess.Popen(
                        row["command"], stdout=log, stderr=subprocess.STDOUT, start_new_session=True
                    )
                    process.wait(timeout=allowance)
                row.update(state="completed", exit_code=process.returncode, finished=time.time())
            except subprocess.TimeoutExpired:
                row.update(
                    state="wrapper_timeout",
                    finished=time.time(),
                    reason="stop_owned_containers_before_any_later_control",
                )
                return 124
            finally:
                if process and process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
            row["trial_results"] = [
                {"path": p.relative_to(jobs).as_posix(), "result": json.loads(p.read_text())}
                for p in sorted((jobs / row["name"]).glob("*/result.json"))
            ]
            row["reward_files"] = {
                p.relative_to(jobs).as_posix(): p.read_text()
                for p in sorted((jobs / row["name"]).rglob("reward*"))
                if p.is_file() and p.stat().st_size < 100000
            }
            write_json(evidence / "controls.json", rows)
    finally:
        after = inspect(config)
        write_json(
            evidence / "task-files-unchanged.json",
            {"verified": before == after, "before": before, "after": after},
        )
        write_json(evidence / "controls.json", rows)
        require(before == after, "Task files changed during controls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
