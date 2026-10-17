"""Replay a frozen public PR through native filters, validation and export.

Provider reads are replaced with pinned public responses for a matched cohort.
Generation and grading logic remain native; this is not independent problem diversity.
"""

import dataclasses
import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.github import PullRequestSummary
from repo2rlenv.pipelines import pr_runtime, pr_runtime_validate
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import PRRuntimeOptions

PARENT = "71286a24bddff66c82cb25a7ca13441aa13c2f2c"
FIX = "4c07596c68e8e6c1f51f5ea917e642e933802aa7"
IMAGE = "biotasks21-skbio-pr"
TEST = "cd /workspace && python -m pytest -o addopts= -v --tb=short skbio/stats/composition/tests/test_ancombc.py"


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Run on the authorized remote worker only")
    output = Path("/evidence/native")
    output.mkdir(parents=True, exist_ok=True)
    inputs = Path("/work/native")
    started = time.monotonic()
    with (output / "build.log").open("w") as log:
        subprocess.run(
            ["docker", "build", "--progress=plain", "-t", IMAGE, str(inputs)],
            stdout=log,
            stderr=log,
            check=True,
            timeout=1800,
        )
    digest = subprocess.check_output(
        ["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"], text=True
    ).strip()
    bootstrap = BootstrapResult(
        image_digest=digest,
        image_tag=IMAGE,
        language=LanguageHint.PYTHON,
        repo="scikit-bio/scikit-bio",
        ref=PARENT,
        rebuild_cmds=[],
        test_cmds=[TEST],
        smoke_passed=False,
        iterations=0,
        build_time_sec=time.monotonic() - started,
        llm_provider="none; explicit Docker profile",
        dockerfile_reconstruction=(inputs / "Dockerfile").read_text(),
    )
    save_record(output / "bootstrap.json", dataclasses.asdict(bootstrap))
    spec = GenerationInput.model_validate(
        {
            "repo": {"url": "https://github.com/scikit-bio/scikit-bio", "ref": FIX},
            "pipeline": {"name": "pr_runtime"},
            "output": {
                "destination": str(output / "tasks"),
                "org": "open-athena",
                "dataset_name": "biotasks21-pr",
            },
            "auth": {"use_gh_cli": False},
        }
    )
    options = PRRuntimeOptions(limit=1)
    pipeline = pr_runtime.PRRuntimePipeline(spec, options, bootstrap)
    save_record(output / "recipe-options.json", options.model_dump(mode="json"))
    start_sandbox = pipeline._start_validation_sandbox

    def offline_sandbox():
        sandbox = start_sandbox()
        try:
            subprocess.run(
                ["docker", "network", "disconnect", "bridge", sandbox.container_id],
                check=True,
            )
            subprocess.run(
                [
                    "docker",
                    "update",
                    "--cpus",
                    "1",
                    "--memory",
                    "2048m",
                    "--memory-swap",
                    "2048m",
                    sandbox.container_id,
                ],
                check=True,
            )
            return sandbox
        except BaseException:
            sandbox.cleanup()
            raise

    original_validate = pr_runtime_validate.validate_pr

    def validate(**kwargs):
        result = original_validate(**kwargs)
        save_record(output / "validation.json", dataclasses.asdict(result))
        return result

    pr = PullRequestSummary(**json.loads((inputs / "pr2633.json").read_text()))
    issue = json.loads((inputs / "issue2631.json").read_text())
    diff = (inputs / "pr2633.diff").read_text()
    if pr.number != 2633 or pr.base_sha != PARENT or issue["number"] != 2631:
        raise ValueError("Frozen cohort mismatch")

    class FrozenProvider:
        def list_merged_prs(self, owner, name, **kwargs):
            assert (owner, name) == ("scikit-bio", "scikit-bio")
            return [pr]

        def fetch_pr_diff(self, owner, name, number, **kwargs):
            assert (owner, name, number) == ("scikit-bio", "scikit-bio", 2633)
            return diff

        def fetch_issue(self, owner, name, number, **kwargs):
            assert (owner, name, number) == ("scikit-bio", "scikit-bio", 2631)
            return issue["title"], issue["body"]

    save_record(output / "candidate.json", dataclasses.asdict(pr))
    with (
        patch.object(pr_runtime, "provider_for", return_value=FrozenProvider()),
        patch.object(pipeline, "_start_validation_sandbox", new=offline_sandbox),
        patch.object(pr_runtime_validate, "validate_pr", new=validate),
    ):
        result = dataclasses.asdict(pipeline.run(output / "tasks"))
    result["out_dir"] = str(result["out_dir"])
    save_record(output / "result.json", result)


if __name__ == "__main__":
    main()
