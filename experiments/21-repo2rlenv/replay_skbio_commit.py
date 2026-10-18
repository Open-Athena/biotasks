"""Exercise native commit-runtime on the pinned scikit-bio string-column fix.

Retain native Git mining, filters, validation, P2P cap and no-model instruction
fallback. Baseline compiled extensions are restored only for this pure-Python
patch, preserving the explicit profile already used for PR-runtime.
"""

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

PARENT = "2d071fdfa75037d6da24ca0a4f00eaa7c568cbf1"
FIX = "71912bf097087f23e97ae8f11d234d0d5286f6ae"
IMAGE = "biotasks21-skbio-commit"
TEST = "cp -a /opt/skbio-baseline-extensions/. /workspace/ && cd /workspace && python -m pytest -o addopts= -v --tb=short skbio/stats/composition/tests/test_utils.py"


EXPECTED_FILES = {'CHANGELOG.md', 'skbio/stats/composition/_ancombc.py',
                  'skbio/stats/composition/_dirmult.py', 'skbio/stats/composition/_utils.py',
                  'skbio/stats/composition/tests/test_utils.py'}
DIFF_SHA256 = '39752db1ddb4328dc6004cfc6599b3d07426dad061bcb4671757a338d9808a51'


def check_inputs(directory):
    record = json.loads((directory/'commit-71912.json').read_text())
    parents = [p if isinstance(p, str) else p['sha'] for p in record['parents']]
    if record['sha'] != FIX or parents != [PARENT]:
        raise ValueError('Frozen commit identity differs')
    if {f['filename'] for f in record['files']} != EXPECTED_FILES:
        raise ValueError('Compiled restoration requires this exact pure-Python patch')
    if hashlib.sha256((directory/'commit-71912.diff').read_bytes()).hexdigest() != DIFF_SHA256:
        raise ValueError('Frozen public diff differs')
    return record


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Run on the authorized remote worker only")
    output = Path("/evidence/native")
    output.mkdir(parents=True, exist_ok=True)
    inputs = Path("/work/native")
    frozen = check_inputs(inputs)
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
    for filename in ('baseline-freeze.txt', 'skbio-baseline-extension-sha256.txt'):
        recorded = subprocess.check_output(
            ['docker', 'run', '--rm', '--network', 'none', '--cpus', '1',
             '--memory', '128m', digest, 'cat', '/opt/' + filename],
            text=True, timeout=30)
        (output/filename).write_text(recorded)
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
            "pipeline": {"name": "commit_runtime"},
            "output": {
                "destination": str(output / "tasks"),
                "org": "open-athena",
                "dataset_name": "biotasks21-commit",
            },
            "auth": {"use_gh_cli": False},
        }
    )
    assert spec.llm is None, "This replay must not make model calls"
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
        if values[0].message.strip() != frozen["message"].strip():
            raise ValueError("Native mined message differs from frozen public metadata")
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
