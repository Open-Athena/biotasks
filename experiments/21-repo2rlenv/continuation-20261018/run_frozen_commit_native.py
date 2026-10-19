"""Run a fixed commit cohort with one predeclared repository bootstrap profile.

The reusable profile was developed earlier; this is not the stock automatic
bootstrap route. No task-specific fixes, author calls or retries occur here.
"""

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines import commit_runtime, pr_runtime_validate
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import CommitRuntimeOptions


TEST_COMMAND = "cp -a /opt/skbio-baseline-extensions/. /workspace/ && cd /workspace && python -m pytest -o addopts= -v --tb=short"


def run_case(inputs, output, case):
    output.mkdir(parents=True, exist_ok=False)
    fix, parent = case["fix"], case["parent"]
    metadata = json.loads((inputs / case["metadata"]).read_text())
    assert metadata["sha"] == fix
    assert [p["sha"] for p in metadata["parents"]] == [parent]
    assert all(f["filename"].endswith(".py") or f["filename"] == "CHANGELOG.md" for f in metadata["files"])
    dockerfile = (inputs / "Dockerfile.template").read_text().replace("{{REPO_REF}}", parent)
    build = output / "bootstrap-input"
    build.mkdir()
    (build / "Dockerfile").write_text(dockerfile)
    image = "biotasks21-final-commit-" + fix[:12]
    started = time.monotonic()
    with (output / "build.log").open("w") as log:
        subprocess.run(["docker", "build", "--progress=plain", "-t", image, str(build)], stdout=log, stderr=log, check=True, timeout=1800)
    digest = subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Id}}"], text=True).strip()
    bootstrap = BootstrapResult(
        image_digest=digest, image_tag=image, language=LanguageHint.PYTHON,
        repo="scikit-bio/scikit-bio", ref=parent, rebuild_cmds=[],
        test_cmds=[TEST_COMMAND], smoke_passed=False, iterations=0,
        build_time_sec=time.monotonic() - started,
        llm_provider="none; existing predeclared repository profile",
        dockerfile_reconstruction=dockerfile,
    )
    save_record(output / "bootstrap.json", dataclasses.asdict(bootstrap))
    spec = GenerationInput.model_validate({
        "repo": {"url": "https://github.com/scikit-bio/scikit-bio", "ref": fix},
        "pipeline": {"name": "commit_runtime"},
        "output": {"destination": str(output / "tasks"), "org": "open-athena", "dataset_name": "biotasks21-commit"},
        "auth": {"use_gh_cli": False},
    })
    assert spec.llm is None
    options = CommitRuntimeOptions(limit=1, clone_depth=2, synthesize_with_llm=False)
    save_record(output / "recipe-options.json", options.model_dump(mode="json"))
    pipeline = commit_runtime.CommitRuntimePipeline(spec, options, bootstrap)
    start_sandbox = pipeline._start_validation_sandbox
    original_list = commit_runtime.list_commits
    original_validate = pr_runtime_validate.validate_pr

    def candidates(*args, **kwargs):
        values = original_list(*args, **kwargs)
        assert len(values) == 1 and values[0].sha == fix and values[0].parent_sha == parent
        assert values[0].message.strip() == metadata["commit"]["message"].strip()
        save_record(output / "candidates.json", [dataclasses.asdict(v) for v in values])
        return values

    def sandbox():
        value = start_sandbox()
        try:
            subprocess.run(["docker", "network", "disconnect", "bridge", value.container_id], check=True)
            subprocess.run(["docker", "update", "--cpus", "1", "--memory", "2048m", "--memory-swap", "2048m", value.container_id], check=True)
            return value
        except BaseException:
            value.cleanup()
            raise

    def validate(**kwargs):
        result = original_validate(**kwargs)
        save_record(output / "validation.json", dataclasses.asdict(result))
        return result

    with patch.object(commit_runtime, "list_commits", new=candidates), patch.object(pipeline, "_start_validation_sandbox", new=sandbox), patch.object(pr_runtime_validate, "validate_pr", new=validate):
        result = dataclasses.asdict(pipeline.run(output / "tasks"))
    result["out_dir"] = str(result["out_dir"])
    save_record(output / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("REPO2RLENV_REMOTE_WORKER") == "1"
    manifest = json.loads((args.inputs / "cohort.json").read_text())
    assert len(manifest["cases"]) == 2 and manifest["model_calls"] == 0
    for name, expected in manifest["files"].items():
        raw = (args.inputs / name).read_bytes()
        assert len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"]
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in manifest["cases"]:
        started = time.monotonic()
        row = {"fix": case["fix"], "status": "started", "task_specific_fixes": 0, "model_calls": 0}
        records.append(row)
        try:
            row.update(status="native_run_completed", native_result=run_case(args.inputs, args.output / case["fix"][:12], case))
        except Exception as exc:
            row.update(status="native_run_failed_no_repair", error_type=type(exc).__name__)
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save_record(args.output / "result.json", {"stage": "fixed_native_commit_cohort_not_admission", "records": records, "model_calls": 0, "new_candidate_charge": 0, "task_specific_fixes": 0})


if __name__ == "__main__":
    main()
