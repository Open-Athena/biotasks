"""Exercise native commit-runtime on the pinned scikit-bio Stockholm-reader fix.

Retain native Git mining, filters, validation, P2P cap and no-model instruction
fallback. Baseline compiled extensions are restored only for this pure-Python
patch, preserving the explicit profile already used for PR-runtime.
"""

import dataclasses
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from repo2rlenv.bootstrap.spec import BootstrapResult, LanguageHint
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.pipelines import commit_runtime, pr_runtime_validate
from repo2rlenv.spec.input import GenerationInput
from repo2rlenv.spec.options import CommitRuntimeOptions

PARENT = "f919ffd12668ed712c1e3f5c6e5ab0805a9b3936"
FIX = "02fe0c9d47e43ce3a5ce581b66904cd7529db2e2"
IMAGE = "biotasks21-skbio-stockholm-commit"
TEST = "cp -a /opt/skbio-baseline-extensions/. /workspace/ && cd /workspace && python -m pytest -o addopts= -v --tb=short skbio/io/format/tests/test_stockholm.py"


EXPECTED_FILES = {'skbio/io/format/stockholm.py', 'CHANGELOG.md', 'skbio/io/format/tests/test_stockholm.py'}
DIFF_SHA256 = '5cb8a2ada53e450a00f9755acc4a25d8abbd34702eb66207f3b21ec7aae3a1a2'


def comparable_diff(text):
    """Ignore only Git's abbreviated blob IDs and display-only hunk labels.

    Commit/parent IDs, file paths, modes, hunk ranges and every patch/context
    line still have to match. The native diff itself is never rewritten.
    """
    lines = []
    for line in text.splitlines(keepends=True):
        index = re.fullmatch(r'index ([0-9a-f]{7,40})\.\.([0-9a-f]{7,40})([^\n]*)(\n?)', line)
        hunk = re.fullmatch(r'(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)[^\n]*(\n?)', line)
        if index:
            line = 'index ' + index[1][:7] + '..' + index[2][:7] + index[3] + index[4]
        elif hunk:
            line = hunk[1] + hunk[2]
        lines.append(line)
    return ''.join(lines)


def check_inputs(directory):
    record = json.loads((directory/'stockholm-head-commit.json').read_text())
    parents = [p if isinstance(p, str) else p['sha'] for p in record['parents']]
    if record['sha'] != FIX or parents != [PARENT]:
        raise ValueError('Frozen commit identity differs')
    if {f['filename'] for f in record['files']} != EXPECTED_FILES:
        raise ValueError('Compiled restoration requires this exact pure-Python patch')
    if hashlib.sha256((directory/'stockholm-head-commit.diff').read_bytes()).hexdigest() != DIFF_SHA256:
        raise ValueError('Frozen public diff differs')
    return record


def main():
    if os.environ.get("REPO2RLENV_REMOTE_WORKER") != "1":
        raise RuntimeError("Run on the authorized remote worker only")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    inputs = args.inputs
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
    license_text = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--cpus', '1', '--memory', '128m', digest, 'cat', '/workspace/LICENSE.txt'], text=True, timeout=30)
    (output / 'source-LICENSE.txt').write_text(license_text)
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
        if values[0].message.strip() != frozen["commit"]["message"].strip():
            raise ValueError("Native mined message differs from frozen public metadata")
        save_record(output / "candidates.json", [dataclasses.asdict(v) for v in values])
        return values

    def diff(*args, **kwargs):
        value = original_diff(*args, **kwargs)
        (output / "commit.diff").write_text(value)
        expected = (inputs / 'stockholm-head-commit.diff').read_text()
        same = comparable_diff(value) == comparable_diff(expected)
        save_record(output / 'commit-diff-equivalence.json', {
            'native_diff_sha256': hashlib.sha256(value.encode()).hexdigest(),
            'public_API_diff_sha256': hashlib.sha256(expected.encode()).hexdigest(),
            'canonical_patch_sha256': hashlib.sha256(comparable_diff(value).encode()).hexdigest(),
            'same_paths_modes_hunk_ranges_and_all_patch_lines': same,
            'ignored_display_fields': ['blob-hash abbreviation length beyond seven characters', 'hunk function/class display label'],
            'native_patch_rewritten': False,
        })
        if not same:
            raise ValueError('Native/public commit patch content differs beyond display fields')
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
