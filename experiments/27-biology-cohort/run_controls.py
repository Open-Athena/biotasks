"""Official Harbor nop/oracle controls; no task rewriting or solver calls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    evidence = Path("/work/evidence")
    tasks = sorted(p.parent for p in args.tasks.rglob("task.toml"))
    rows = []
    environment = os.environ.copy()
    for name in ["GH_TOKEN", "GITHUB_TOKEN", "OPENROUTER_API_KEY"]:
        environment.pop(name, None)
    environment["PATH"] = "/work/harbor-bin:/work/harbor066/bin:/work/bin:/usr/local/bin:/usr/bin:/bin"
    jobs = Path(os.environ["BIOTASKS_SHARED_ROOT"]) / "jobs" / args.prefix
    jobs.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        before = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in task.rglob("*") if p.is_file()}
        for agent in ["nop", "oracle"]:
            name = task.name + "-" + agent
            command = ["/work/harbor066/bin/harbor", "run", "-p", str(task), "-a", agent,
                       "--env", "docker", "-n", "1", "-k", "1", "-r", "0",
                       "--override-cpus", "1", "--override-memory-mb", "6144",
                       "-o", str(jobs), "--job-name", name]
            row = {"task": task.name, "agent": agent, "command": command,
                   "started": time.time(), "state": "running"}
            rows.append(row)
            (evidence / (args.prefix + "-controls.json")).write_text(json.dumps(rows, indent=2) + "\n")
            print("CONTROL_START " + name, flush=True)
            with (evidence / (args.prefix + "-" + name + ".log")).open("w") as log:
                result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                        check=False, timeout=3300)
            row.update(exit_code=result.returncode, state="completed", finished=time.time())
            row["trial_results"] = []
            for path in sorted((jobs / name).glob("*/result.json")):
                value = json.loads(path.read_text())
                row["trial_results"].append({"path": str(path), "result": value})
            for path in sorted((jobs / name).rglob("reward*")):
                if path.is_file() and path.stat().st_size < 100000:
                    row.setdefault("reward_files", {})[str(path.relative_to(jobs / name))] = path.read_text()
            (evidence / (args.prefix + "-controls.json")).write_text(json.dumps(rows, indent=2) + "\n")
            print("CONTROL_END " + name + " exit=" + str(result.returncode), flush=True)
        after = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in task.rglob("*") if p.is_file()}
        assert before == after, "Harbor modified original task files"
    (evidence / (args.prefix + "-task-files-unchanged.json")).write_text(json.dumps({
        "verified": True, "tasks": [p.name for p in tasks]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
