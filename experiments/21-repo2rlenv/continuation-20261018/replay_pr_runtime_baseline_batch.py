"""Run frozen PRs with the existing unmodified repository baseline profile.

No compiled-extension restoration, per-task dependencies, fixtures, source edits,
statement rewrite or grader modifications. Native filters/validation/export own
the outcome. Frozen public provider inputs and resource isolation are plumbing.
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

from source_fetch_isolation import isolated_native_fetch

from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.github import PullRequestSummary
from repo2rlenv.pipelines import pr_runtime, pr_runtime_validate
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import PRRuntimeOptions


def run(inputs, output):
    manifest = json.loads((inputs / "manifest.json").read_text())
    assert manifest["repository"] == "scikit-bio/scikit-bio"
    assert manifest["prior_candidate_charge"] == 5
    candidates = manifest["candidates"]
    assert 1 <= len(candidates) <= 5 and len(set(candidates)) == len(candidates)
    original = manifest.get("original_selected_candidates", candidates)
    consumed = manifest.get("excluded_already_executed_candidates", [])
    assert original == [2638, 2637, 2635, 2634, 2632]
    assert len(set(consumed)) == len(consumed) and set(consumed) <= set(original)
    assert candidates == [number for number in original if number not in consumed]
    assert manifest["campaign_charge_after_selection"] == 10
    for name, record in manifest["files"].items():
        path = inputs / name
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size == record["bytes"]
        with path.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == record["sha256"]
    options = PRRuntimeOptions.model_validate(manifest["native_options"])
    assert not options.skip_validation and options.require_fail_to_pass
    assert options.limit == len(candidates) and options.validation_timeout_sec == 600
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    with (output / "build.log").open("w") as log:
        subprocess.run(["docker", "build", "--progress=plain", "-t", manifest["image_tag"], str(inputs)],
                       stdout=log, stderr=log, check=True, timeout=1800)
    digest = subprocess.check_output(["docker", "image", "inspect", manifest["image_tag"], "--format", "{{.Id}}"], text=True).strip()
    freeze = subprocess.check_output(["docker", "run", "--rm", "--network", "none", "--cpus", "0.1", "--memory", "128m",
                                      digest, "cat", "/opt/baseline-freeze.txt"], timeout=30)
    (output / "baseline-freeze.txt").write_bytes(freeze)
    dockerfile = (inputs / "Dockerfile").read_text()
    assert hashlib.sha256(dockerfile.encode()).hexdigest() == manifest["baseline_Dockerfile_sha256"]
    bootstrap = BootstrapResult(image_digest=digest, image_tag=manifest["image_tag"],
        language=LanguageHint.PYTHON, repo=manifest["repository"], ref=manifest["bootstrap_ref"],
        rebuild_cmds=[], test_cmds=[manifest["baseline_test_command"]], smoke_passed=False,
        iterations=0, build_time_sec=time.monotonic() - started,
        llm_provider="none; existing frozen repository baseline profile",
        dockerfile_reconstruction=dockerfile)
    save_record(output / "bootstrap.json", dataclasses.asdict(bootstrap))
    spec = GenerationInput.model_validate({"repo": {"url": "https://github.com/" + manifest["repository"], "ref": manifest["source_ref"]},
        "pipeline": {"name": "pr_runtime"}, "output": {"destination": str(output / "tasks"),
        "org": "open-athena", "dataset_name": "biotasks21-pr-baseline"}, "auth": {"use_gh_cli": False}})
    pipeline = pr_runtime.PRRuntimePipeline(spec, options, bootstrap)
    save_record(output / "recipe-options.json", options.model_dump(mode="json"))
    prs = [PullRequestSummary(**json.loads((inputs / f"pr{number}/pr.json").read_text())) for number in manifest["candidates"]]
    events = []

    def progress(**event):
        events.append(event)
        save_record(output / "cohort-summary.json", {"stage": "original_profile_native_PR_runtime_not_admission",
            "records": events, "model_calls": 0, "task_fixes": 0, "compiled_extension_restoration": False})

    pipeline.set_progress_callback(progress)
    start_sandbox = pipeline._start_validation_sandbox

    def offline_sandbox():
        sandbox = start_sandbox()
        try:
            subprocess.run(["docker", "network", "disconnect", "bridge", sandbox.container_id], check=True)
            subprocess.run(["docker", "update", "--cpus", "1", "--memory", "2048m", "--memory-swap", "2048m", sandbox.container_id], check=True)
            return sandbox
        except BaseException:
            sandbox.cleanup()
            raise

    class FrozenProvider:
        def list_merged_prs(self, owner, name, **kwargs):
            assert (owner, name) == ("scikit-bio", "scikit-bio")
            return prs

        def fetch_pr_diff(self, owner, name, number, **kwargs):
            assert (owner, name) == ("scikit-bio", "scikit-bio") and number in manifest["candidates"]
            return (inputs / f"pr{number}/pr.diff").read_text()

        def fetch_issue(self, owner, name, number, **kwargs):
            assert (owner, name) == ("scikit-bio", "scikit-bio")
            data = json.loads((inputs / f"issues/{number}.json").read_text())
            assert data["number"] == number
            return data["title"], data["body"]

    original_validate = pr_runtime_validate.validate_pr
    source_events = []

    def source_event(event):
        source_events.append(event)
        save_record(output / "source-fetch-isolation.json", {"events": source_events,
            "scope": "Native Git acquisition only; tests remain offline; no task/runtime asset repair"})

    fetch = isolated_native_fetch(pr_runtime_validate._fetch_base_commit,
                                 [pr.base_sha for pr in prs], source_event)
    validations = 0

    def validate(**kwargs):
        nonlocal validations
        validations += 1
        result = original_validate(**kwargs)
        save_record(output / f"validation-{validations:03d}.json", {
            "base_commit": kwargs.get("base_commit"), "outcome": dataclasses.asdict(result)})
        return result

    with patch.object(pr_runtime, "provider_for", return_value=FrozenProvider()), \
         patch.object(pipeline, "_start_validation_sandbox", new=offline_sandbox), \
         patch.object(pr_runtime_validate, "_fetch_base_commit", new=fetch), \
         patch.object(pr_runtime_validate, "validate_pr", new=validate):
        result = dataclasses.asdict(pipeline.run(output / "tasks"))
    result["out_dir"] = str(result["out_dir"])
    save_record(output / "result.json", result)
    progress(name="cohort", outcome="completed", reason="Native result recorded; no independent admission")


if __name__ == "__main__":
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Approved remote execution required")
    assert not os.environ.get("BIOTASKS21_GLM_KEY") and not os.environ.get("OPENAI_API_KEY")
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.output)
