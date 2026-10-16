"""Exercise native commit-runtime on the same pinned fix as the CVE replay.

Native Git mining, filters, before/after validation, P2P cap and no-model
instruction fallback are retained. This matched replay is not a new independent
biological problem. No model calls or credential-bearing task processes.
"""

import dataclasses
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

PARENT = "ead54d7b2cca66226681ee37e355f7aa783881f2"
FIX = "736c96f37b190732ecca9da80ad0cb9d4967214d"
IMAGE = "biotasks21-biopython-commit"
TEST = "cd /workspace/Tests && python -m pytest -o addopts= -v --tb=short ./test_Entrez_parser.py"


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
        repo="biopython/biopython",
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
            "repo": {"url": "https://github.com/biopython/biopython", "ref": FIX},
            "pipeline": {"name": "commit_runtime"},
            "output": {
                "destination": str(output / "tasks"),
                "org": "open-athena",
                "dataset_name": "biotasks21-commit",
            },
            "auth": {"use_gh_cli": False},
        }
    )
    options = CommitRuntimeOptions(limit=1, clone_depth=2)
    pipeline = commit_runtime.CommitRuntimePipeline(spec, options, bootstrap)
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

    original_list = commit_runtime.list_commits
    original_diff = commit_runtime.show_diff

    def candidates(*args, **kwargs):
        values = original_list(*args, **kwargs)
        if len(values) != 1 or values[0].sha != FIX or values[0].parent_sha != PARENT:
            raise ValueError("Commit walk did not match the frozen single-fix cohort")
        save_record(output / "candidates.json", [dataclasses.asdict(v) for v in values])
        return values

    def diff(*args, **kwargs):
        value = original_diff(*args, **kwargs)
        (output / "commit.diff").write_text(value)
        return value

    with (
        patch.object(commit_runtime, "list_commits", new=candidates),
        patch.object(commit_runtime, "show_diff", new=diff),
        patch.object(pipeline, "_start_validation_sandbox", new=offline_sandbox),
        patch.object(pr_runtime_validate, "validate_pr", new=validate),
    ):
        result = dataclasses.asdict(pipeline.run(output / "tasks"))
    result["out_dir"] = str(result["out_dir"])
    save_record(output / "result.json", result)


if __name__ == "__main__":
    main()
