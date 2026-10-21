"""Run the two checkpointed official CLI inputs once, then official controls."""

import json
import os
from pathlib import Path
import subprocess
import time


def main():
    environment = os.environ.copy()
    environment.pop("GITHUB_TOKEN", None)
    environment["PATH"] = "/work/native-bin:/work/upstream/.venv/bin:/work/bin:/usr/local/bin:/usr/bin:/bin"
    assert not list(Path("/work/bootstrap").glob("*")), "Fresh bootstrap cache required"
    rows = []
    for config in sorted(Path("/work/inputs").glob("*.json")):
        command = ["/work/upstream/.venv/bin/repo2rlenv", "--no-ui", "generate", "--config", str(config),
                   "--max-spend-usd", "5"]
        row = {"input": config.name, "command": command, "started": time.time(), "state": "running"}
        rows.append(row)
        target = Path("/work/evidence/native-windows.json")
        target.write_text(json.dumps(rows, indent=2) + "\n")
        print("NATIVE_START " + config.stem, flush=True)
        with (Path("/work/evidence") / (config.stem + ".log")).open("w") as log:
            result = subprocess.run(command, env=environment, cwd="/work/upstream", stdout=log,
                                    stderr=subprocess.STDOUT, timeout=10800, check=False)
        row.update(exit_code=result.returncode, finished=time.time(), state="completed")
        target.write_text(json.dumps(rows, indent=2) + "\n")
        print("NATIVE_END " + config.stem + " exit=" + str(result.returncode), flush=True)
    exports = sorted(str(p.relative_to("/work")) for p in Path("/work/outputs").rglob("task.toml"))
    Path("/work/evidence/exported-tasks.json").write_text(json.dumps(exports, indent=2) + "\n")
    if exports:
        subprocess.run(["/usr/local/bin/python", "/work/run_controls.py", "--tasks", "/work/outputs",
                        "--prefix", "fresh"], check=True)
    print("GENERATION_DONE exports=" + str(len(exports)), flush=True)


if __name__ == "__main__":
    main()
