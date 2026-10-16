"""Export saved native contrasts and run Harbor nop/oracle on a remote worker.

Uses the pinned native exporter and the same Harbor command/environment as
run_trial, without invoking its remote transport wrapper from inside the worker.
No model calls occur. Passing these controls is not independent validation.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from repo2rlenv.execution.harbor import read_trial
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.swe_smith.export import export_candidate
from repo2rlenv.pipelines.recipes.swe_smith.options import SWESmithOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--issues", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Run only inside the authorized remote worker")
    generation = json.loads((args.generation / "generation.json").read_text())
    issues = json.loads(args.issues.read_text())["records"]
    authored = {r["candidate_id"]: r["issue"] for r in issues if r["status"] == "authored"}
    options = SWESmithOptions.model_validate(json.loads(args.config.read_text())["options"])
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for candidate in generation["candidates"]:
        identifier = candidate["id"]
        if identifier not in authored:
            continue
        record = {"candidate_id": identifier, "stage": "export", "trials": []}
        records.append(record)
        try:
            task = export_candidate(
                args.generation,
                candidate,
                options,
                authored[identifier],
                args.output / "tasks" / identifier,
                org="open-athena",
            )
            record["task"] = str(task)
            record["stage"] = "native_controls"
            for agent in ("nop", "oracle"):
                trial_id = f"smith-{identifier}-{agent}"
                command = [
                    str(Path(sys.executable).with_name("harbor")),
                    "run",
                    "--path",
                    str(task),
                    "--agent",
                    agent,
                    "--env",
                    "repo2rlenv.execution.harbor_offline:OfflineDockerEnvironment",
                    "--n-concurrent",
                    "1",
                    "--max-retries",
                    "0",
                    "--job-name",
                    trial_id,
                    "--jobs-dir",
                    str(args.output / "jobs"),
                    "--quiet",
                ]
                trial = {"agent": agent, "command": command, "timeout_sec": 900}
                record["trials"].append(trial)
                save_record(args.output / "summary.json", {"records": records})
                with (args.output / f"{trial_id}.log").open("w") as log:
                    process = subprocess.Popen(
                        command,
                        stdout=log,
                        stderr=log,
                        start_new_session=True,
                    )
                    try:
                        trial["returncode"] = process.wait(timeout=900)
                    finally:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGTERM)
                            try:
                                process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait()
                evidence = read_trial(args.output / "jobs" / trial_id)
                trial.update(
                    completed=evidence.completed,
                    reward=evidence.reward,
                    exception_type=evidence.exception_type,
                )
            record["native_controls_passed"] = all(
                t["returncode"] == 0 and t["completed"] for t in record["trials"]
            ) and [t["reward"] for t in record["trials"]] == [0, 1]
            record["stage"] = "native_controls_completed"
        except Exception as exc:
            record.update(stage="failed", error_type=type(exc).__name__)
        save_record(args.output / "summary.json", {"records": records})


if __name__ == "__main__":
    main()
