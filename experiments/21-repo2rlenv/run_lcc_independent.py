"""Run alternative-correct and incorrect submissions through the unchanged grader."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from repo2rlenv.execution.harbor import read_trial
from repo2rlenv.execution.lifecycle import save_record


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Remote execution required")
    output = Path("/evidence/native/independent")
    output.mkdir(parents=True, exist_ok=False)
    original = Path(
        "/work/native/inputs/native/validation/tasks/e4027e396d2357882bc7/"
        "swe-smith-e4027e396d2357882bc7"
    )
    subprocess.run(
        [
            sys.executable,
            "/work/native/prepare_lcc_independent_controls.py",
            "--task",
            str(original),
            "--output",
            str(output / "bundles"),
        ],
        check=True,
        timeout=120,
    )
    manifest = json.loads((output / "bundles/manifest.json").read_text())
    records = []
    for case in manifest["cases"]:
        name = case["case"]
        command = [
            str(Path(sys.executable).with_name("harbor")),
            "run",
            "--path",
            case["bundle"],
            "--agent",
            "oracle",
            "--env",
            "repo2rlenv.execution.harbor_offline:OfflineDockerEnvironment",
            "--n-concurrent",
            "1",
            "--max-retries",
            "0",
            "--job-name",
            name,
            "--jobs-dir",
            str(output / "jobs"),
            "--quiet",
        ]
        record = {
            "case": name,
            "expected_reward": case["expected_reward"],
            "command": command,
            "timeout_sec": 900,
            "stage": "running",
        }
        records.append(record)
        save_record(output / "summary.json", {"records": records})
        with (output / (name + ".log")).open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
            try:
                record["returncode"] = process.wait(timeout=900)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
        evidence = read_trial(output / "jobs" / name)
        record.update(
            stage="completed",
            completed=evidence.completed,
            reward=evidence.reward,
            exception_type=evidence.exception_type,
        )
        record["passed"] = (
            record["returncode"] == 0
            and evidence.completed
            and evidence.reward == case["expected_reward"]
        )
        save_record(output / "summary.json", {"records": records})
    if not all(r["passed"] for r in records):
        raise RuntimeError("Independent submission controls did not all pass")


if __name__ == "__main__":
    main()
