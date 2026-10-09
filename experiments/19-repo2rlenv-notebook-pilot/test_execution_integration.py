"""Control-plane tests only: no scientific candidate, model or sandbox calls."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from iris_execution import AttachedHost, IrisDaytonaExecution
from repo2rlenv.campaigns.budget import BudgetLedger
from repo2rlenv.emitter.bundle import TaskBundle, TaskFile, write_bundle
from repo2rlenv.execution import harbor
from repo2rlenv.spec.input import LLMSpec


def bundle(tmp_path, **overrides):
    return write_bundle(
        TaskBundle(
            name="control-plane-fixture",
            org="tests",
            instruction="Test fixture only.",
            files={
                "environment/Dockerfile": TaskFile.text("FROM python:3.12-slim\n"),
                "solution/solve.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
                "tests/test.sh": TaskFile.text("#!/bin/sh\ntrue\n", executable=True),
            },
            metadata={"recipe": "test", "recipe_version": "1", "reward_kinds": ["test_execution"]},
            **overrides,
        ),
        tmp_path / "tasks",
    )


def test_real_runner_forwards_host_credentials_and_preserves_offline_bundle(tmp_path, monkeypatch):
    task = bundle(tmp_path)
    original = (task / "task.toml").read_bytes()
    monkeypatch.setenv("DAYTONA_API_KEY", "FAKE_DAYTONA_SECRET")
    monkeypatch.setenv("PILOT_MODEL_KEY", "FAKE_MODEL_SECRET")
    worker = Mock(id="test-worker")
    launch = Mock()
    monkeypatch.setattr(harbor, "launch_job", launch)
    monkeypatch.setattr(harbor, "observe_job", lambda *a, **kw: {"state": "completed"})
    monkeypatch.setattr(harbor, "_collect_trial", lambda *a: None)
    model = LLMSpec(
        provider="openai",
        model="test-model",
        endpoint="https://test.example/v1",
        api_key_env="PILOT_MODEL_KEY",
        model_info={"max_input_tokens": 120000},
    )
    output = tmp_path / "trial"
    harbor.run_trial(
        worker,
        task,
        output,
        trial_id="test-run",
        agent="terminus-2",
        model=model,
        ledger=BudgetLedger(tmp_path / "budget.db", limit_usd="10"),
        environment="daytona",
        agent_timeout_sec=300,
        resource_overrides={"cpus": 1, "memory_mb": 2048, "storage_mb": 10240},
    )
    args, kwargs = launch.call_args
    command = args[2]
    assert command[command.index("--env") + 1] == "daytona"
    assert command[command.index("--agent-timeout-multiplier") + 1] == "0.5"
    for flag, value in (
        ("--override-cpus", "1"),
        ("--override-memory-mb", "2048"),
        ("--override-storage-mb", "10240"),
    ):
        assert command[command.index(flag) + 1] == value
    assert "api_base=https://test.example/v1" in command
    assert kwargs["env"]["OPENAI_API_KEY"] == "FAKE_MODEL_SECRET"
    assert kwargs["env"]["DAYTONA_API_KEY"] == "FAKE_DAYTONA_SECRET"
    assert "SECRET" not in (output / "trial.json").read_text()
    assert (task / "task.toml").read_bytes() == original


@pytest.mark.parametrize(
    "overrides",
    [
        {"environment": {"network_mode": "public"}},
        {"agent": {"network_mode": "public"}},
        {"verifier": {"network_mode": "public"}},
    ],
)
def test_daytona_rejects_network_expansion_before_dispatch(tmp_path, monkeypatch, overrides):
    task = bundle(tmp_path, **overrides)
    monkeypatch.setenv("DAYTONA_API_KEY", "FAKE")
    worker = Mock(id="test-worker")
    with pytest.raises(ValueError, match="offline"):
        harbor.run_trial(
            worker, task, tmp_path / "trial", trial_id="offline-test", environment="daytona"
        )
    worker.exec.assert_not_called()
    worker.upload.assert_not_called()


def test_adapter_bounds_attempts_including_uncertain_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOTASKS_IRIS_WORKER_ID", "test-worker")
    adapter = IrisDaytonaExecution(
        worker_id="test-worker",
        deadline=datetime.now(UTC) + timedelta(hours=1),
        records=tmp_path / "claims",
        max_trials=3,
        max_solver_attempts=2,
    )
    dispatch = Mock(side_effect=TimeoutError("uncertain"))
    monkeypatch.setattr(harbor, "run_trial", dispatch)
    for number in range(1):
        with pytest.raises(TimeoutError, match="uncertain"):
            adapter.run_trial(
                adapter.worker,
                Path("fixture"),
                tmp_path / str(number),
                trial_id=f"solve-{number}",
                agent="terminus-2",
            )
    with pytest.raises(RuntimeError, match="cleanup is unresolved"):
        adapter.run_trial(
            adapter.worker,
            Path("fixture"),
            tmp_path / "third",
            trial_id="solve-2",
            agent="terminus-2",
        )
    with pytest.raises(FileExistsError, match="reconcile"):
        adapter.run_trial(
            adapter.worker,
            Path("fixture"),
            tmp_path / "again",
            trial_id="solve-0",
            agent="terminus-2",
        )
    assert dispatch.call_count == 1
    assert all(call.kwargs["agent_timeout_sec"] == 300 for call in dispatch.call_args_list)


def test_host_guard_prevents_accidental_local_execution(monkeypatch):
    monkeypatch.delenv("BIOTASKS_IRIS_WORKER_ID", raising=False)
    with pytest.raises(RuntimeError, match="allocated"):
        AttachedHost("test-worker")


def test_transfer_paths_cannot_escape_owned_directories():
    with pytest.raises(ValueError, match="outside"):
        AttachedHost._remote("/work/../../etc/passwd")


@pytest.mark.parametrize("oracle_passes", [True, False])
def test_upstream_synthesis_uses_adapter_and_keeps_repair_bounds(
    tmp_path, monkeypatch, oracle_passes
):
    import json
    import sys
    from types import SimpleNamespace

    from repo2rlenv.pipelines.recipes.seta_seed2synth.recipe import TaskDesign
    from repo2rlenv.pipelines.recipes.terminal import runner
    from repo2rlenv.spec.input import GenerationInput
    from repo2rlenv.spec.recipe_options import TerminalSynthesisOptions

    campaign = tmp_path / "campaign"
    campaign.mkdir()
    BudgetLedger(campaign / "budget.sqlite3", limit_usd="10")
    input_spec = GenerationInput.model_validate(
        {
            "source": {"kind": "seeds", "path": str(tmp_path / "unused.json")},
            "pipeline": {"name": "terminal_synth", "recipe": "seta_seed2synth"},
            "llm": {"provider": "openai", "model": "test-model"},
            "output": {"destination": "local", "org": "tests", "dataset_name": "fixture"},
            "execution": {
                "worker_receipt": str(tmp_path / "unused-worker.json"),
                "runtime_wheel": str(tmp_path / "fixture.whl"),
                "campaign_dir": str(campaign),
                "run_id": "test-synthesis",
            },
        }
    )
    monkeypatch.setattr(runner, "check_runtime_wheel", lambda path: "a" * 64)
    connect = Mock(side_effect=AssertionError("Must not provision or connect a default worker"))
    monkeypatch.setattr(runner, "connect_worker", connect)
    worker = SimpleNamespace(id="test-worker")
    adapter = Mock()
    adapter.identity.return_value = {"adapter": "unit-fixture"}
    adapter.prepare.return_value = (worker, sys.executable, datetime.now(UTC) + timedelta(hours=1))
    adapter.run_trial.side_effect = lambda *args, **kwargs: harbor.TrialEvidence(
        reward=1.0 if kwargs["agent"] == "oracle" and oracle_passes else 0.0,
        exception_type=None,
        result=tmp_path / "fixture-result.json",
        cost_usd=0.0,
    )
    designer = Mock(
        return_value=TaskDesign(core_capabilities=["fixture"], draft_spec="fixture " * 20)
    )
    materializer = Mock(
        return_value=json.dumps(
            {
                "instruction": "A controller test fixture, never a scientific task.",
                "environment_setup": "RUN true",
                "environment_files": [
                    {"path": "input.txt", "content": "fixture", "executable": False}
                ],
                "tests_python": "\n".join(
                    f"def test_case_{n}():\n    assert True\n" for n in range(5)
                ),
                "solution_shell": "#!/bin/bash\nset -eu\ntrue\n",
                "weights": [{"name": f"test_case_{n}", "weight": 0.2} for n in range(5)],
                "self_review": "Unit fixture only; no scientific validity claimed.",
            }
        )
    )
    result = runner.run_synthesis(
        input_spec,
        TerminalSynthesisOptions(target=1, max_candidates=1, max_repairs=2),
        tmp_path / "out",
        lambda event: None,
        inputs=[{"source": "fixture", "title": "Fixture", "question_text": "fixture"}],
        designer=designer,
        materializer=materializer,
        execution_adapter=adapter,
    )
    assert designer.call_count == 1
    assert materializer.call_count == (1 if oracle_passes else 3)
    assert adapter.run_trial.call_count == (2 if oracle_passes else 6)
    assert result.emitted == int(oracle_passes)
    connect.assert_not_called()


def test_solver_attempts_use_separate_request_allowances(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOTASKS_IRIS_WORKER_ID", "test-worker")
    endpoints = ("http://127.0.0.1:1234/solver-1/v1", "http://127.0.0.1:1234/solver-2/v1")
    adapter = IrisDaytonaExecution(
        worker_id="test-worker",
        deadline=datetime.now(UTC) + timedelta(hours=1),
        records=tmp_path / "claims",
        max_trials=16,
        max_solver_attempts=2,
        solver_endpoints=endpoints,
    )

    def completed(worker, task, output, **kwargs):
        output.mkdir()
        (output / "remote-job.json").write_text(json.dumps({"cleanup": {"passed": True}}))

    dispatch = Mock(side_effect=completed)
    monkeypatch.setattr(harbor, "run_trial", dispatch)
    model = LLMSpec(provider="openai", model="fixture", api_key_env="KEY")
    for number in range(2):
        adapter.run_trial(
            adapter.worker,
            Path("fixture"),
            tmp_path / str(number),
            trial_id=f"solve-{number}",
            agent="terminus-2",
            model=model,
        )
    assert [call.kwargs["model"].endpoint for call in dispatch.call_args_list] == list(endpoints)
    assert model.endpoint is None
