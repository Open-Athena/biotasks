"""The paired experiment preserves original evidence and does not change rewards."""

import json
from pathlib import Path

import pytest
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, inspect_bundle, write_bundle
from run_roundtrip_diagnostic import VERIFY, diagnostic_bundle


def original_task(tmp_path):
    files = {
        "environment/Dockerfile": TaskFile.text("FROM example.invalid/frozen\n"),
        "environment/inputs/x.txt": TaskFile.text("input"),
        "solution/oracle.py": TaskFile.text("original reference"),
        "solution/solve.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
        "tests/grade.py": TaskFile.text("original grader"),
        "tests/checks.json": TaskFile.text('[{"id":"value"}]'),
        "tests/outputs.json": TaskFile.text('["result.txt"]'),
        "tests/reference/result.txt": TaskFile.text("original answer"),
        "tests/verify.py": TaskFile.text("original wrapper"),
        "tests/test.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
    }
    return write_bundle(
        TaskBundle(
            name="original",
            org="fixture",
            instruction="Public task",
            files=files,
            metadata={"recipe": "fixture", "recipe_version": "1", "reward_kinds": ["binary"]},
            environment={"network_mode": "no-network", "cpus": 4, "memory_mb": 8192},
        ),
        tmp_path / "original",
    )


def test_clone_changes_only_experiment_execution_and_reporting(tmp_path):
    original = original_task(tmp_path)
    before = inspect_bundle(original)
    result = diagnostic_bundle(
        original,
        tmp_path / "diagnostics",
        identity=before["bundle_hash"],
        code="GLM diagnostic",
        revision="frozen",
        name="paired",
    )
    assert inspect_bundle(original) == before
    assert inspect_bundle(result)["integrity_passed"]
    for file in original.rglob("*"):
        relative = file.relative_to(original).as_posix()
        if file.is_file() and relative not in {
            "task.toml",
            "solution/oracle.py",
            "tests/verify.py",
        }:
            assert (result / relative).read_bytes() == file.read_bytes()
    with pytest.raises(ValueError, match="exact original"):
        diagnostic_bundle(
            original,
            tmp_path / "invalid",
            identity="sha256:wrong",
            code="unused",
            revision="frozen",
            name="bad",
        )


@pytest.mark.parametrize("baseline,stored", [(True, False), (False, True), (True, True)])
def test_reports_preserve_both_outcomes_and_reward_only_baseline(
    tmp_path, monkeypatch, baseline, stored
):
    checks = tmp_path / "tests/checks.json"
    checks.parent.mkdir()
    checks.write_text('[{"id":"value"}]')
    verifier = tmp_path / "logs/verifier"
    outputs = tmp_path / "workspace/outputs"

    def fake_grader(command, *, check):
        assert check
        branch = Path(command[command.index("--submission-dir") + 1]).name
        passed = baseline if branch == "direct" else stored
        Path(command[-1]).write_text(
            json.dumps(
                {
                    "passed": passed,
                    "checks": [{"id": "value", "passed": passed}],
                }
            )
        )

    monkeypatch.setattr("subprocess.run", fake_grader)
    # Redirect only transport paths; no scientific program is executed locally.
    program = VERIFY.replace("/tests/checks.json", str(checks))
    program = program.replace("/logs/verifier", str(verifier))
    program = program.replace("/workspace/outputs", str(outputs))
    exec(compile(program, "diagnostic-wrapper", "exec"), {})
    report = json.loads((verifier / "report.json").read_text())
    assert report["baseline_matches_reference"] is baseline
    assert report["stored_matches_reference"] is stored
    assert report["original_solver_reward_changed"] is False
    assert (verifier / "reward.txt").read_text() == ("1\n" if baseline else "0\n")
