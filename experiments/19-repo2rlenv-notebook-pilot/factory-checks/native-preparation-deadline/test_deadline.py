"""Exercise the real pinned runner with simulated preparation time, no providers."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, inspect_bundle, write_bundle
from repo2rlenv.execution import harbor as original
from repo2rlenv.execution.base import CommandResult
from repo2rlenv.spec.input import LLMSpec

HERE = Path(__file__).parent


@pytest.fixture
def candidate(tmp_path):
    identity = json.loads((HERE / "source-identity.json").read_text())
    source = Path(original.__file__).read_bytes()
    assert hashlib.sha256(source).hexdigest() == identity["baseline_patched_upstream_sha256"]
    root = tmp_path / "candidate"
    target = root / "src/repo2rlenv/execution/harbor.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(source)
    subprocess.run(
        [
            "patch",
            "-p1",
            "--batch",
            "--fuzz=0",
            "-i",
            str(HERE.parents[1] / "patches/0015-native-preparation-deadline.patch"),
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    assert (
        hashlib.sha256(target.read_bytes()).hexdigest()
        == identity["candidate_patched_upstream_sha256"]
    )
    name = "native_deadline_candidate"
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    del sys.modules[name]


def task(root):
    return write_bundle(
        TaskBundle(
            name="preparation-fixture",
            org="tests",
            instruction="Synthetic fixture only.",
            files={
                "environment/Dockerfile": TaskFile.text("FROM python:3.13-slim\n"),
                "environment/input.txt": TaskFile.text("synthetic input\n"),
                "solution/solve.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
                "tests/test.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
            },
            metadata={"recipe": "test", "recipe_version": "1", "reward_kinds": ["test_execution"]},
        ),
        root / "tasks",
    )


def exercise(
    module,
    monkeypatch,
    tmp_path,
    *,
    extract_seconds=45,
    upload_seconds=0,
    extract_fails=False,
    solver=False,
):
    clock = SimpleNamespace(seconds=1000.0)
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: clock.seconds))
    launch = Mock()
    observe = Mock(return_value={"state": "completed"})
    monkeypatch.setattr(module, "launch_job", launch)
    monkeypatch.setattr(module, "observe_job", observe)
    monkeypatch.setattr(module, "_collect_trial", lambda *args: "recorded evidence")
    calls = []

    class Worker:
        id = "synthetic-host"

        def exec(self, argv, *, timeout):
            calls.append((argv, timeout))
            if argv[:2] == ["tar", "-xzf"]:
                if extract_seconds > timeout:
                    raise subprocess.TimeoutExpired(argv, timeout)
                clock.seconds += extract_seconds
                if extract_fails:
                    return CommandResult(1, "", "synthetic unpack failure")
            return CommandResult(0, "", "")

        def upload(self, *_args):
            clock.seconds += upload_seconds

    source = task(tmp_path)
    before = inspect_bundle(source)
    result = None
    error = None
    options = {}
    if solver:
        monkeypatch.setenv("DAYTONA_API_KEY", "FAKE_DAYTONA")
        monkeypatch.setenv("PILOT_MODEL_KEY", "FAKE_MODEL")
        options = {
            "model": LLMSpec(
                provider="openai",
                model="test-model",
                endpoint="https://example.invalid/v1",
                api_key_env="PILOT_MODEL_KEY",
                model_info={"max_input_tokens": 262144},
            ),
            "ledger": BudgetLedger(tmp_path / "budget.sqlite", limit_usd="10"),
            "environment": "daytona",
            "agent_timeout_sec": 600,
            "resource_overrides": {"cpus": 4, "memory_mb": 8192, "storage_mb": 10240},
            "max_tokens": None,
            "max_turns": None,
        }
    try:
        result = module.run_trial(
            Worker(),
            source,
            tmp_path / "trial",
            trial_id="synthetic-native",
            agent="terminus-2" if solver else "oracle",
            timeout_sec=900,
            **options,
        )
    except Exception as caught:
        error = caught
    assert inspect_bundle(source) == before
    if not (tmp_path / "trial/trial.json").exists() and error is not None:
        raise error
    receipt = json.loads((tmp_path / "trial/trial.json").read_text())
    return result, error, calls, launch, observe, receipt


def test_original_short_unpack_timeout_reproduced(tmp_path, monkeypatch):
    result, error, calls, launch, _, _ = exercise(original, monkeypatch, tmp_path)
    assert result is None and isinstance(error, subprocess.TimeoutExpired)
    assert [timeout for argv, timeout in calls if argv[:2] == ["tar", "-xzf"]] == [30]
    launch.assert_not_called()


def test_candidate_uses_existing_trial_time_and_debits_preparation(
    candidate, tmp_path, monkeypatch
):
    result, error, calls, launch, observe, receipt = exercise(candidate, monkeypatch, tmp_path)
    assert error is None and result == "recorded evidence"
    assert [timeout for argv, timeout in calls if argv[:2] == ["tar", "-xzf"]] == [900]
    assert launch.call_count == 1 and launch.call_args.kwargs["timeout_sec"] == 855
    assert observe.call_args.kwargs["timeout_sec"] == 955  # Existing observation-only margin.
    assert receipt["timeout_sec"] == 900 and receipt["supervisor_timeout_sec"] == 855
    assert receipt["preparation_elapsed_seconds"] == 45 and receipt["trial_dispatched"]


@pytest.mark.parametrize("spent", [875, 901])
def test_preparation_cannot_reset_or_extend_trial_budget(candidate, tmp_path, monkeypatch, spent):
    result, error, calls, launch, observe, receipt = exercise(
        candidate, monkeypatch, tmp_path, extract_seconds=0, upload_seconds=spent
    )
    assert result is None and isinstance(error, TimeoutError)
    launch.assert_not_called()
    observe.assert_not_called()
    assert receipt["state"] == "interrupted" and receipt["trial_dispatched"] is False
    assert len([argv for argv, _ in calls if argv[:2] == ["tar", "-xzf"]]) == (
        1 if spent == 875 else 0
    )


def test_solver_limits_resources_and_route_survive_preparation(candidate, tmp_path, monkeypatch):
    result, error, _, launch, _, receipt = exercise(candidate, monkeypatch, tmp_path, solver=True)
    assert error is None and result == "recorded evidence"
    assert launch.call_count == 1 and launch.call_args.kwargs["timeout_sec"] == 855
    command = launch.call_args.args[2]
    for flag, value in (
        ("--env", "daytona"),
        ("--override-cpus", "4"),
        ("--override-memory-mb", "8192"),
        ("--override-storage-mb", "10240"),
        ("--agent-timeout-multiplier", "1.0"),
    ):
        assert command[command.index(flag) + 1] == value
    assert "api_base=https://example.invalid/v1" in command
    assert receipt["max_tokens"] is None and receipt["max_turns"] is None


def test_failed_extraction_never_launches_or_retries(candidate, tmp_path, monkeypatch):
    result, error, calls, launch, observe, receipt = exercise(
        candidate, monkeypatch, tmp_path, extract_fails=True
    )
    assert result is None and isinstance(error, RuntimeError)
    launch.assert_not_called()
    observe.assert_not_called()
    assert len([argv for argv, _ in calls if argv[:2] == ["tar", "-xzf"]]) == 1
    assert receipt["state"] == "interrupted" and receipt["trial_dispatched"] is False
