"""Replay the native CVE recipe with frozen public API inputs and offline tests.

Uses a declared historical Docker profile, not an LLM-built bootstrap. No model
or credential calls occur. Native filtering, patch split, validation and export
remain unchanged; API reads are replaced with checkpointed public responses.
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
from repo2rlenv.osv import OSVVuln
from repo2rlenv.pipelines import cve_patches, pr_runtime_validate
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import CVEPatchesOptions

PARENT = "ead54d7b2cca66226681ee37e355f7aa783881f2"
FIX = "736c96f37b190732ecca9da80ad0cb9d4967214d"
IMAGE = "biotasks21-biopython-cve"
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
            "repo": {"url": "https://github.com/biopython/biopython", "ref": PARENT},
            "pipeline": {"name": "cve_patches"},
            "output": {
                "destination": str(output / "tasks"),
                "org": "open-athena",
                "dataset_name": "biotasks21-cve",
            },
            "auth": {"use_gh_cli": False},
        }
    )
    options = CVEPatchesOptions(
        osv_ecosystem="PyPI", osv_package="biopython", limit=3, synthesize_poc_test=False
    )
    pipeline = cve_patches.CVEPatchesPipeline(spec, options, bootstrap)
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

    def parent(owner, name, sha, **kwargs):
        assert (owner, name, sha) == ("biopython", "biopython", FIX)
        return PARENT

    def diff(owner, name, sha, **kwargs):
        parent(owner, name, sha)
        return (inputs / "fix.diff").read_text()

    records = json.loads((inputs / "advisories.json").read_text())["records"]
    with (
        patch.object(cve_patches, "query_vulns", return_value=[OSVVuln(**r) for r in records]),
        patch.object(cve_patches, "fetch_commit_parent", new=parent),
        patch.object(cve_patches, "fetch_commit_diff", new=diff),
        patch.object(pipeline, "_start_validation_sandbox", new=offline_sandbox),
        patch.object(pr_runtime_validate, "validate_pr", new=validate),
    ):
        result = dataclasses.asdict(pipeline.run(output / "tasks"))
    result["out_dir"] = str(result["out_dir"])
    save_record(output / "result.json", result)


if __name__ == "__main__":
    main()
