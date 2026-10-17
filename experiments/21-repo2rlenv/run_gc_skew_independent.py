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
    import argparse
    from prepare_gc_skew_controls import prepare
    from prepare_skbio_pr_controls import retained_hashes
    from repo2rlenv.emitter.bundle import inspect_bundle
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('/evidence/native/independent'))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    identity = inspect_bundle(args.task)
    assert identity['integrity_passed'], 'Original native bundle changed'
    prepare(args.task, output/'bundles')
    manifest = json.loads((output/'bundles/manifest.json').read_text())
    manifest['source_bundle_hash'] = identity['bundle_hash']
    manifest['reward_contract'] = 'binary_all_expected_tests_pass'
    for case in manifest['cases']:
        assert retained_hashes(Path(case['bundle'])) == manifest['unchanged_assets']
    save_record(output/'bundles/manifest.json', manifest)
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
            "interpretation": case["interpretation"],
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
            and evidence.exception_type is None
            and (case["expected_reward"] is None or evidence.reward == case["expected_reward"])
        )
        save_record(output / "summary.json", {"records": records})
    if not all(r["passed"] for r in records):
        raise RuntimeError("Independent submission controls did not all pass")


if __name__ == "__main__":
    main()
