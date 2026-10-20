"""Invoke upstream CLI once per window; never repair or restart a bootstrap."""

import json
import os
from pathlib import Path
import signal
import subprocess
import time

from repo2rlenv.bootstrap import cache
from repo2rlenv.bootstrap.runner import _cache_options
from repo2rlenv.config import load_generation_input

WORK = Path("/work")
EVIDENCE = WORK / "evidence"
ORDER = ["MLCIL__scikit-fingerprints-544", "MLCIL__scikit-fingerprints-525",
         "nipy__nipype-3753", "psychopy__psychopy-7475", "psychopy__psychopy-7805"]
COUNTS = [3, 1, 6, 1, 5]


def save(rows):
    (EVIDENCE / "native-windows.json").write_text(json.dumps(rows, indent=2) + "\n")


def main():
    EVIDENCE.mkdir(exist_ok=True)
    (WORK / "bootstrap").mkdir(exist_ok=True)
    (WORK / "outputs").mkdir(exist_ok=True)
    seen = set()
    rows = []
    for slug, count in zip(ORDER, COUNTS, strict=True):
        config = WORK / "inputs" / f"{slug}.json"
        spec = load_generation_input(config)
        repo = spec.repo.url.removeprefix("https://github.com/").removesuffix(".git")
        if repo in seen:
            cached = cache.load(repo, spec.repo.ref, spec.bootstrap.cache_dir,
                                options=_cache_options(spec.bootstrap))
            present = cached and cached.image_digest and subprocess.run(
                ["docker", "image", "inspect", cached.image_tag or cached.image_digest],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
            ).returncode == 0
            if not present:
                rows.append({"window": slug, "state": "not_run",
                             "reason": "no_reusable_native_bootstrap; no_second_bootstrap_allowed"})
                save(rows)
                continue
        seen.add(repo)
        command = ["repo2rlenv", "--no-ui", "generate", "--config", str(config), "--max-spend-usd", "5"]
        row = {"window": slug, "command": command, "started": time.time(), "state": "running"}
        rows.append(row)
        save(rows)
        print("BIOTASKS25_WINDOW_START " + slug, flush=True)
        with (EVIDENCE / f"{slug}.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, cwd="/work/upstream")
            try:
                row["exit_code"] = process.wait(timeout=2400 + count * 1800)
                row["state"] = "completed"
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                row["state"] = "infrastructure_deadline"
                raise
            finally:
                row["finished"] = time.time()
                save(rows)
        print("BIOTASKS25_WINDOW_END " + json.dumps(row), flush=True)
    tasks = sorted(str(path.relative_to(WORK)) for path in (WORK / "outputs").rglob("task.toml"))
    (EVIDENCE / "exported-tasks.json").write_text(json.dumps(tasks, indent=2) + "\n")
    print("BIOTASKS25_NATIVE_FINISHED " + json.dumps({"exports": len(tasks)}), flush=True)


if __name__ == "__main__":
    main()
