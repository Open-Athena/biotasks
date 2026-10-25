"""Generation-only infrastructure checks; no provider, Docker or Iris service."""

import importlib
import json
import sys
import types
from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace

import pytest

from biotasks.generation import resources
from biotasks.validation.files import ValidationError, sha, write_json


def load(name):
    data = resources.assets()
    if name + ".py" in data:
        module = types.ModuleType(name)
        module.__file__ = "bundled-asset:" + name + ".py"
        exec(compile(data[name + ".py"], module.__file__, "exec"), module.__dict__)
        return module
    return importlib.import_module("biotasks.generation." + name)


entry = load("generation_entry")
worker = load("generation_worker")
client = load("generation_client")


def test_original_model_call_is_forwarded_once_without_changes():
    recorder = SimpleNamespace(calls=0, actual_cost=Decimal(0))
    response, seen = object(), []

    def original(**kwargs):
        recorder.calls += 1
        seen.append(kwargs)
        return response

    price_guard = SimpleNamespace(wrap=lambda recorder, fn, maximum, prior: fn)
    guarded = entry.guard_completion(recorder, original, {"maximum_usd": "13.07"}, price_guard)
    messages = [{"role": "user", "content": "synthetic upstream bootstrap prompt"}]
    args = {
        "model": "openrouter/anthropic/claude-sonnet-4.6",
        "max_tokens": 2048,
        "temperature": 0.2,
        "num_retries": 0,
        "messages": messages,
    }
    assert guarded(**args) is response and seen == [args] and seen[0]["messages"] is messages
    for _ in range(19):
        guarded(**args)
    with pytest.raises(RuntimeError, match="count"):
        guarded(**args)
    assert len(seen) == 20


@pytest.mark.parametrize(
    "change",
    [
        {"num_retries": 1},
        {"temperature": 0.3},
        {"max_tokens": 4096},
        {"tools": [{"name": "extra"}]},
    ],
)
def test_changed_native_call_is_not_sent(change):
    recorder = SimpleNamespace(calls=0)
    guarded = entry.guard_completion(
        recorder,
        lambda **k: pytest.fail("No call permitted"),
        {"maximum_usd": "13.07"},
        SimpleNamespace(wrap=lambda r, fn, maximum, prior: fn),
    )
    args = {
        "model": "openrouter/anthropic/claude-sonnet-4.6",
        "max_tokens": 2048,
        "temperature": 0.2,
        "num_retries": 0,
        **change,
    }
    with pytest.raises(RuntimeError):
        guarded(**args)


class Entrypoint:
    def __init__(self, *, command, workdir_files, workdir_file_refs=None):
        self.command = command
        self.workdir_files = workdir_files
        self.workdir_file_refs = workdir_file_refs or {}


@dataclass
class Environment:
    env_vars: dict
    secret_behavior: str = "isolate"
    secrets: dict = field(default_factory=dict)


def test_primary_uses_isolated_named_secret_files_not_manifest_environment():
    submitted = []
    remote = SimpleNamespace(submit=lambda **kwargs: submitted.append(kwargs) or "fixed-job")
    proxy = client.GenerationClient(
        remote,
        {"GH_TOKEN": "synthetic-gh-sentinel", "OPENROUTER_API_KEY": "synthetic-model-sentinel"},
    )
    payload = {"generation_worker.py": b"synthetic"}
    original_entry = Entrypoint(
        command=[
            "bash",
            "-c",
            'PYTHONPATH="$IRIS_WORKDIR" exec "$IRIS_PYTHON" -u -m biotasks.validation.worker.job',
        ],
        workdir_files=payload,
    )
    original_env = Environment({"BIOTASKS_RUN_ID": "fixture"})
    assert (
        proxy.submit(entrypoint=original_entry, environment=original_env, max_retries_failure=0)
        == "fixed-job"
    )
    actual = submitted[0]
    assert actual["environment"].secret_behavior == "isolate"
    assert set(actual["environment"].secrets) == {"GH_TOKEN", "OPENROUTER_API_KEY"}
    assert actual["environment"].env_vars == {"BIOTASKS_RUN_ID": "fixture"}
    assert actual["entrypoint"].workdir_files is payload and actual["max_retries_failure"] == 0
    assert "generation_worker.py" in actual["entrypoint"].command[-1]
    assert not original_env.secrets and "synthetic-model-sentinel" not in repr(original_entry)


def test_unisolated_secret_delivery_is_rejected():
    remote = SimpleNamespace(submit=lambda **k: pytest.fail("No submission permitted"))
    proxy = client.GenerationClient(remote, {"GH_TOKEN": "a", "OPENROUTER_API_KEY": "b"})
    with pytest.raises(ValidationError):
        proxy.submit(
            entrypoint=Entrypoint(
                command=[
                    "bash",
                    "-c",
                    'PYTHONPATH="$IRIS_WORKDIR" exec "$IRIS_PYTHON" -u -m biotasks.validation.worker.job',
                ],
                workdir_files={},
            ),
            environment=Environment({}, secret_behavior="inherit"),
        )


