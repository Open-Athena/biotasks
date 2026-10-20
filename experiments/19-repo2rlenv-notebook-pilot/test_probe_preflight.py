"""Invalid mutation scripts are repaired before freezing, without grader feedback."""

import asyncio
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import grading_remote as remote
import pytest
from grading_session import GradingSession
from test_grading import probe


@pytest.mark.parametrize(
    "script,valid",
    [
        ("from pathlib import Path\nPath('value.txt').write_text('wrong')", True),
        ("raise AssertionError('invalid mutation premise')", False),
        ("pass", False),
    ],
)
def test_probe_preflight_never_loads_or_executes_grader(
    tmp_path, monkeypatch, capsys, script, valid
):
    private = tmp_path / "private"
    oracle = private / "oracle"
    oracle.mkdir(parents=True)
    (oracle / "value.txt").write_text("right")
    expected = remote.hashes(oracle)
    (private / "expected.json").write_text(json.dumps(expected))
    (private / "request.json").write_text(
        json.dumps({"kind": "probe", "seconds": 10, "script": script})
    )
    # Deliberately no grade.py. Preflight cannot depend on a grader implementation.
    monkeypatch.setattr(remote, "PRIVATE", private)
    monkeypatch.setattr(remote, "CASE", tmp_path / "case")
    monkeypatch.setattr(remote.os, "chown", lambda *args: None)
    users = []

    def execute(uid, argv, cwd, seconds):
        users.append(uid)
        result = subprocess.run(
            [sys.executable, *argv[1:]], cwd=cwd, capture_output=True, text=True, timeout=seconds
        )
        return dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

    monkeypatch.setattr(remote, "run_as", execute)
    monkeypatch.setattr(sys, "argv", ["grading_remote.py", "probe-check"])
    remote.main()
    result = json.loads(capsys.readouterr().out)
    assert result["probe_valid_execution"] is valid
    assert (result["status"] == "probe_executed") is valid
    assert "grader" not in result and "report" not in result
    assert users == [remote.PROBE]
    assert remote.hashes(oracle) == expected


def test_controller_rejects_broken_probe_with_recoverable_execution_only_feedback(tmp_path):
    session = GradingSession(
        remote=SimpleNamespace(upload=AsyncMock()),
        snapshot={"outputs": [{"path": "value.txt"}]},
        root=tmp_path / "session",
        config={"verifier_seconds": 10},
    )
    broken = {"status": "incomplete", "probe_valid_execution": False, "probe": {"exit_code": 1}}
    fixed = {"status": "probe_executed", "probe_valid_execution": True, "probe": {"exit_code": 0}}
    session.helper = AsyncMock(side_effect=[broken, fixed])
    with pytest.raises(ValueError, match="repair its execution"):
        asyncio.run(session.validate_probe_execution(probe()))
    asyncio.run(session.validate_probe_execution(probe()))
    assert session.last_controls == [] and session.frozen_probes is None
    assert session.case_number == 0
    assert all(c.args[0] == ["probe-check"] for c in session.helper.call_args_list)
    assert len(list((session.root / "probe-validations").glob("*/result.json"))) == 2


def test_probe_recovery_config_requires_verified_grader_without_frozen_probes():
    from pathlib import Path

    from run_reference_setup import check_config

    config = json.loads((Path(__file__).parent / "grading-config.json").read_text())
    for key in (
        "resume_grading_directory",
        "resume_grader_draft_directory",
        "resume_probes_directory",
    ):
        config.pop(key, None)
    config["resume_probe_draft_directory"] = "prior"
    with pytest.raises(ValueError, match="requires full grader recovery"):
        check_config(config)
    config["resume_grading_directory"] = "prior"
    check_config(config)
    config["resume_probes_directory"] = "frozen"
    with pytest.raises(ValueError, match="no frozen probe resume"):
        check_config(config)
