"""Run only the pinned native SWE-gen source/build/test stage on frozen inputs.

This orchestration does not author, export, assess or repair tasks. Repository
profiles and source metadata must match the previously recorded intake hashes.
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.spec.recipe_options import PRRecipeOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("REPO2RLENV_REMOTE_WORKER") == "1"
    assert not os.environ.get("OPENAI_API_KEY") and not os.environ.get("GLM_BULK_TOKEN")
    manifest = json.loads((args.inputs / "cohort.json").read_text())
    assert 1 <= len(manifest["cases"]) <= 4 and manifest["model_calls"] == 0
    assert manifest["task_specific_fixes"] == manifest["new_candidate_charge"] == 0
    for name, expected in manifest["files"].items():
        raw = (args.inputs / name).read_bytes()
        assert len(raw) == expected["bytes"]
        assert hashlib.sha256(raw).hexdigest() == expected["sha256"]
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    records = []
    summary = {
        "stage": "native_swe_gen_contrasts_only_not_author_export_or_admission",
        "model_calls": 0, "new_candidate_charge": 0, "task_specific_fixes": 0,
        "records": records,
    }
    for case in manifest["cases"]:
        output = args.output / str(case["pull_request"])
        output.mkdir(exist_ok=False)
        source_bytes = (args.inputs / case["source"]).read_bytes()
        profile = json.loads((args.inputs / case["profile"]).read_text())
        assert hashlib.sha256(source_bytes).hexdigest() == profile["source_sha256"]
        source = json.loads(source_bytes)
        options = PRRecipeOptions.model_validate(profile["options"])
        assert profile["recipe"] == "swe_gen" and source["id"] == case["candidate_id"]
        assert source["source_files"] == options.source_paths
        assert options.target == 3 and options.max_candidates == 10
        config = output / "config.json"
        save_record(config, {"source": source, "options": profile["options"]})
        row = {"pull_request": case["pull_request"], "candidate_id": source["id"],
               "status": "started", "task_specific_fixes": 0, "model_calls": 0}
        records.append(row)
        save_record(args.output / "result.json", summary)
        case_started = time.monotonic()
        try:
            with (output / "stdout.txt").open("w") as stdout, (output / "stderr.txt").open("w") as stderr:
                process = subprocess.Popen(
                    [sys.executable, "-m", "repo2rlenv.pipelines.recipes.swe_gen.worker",
                     str(config), str(output / "generation")],
                    stdout=stdout, stderr=stderr, start_new_session=True,
                )
                try:
                    process.wait(timeout=1200)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise
            row["native_returncode"] = process.returncode
            row["status"] = "native_generation_completed" if process.returncode == 0 else "native_generation_failed_no_repair"
            candidate = output / "generation/candidate.json"
            if process.returncode == 0:
                record = json.loads(candidate.read_text())
                assert record["id"] == source["id"] and record["head"] == source["head"]
                row["contrast"] = record["contrast"]
                row["candidate_json_sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except Exception as exc:
            row.update(status="native_generation_failed_no_repair", error_type=type(exc).__name__)
        row["elapsed_seconds"] = round(time.monotonic() - case_started, 3)
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save_record(args.output / "result.json", summary)
        if row.get("error_type") == "TimeoutExpired":
            # Do not start another build while Docker daemon work is uncertain.
            # The enclosing controller archives the partial result and removes
            # this cohort's dedicated sandbox before any later dispatch.
            summary["unstarted_pull_requests"] = [
                c["pull_request"] for c in manifest["cases"][len(records):]
            ]
            save_record(args.output / "result.json", summary)
            break


if __name__ == "__main__":
    main()