def test_stop_precedes_seal_and_cleanup_is_deferred(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("IRIS_WORKER_ID", "fixture-worker")
    out, root = tmp_path / "out", tmp_path / "root"
    root.mkdir()
    out.mkdir()
    runner = worker.Generation(root, out, {"run_id": "fixture", "operation": "generate"})
    runner.tools.mkdir()
    (runner.tools / "docker").write_text("synthetic tool")
    runner.report.update(
        creation_started=True,
        controller_created=True,
        generation_started=True,
        configuration_verified=True,
        error="synthetic-secret-sentinel",
    )
    runner.secrets = {"OPENROUTER_API_KEY": "synthetic-secret-sentinel"}
    effects = []
    monkeypatch.setattr(
        runner, "stop_execution", lambda: effects.append("stop") or {"verified_stopped": True}
    )

    def docker(*args, **kwargs):
        effects.append(args)
        if args[0] == "cp":
            (out / "control-artifacts.tar.gz").write_bytes(
                b"synthetic archive, no native execution"
            )
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(runner, "docker", docker)
    runner.finish()
    tar_index = next(i for i, row in enumerate(effects) if isinstance(row, tuple) and "tar" in row)
    assert effects[0] == effects[-1] == "stop" and tar_index > 0
    assert not any(
        isinstance(row, tuple) and row[0] in {"rm", "volume", "image"} for row in effects
    )
    result = json.loads((out / "result.json").read_text())
    assert result["model_calls"] is None and result["stop"]["verified_stopped"]
    assert result["retained_resources"]["volume"] == "fixture-work"
    assert (
        "synthetic-secret-sentinel"
        not in (out / "result.json").read_text() + capsys.readouterr().out
    )


def test_worker_receives_only_named_credentials_and_binds_payload(tmp_path, monkeypatch):
    root, out = tmp_path / "root", tmp_path / "out"
    root.mkdir()
    out.mkdir()
    secrets = tmp_path / "mounted"
    secrets.mkdir()
    for key in ("GH_TOKEN", "OPENROUTER_API_KEY"):
        (secrets / key).write_text("synthetic-" + key)
        monkeypatch.delenv(key, raising=False)
    for key in ("GITHUB_TOKEN", "HF_TOKEN", "CW_KEY_ID", "CW_KEY_SECRET"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("RIGGING_SECRETS_DIR", str(secrets))
    for key in ("BIOTASKS_RUN_ID", "BIOTASKS_EXPECTED_WORKER", "IRIS_WORKER_ID"):
        monkeypatch.setenv(key, "fixture")
    names = [
        "generation_worker.py",
        "generation_entry.py",
        "native-config.json",
        "model-run-budget.json",
        "pins.json",
        "native_docker.py",
        "observed_cli.py",
        "provider_usage.py",
        "cost_guard.py",
        "setup_controller.sh",
        "upstream-source-manifest.json",
        "reference-candidates.json",
        "family.json",
    ]
    for name in names:
        (root / name).write_text("synthetic input")
    write_json(root / "model-run-budget.json", {"maximum_usd": "13.07"})
    write_json(root / "payload.json", {"sha256": {name: sha(root / name) for name in names}})
    config = {
        "operation": "generate",
        "run_id": "fixture",
        "resources": {"cpus": 4, "memory_gib": 16, "timeout_seconds": 5400},
        "model_budget": {"maximum_usd": "13.07"},
    }
    runner = worker.Generation(root, out, config)
    runner.validate()
    assert set(runner.secrets) == {"GH_TOKEN", "OPENROUTER_API_KEY"}
    assert runner.report["configuration_verified"] and runner.report["model_calls"] is None
    (root / "native_docker.py").write_text("changed source")
    with pytest.raises(ValidationError, match="payload changed"):
        worker.Generation(root, out, config).validate()


@pytest.mark.parametrize("interrupted", [False, True])
def test_targeting_override_restores_callback_after_native_exit(monkeypatch, interrupted):
    root = types.ModuleType("repo2rlenv")
    root.__path__ = []
    pipelines = types.ModuleType("repo2rlenv.pipelines")
    pipelines.__path__ = []
    runtime = types.ModuleType("repo2rlenv.pipelines.pr_runtime")
    original = lambda commands, files: commands  # noqa: E731
    vars(runtime)["targeted_test_cmds_for_pr"] = original
    vars(pipelines)["pr_runtime"] = runtime
    vars(root)["pipelines"] = pipelines
    for name, module in (
        ("repo2rlenv", root),
        ("repo2rlenv.pipelines", pipelines),
        ("repo2rlenv.pipelines.pr_runtime", runtime),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setitem(sys.modules, "python_targeting", load("python_targeting"))
    state = {}
    try:
        with entry.targeting_policy({"targeting_policy": "workspace-python-v1"}, state):
            assert vars(runtime)["targeted_test_cmds_for_pr"] is not original
            if interrupted:
                raise SystemExit(1)
    except SystemExit:
        assert interrupted
    assert vars(runtime)["targeted_test_cmds_for_pr"] is original
    assert state == {"targeting_policy": "workspace-python-v1", "targeting_policy_restored": True}


def test_default_targeting_policy_does_not_import_or_modify_native_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "python_targeting", None)
    state = {}
    with entry.targeting_policy({}, state):
        assert state == {"targeting_policy": None}
