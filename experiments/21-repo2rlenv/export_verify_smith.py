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
from repo2rlenv.pipelines.recipes.catalog import get_recipe
from repo2rlenv.pipelines.recipes.repository.export import export_repository_task
from repo2rlenv.pipelines.recipes.swe_flow.schedule import skeletonize
from repo2rlenv.pipelines.recipes.swe_smith.export import export_candidate
from repo2rlenv.pipelines.recipes.swe_smith.options import SWESmithOptions
from repo2rlenv.spec.recipe_options import ReconstructionOptions


def export_flow(generation, candidate, options, authored, destination):
    """Mirror the pinned SWE-flow export using saved native author outputs."""
    base = generation / "base"
    recipe = get_recipe("swe_flow")
    return export_repository_task(
        base=base,
        defective={
            relative: skeletonize(
                (base / relative).read_text(),
                path=relative,
                schedule=candidate["schedule"],
                docstrings=authored["docstrings"],
            ).encode()
            for relative in candidate["source_files"]
        },
        reference={
            relative: (base / relative).read_bytes() for relative in candidate["source_files"]
        },
        options=options,
        instruction=authored["instruction"],
        destination=destination,
        name="swe-flow-" + candidate["id"],
        org="open-athena",
        contrast=candidate["contrast"],
        metadata={
            "recipe": recipe.id,
            "pipeline": recipe.pipeline,
            "recipe_version": "1",
            "upstream_revision": recipe.upstream["commit"],
            "repository": candidate["repo"],
            "source_revision": candidate["ref"],
            "development_step": candidate["schedule"]["step"],
            "scheduled_function_count": len(candidate["functions"]),
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--issues", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recipe", choices=("swe_smith", "swe_flow"), default="swe_smith")
    args = parser.parse_args()
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Run only inside the authorized remote worker")
    generation = json.loads((args.generation / "generation.json").read_text())
    issues = json.loads(args.issues.read_text())["records"]
    authored = {r["candidate_id"]: r for r in issues if r["status"] == "authored"}
    option_type = ReconstructionOptions if args.recipe == "swe_flow" else SWESmithOptions
    options = option_type.model_validate(json.loads(args.config.read_text())["options"])
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for candidate in generation["candidates"]:
        identifier = candidate["id"]
        if identifier not in authored:
            continue
        record = {"candidate_id": identifier, "stage": "export", "trials": []}
        records.append(record)
        try:
            if args.recipe == "swe_flow":
                task = export_flow(
                    args.generation,
                    candidate,
                    options,
                    authored[identifier],
                    args.output / "tasks" / identifier,
                )
            else:
                task = export_candidate(
                    args.generation,
                    candidate,
                    options,
                    authored[identifier]["issue"],
                    args.output / "tasks" / identifier,
                    org="open-athena",
                )
            record["task"] = str(task)
            record["stage"] = "native_controls"
            for agent in ("nop", "oracle"):
                prefix = "flow" if args.recipe == "swe_flow" else "smith"
                trial_id = f"{prefix}-{identifier}-{agent}"
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
