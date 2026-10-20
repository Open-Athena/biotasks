"""Finish native SWE-gen export and baseline/reference checks without authoring.

All task inputs are the original saved generation/profile/model output. This is
stage orchestration; it never repairs instructions, sources, tests or packaging.
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tarfile
from pathlib import Path

from repo2rlenv.emitter.bundle import inspect_bundle
from repo2rlenv.execution.harbor import read_trial
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines.recipes.catalog import get_recipe
from repo2rlenv.pipelines.recipes.repository.export import export_repository_task
from repo2rlenv.pipelines.recipes.swe_gen.instruction import TaskInstruction
from repo2rlenv.spec.recipe_options import PRRecipeOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("REPO2RLENV_REMOTE_WORKER") == "1"
    assert not os.environ.get("OPENAI_API_KEY") and not os.environ.get("GLM_BULK_TOKEN")
    manifest = json.loads((args.inputs / "cohort.json").read_text())
    assert manifest["model_calls"] == manifest["task_specific_fixes"] == 0
    for name, expected in manifest["files"].items():
        raw = (args.inputs / name).read_bytes()
        assert len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"]
    archive_path = Path("/work/native/generation-evidence.tar.gz")
    with archive_path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == manifest["generation_archive_sha256"]
    extracted = Path("/work/native/saved-generation")
    extracted.mkdir(exist_ok=False)
    with tarfile.open(archive_path) as archive:
        members = [m for m in archive if m.name.startswith(manifest["generation_prefix"] + "/")]
        archive.extractall(extracted, members=members, filter="data")
    generation = extracted / manifest["generation_prefix"]
    candidate = json.loads((generation / "candidate.json").read_text())
    assert hashlib.sha256((generation / "candidate.json").read_bytes()).hexdigest() == manifest["candidate_context_sha256"]
    authored = json.loads((args.inputs / "author-result.json").read_text())
    assert authored["status"] == "authored" and authored["candidate_id"] == candidate["id"]
    instruction = TaskInstruction.model_validate(authored["result"])
    assert instruction.is_substantial
    options = PRRecipeOptions.model_validate(json.loads((args.inputs / "profile.json").read_text())["options"])
    assert options.target == 3 and options.max_candidates == 10
    recipe = get_recipe("swe_gen")
    # These arguments mirror the pinned PRToEnvPipeline export block exactly.
    kwargs = dict(
        base=generation / "base",
        defective={path: (generation / "defective-source" / path).read_bytes() for path in candidate["source_files"]},
        reference={path: (generation / "base" / path).read_bytes() for path in candidate["source_files"]},
        options=options, instruction=instruction.instruction,
        name="swe-gen-" + candidate["id"], org="open-athena", contrast=candidate["contrast"],
        metadata={"recipe": recipe.id, "recipe_version": "1", "pipeline": recipe.pipeline,
                  "upstream_revision": recipe.upstream["commit"], "repository": candidate["repo"],
                  "source_revision": candidate["head"], "source_pr": candidate["url"],
                  "force_generate_instruction": options.force_generate_instruction},
        resume=False,
    )
    args.output.mkdir(parents=True, exist_ok=False)
    record = {"stage": "saved_native_swe_gen_export_controls_not_admission",
              "candidate_id": candidate["id"], "model_calls": 0, "task_specific_fixes": 0,
              "new_candidate_charge": 0, "draft_exports": 0, "native_emitted_tasks": 0,
              "new_admissions": 0, "trials": []}
    try:
        task = export_repository_task(destination=args.output / "draft", **kwargs)
        record.update(draft_exports=1, draft_task=str(task), draft_bundle=inspect_bundle(task))
        for agent in ("nop", "oracle"):
            trial_id = "swegen-" + candidate["id"] + "-" + agent
            command = [str(Path(sys.executable).with_name("harbor")), "run", "--path", str(task),
                       "--agent", agent, "--env", "repo2rlenv.execution.harbor_offline:OfflineDockerEnvironment",
                       "--n-concurrent", "1", "--max-retries", "0", "--job-name", trial_id,
                       "--jobs-dir", str(args.output / "jobs"), "--quiet"]
            row = {"agent": agent, "trial_id": trial_id, "timeout_sec": 900}
            record["trials"].append(row)
            save_record(args.output / "summary.json", record)
            with (args.output / (trial_id + ".log")).open("w") as log:
                process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
                try:
                    row["returncode"] = process.wait(timeout=900)
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
            evidence = read_trial(args.output / "jobs" / trial_id)
            row.update(completed=evidence.completed, reward=evidence.reward, exception_type=evidence.exception_type)
        passed = all(t["completed"] for t in record["trials"]) and [t["reward"] for t in record["trials"]] == [0, 1]
        record["native_controls_passed"] = passed
        if passed:
            final = export_repository_task(destination=args.output / "tasks", **kwargs)
            final_bundle = inspect_bundle(final)
            record.update(native_emitted_tasks=1, final_task=str(final), final_bundle=final_bundle,
                          draft_matches_final=final_bundle["bundle_hash"] == record["draft_bundle"]["bundle_hash"])
        else:
            record["native_skip_reason"] = "harbor_packaging"
        record["status"] = "completed_native_export_stage"
    except Exception as exc:
        record.update(status="failed_no_repair", error_type=type(exc).__name__)
        raise
    finally:
        save_record(args.output / "summary.json", record)


if __name__ == "__main__":
    main()
