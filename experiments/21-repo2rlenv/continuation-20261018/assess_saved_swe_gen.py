"""Assess a completed, unchanged SWE-gen export with separate solution controls.

This is post-run assessment, not generation, author feedback or task repair.
The published task must match all frozen hashes and permissions. Every control
retains every task asset except its solution script, including runtime assets.
"""

import argparse
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path

from prepare_pr_correctness_controls import assets, controls
from repo2rlenv.execution.lifecycle import save_record
from run_robbins_native_controls import run_case


def main():
    assert os.environ.get("REPO2RLENV_REMOTE_WORKER") == "1"
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.inputs / "manifest.json").read_text())
    assert manifest["manual_assessment_only"] and not manifest["feedback_to_author"]
    assert manifest["model_calls"] == manifest["task_specific_fixes"] == 0
    assert manifest["candidate_id"] == "d52d9d8d8c952c886adb"
    original = Path("/work/native/generation-evidence.tar.gz")
    with original.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == manifest["original_archive_sha256"]
    args.output.mkdir(parents=True, exist_ok=False)
    prefix = manifest["original_task_member"] + "/"
    task = args.output / "native-task" / manifest["task_name"]
    task.mkdir(parents=True)
    # Copy only the already emitted final task; do not re-export or regenerate.
    with tarfile.open(original, "r|gz") as archive:
        for member in archive:
            if not member.name.startswith(prefix) or member.isdir():
                continue
            relative = Path(member.name[len(prefix):])
            assert not relative.is_absolute() and ".." not in relative.parts
            assert member.isfile()
            destination = task / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output, 65536)
            destination.chmod(member.mode & 0o777)
    original_assets = assets(task)
    assert original_assets == manifest["original_published_task_assets"]
    contract = json.loads((task / "tests/contract.json").read_text())
    assert contract["submitted_files"] == ["skbio/sequence/_sequence.py"]
    expected_tests = set(contract["expected_passes"])
    assert len(expected_tests) == 320
    # No task.toml, image, dependency, fixture or grader changes, even in copies.
    shutil.copytree(task, args.output / "offline-task")
    prepared = controls(task, args.output / "cases", pr=2630)
    cases = prepared["cases"]
    assert [case["case"] for case in cases] == manifest["control_order"]
    for case, expected in zip(cases, manifest["expected_rewards"], strict=True):
        case["expected_reward"] = expected
    fixed = assets(task, exclude={"solution/solve.sh"})
    save_record(args.output / "control-manifest.json", {
        "stage": "post_run_controls_prepared_not_executed",
        "candidate_id": manifest["candidate_id"],
        "native_task_relative_path": task.relative_to(args.output).as_posix(),
        "native_assets": original_assets,
        "profile_assets": original_assets,
        "changed_profile_assets": [],
        "case_unchanged_assets": fixed,
        "cases": cases,
        "model_calls": 0,
        "reward_contract": "unchanged native binary all expected tests pass",
    })
    rows = []
    summary = {
        "stage": "completed_native_output_post_run_manual_assessment_not_admission",
        "candidate_id": manifest["candidate_id"],
        "manual_assessment_only": True,
        "model_calls": 0,
        "task_specific_fixes": 0,
        "feedback_to_author": False,
        "new_candidate_charge": 0,
        "new_native_exports": 0,
        "new_admissions": 0,
        "original_asset_hashes_and_modes_verified": len(original_assets),
        "runtime_profile_changes": [],
        "records": rows,
    }
    for case in cases:
        assert assets(Path(case["bundle"]), exclude={"solution/solve.sh"}) == fixed
        rows.append(run_case(case, args.output, expected_tests))
        save_record(args.output / "summary.json", summary)
    summary["all_controls_passed"] = all(row["passed"] for row in rows)
    summary["all_controls_executed_and_parsed"] = all(row["executed_and_parsed"] for row in rows)
    assert assets(task) == original_assets
    save_record(args.output / "summary.json", summary)
    print(json.dumps({"candidate_id": manifest["candidate_id"], "all_controls_passed": summary["all_controls_passed"], "model_calls": 0}), flush=True)
    if not summary["all_controls_executed_and_parsed"]:
        raise RuntimeError("Some assessment controls did not execute and parse")


if __name__ == "__main__":
    main()
