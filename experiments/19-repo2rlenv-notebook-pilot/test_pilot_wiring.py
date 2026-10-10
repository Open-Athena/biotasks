"""Exercise actual input schemas and quotas without model or cloud dispatch."""

import json
import time
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
import run_pilot


def test_lost_newlines_stop_before_sandbox_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("GLM_BULK_TOKEN", "test-credential")
    responses = iter(['{"compatible":true}', '{"payload":"first linensecond line"}'])
    monkeypatch.setattr(
        run_pilot,
        "complete",
        lambda *a, **kw: SimpleNamespace(content=next(responses), usage={}),
    )
    monkeypatch.setattr(run_pilot, "Daytona", lambda: pytest.fail("Must not create a sandbox"))
    config = json.loads(Path(run_pilot.__file__).with_name("pilot-config.json").read_text())
    seed = tmp_path / "seed.json"
    seed.write_text("[]")
    with pytest.raises(RuntimeError, match="altered code-significant"):
        run_pilot.run(
            root=tmp_path / "run",
            endpoint="http://127.0.0.1:1/v1",
            worker_id="test-worker",
            deadline=time.time() + 7200,
            wheel=tmp_path / "fixture.whl",
            notebook_seed=seed,
            config=config,
        )
    assert (tmp_path / "run/escaping-compatibility.json").exists()


def test_failed_generation_is_preserved_without_quality_or_release(tmp_path, monkeypatch):
    monkeypatch.setenv("GLM_BULK_TOKEN", "test-credential")
    monkeypatch.setenv("BIOTASKS_IRIS_WORKER_ID", "test-worker")
    monkeypatch.setattr(
        run_pilot,
        "complete",
        lambda *a, **kw: SimpleNamespace(
            content=kw["user"].removeprefix("Return this exact object: ")
            if "payload" in kw["response_schema"]["properties"]
            else '{"compatible":true}',
            usage={},
        ),
    )
    monkeypatch.setattr(run_pilot, "Daytona", lambda: object())
    monkeypatch.setattr(
        run_pilot, "run_preflight", lambda *a, **kw: {"passed": True, "cleanup_verified": True}
    )
    observed = []

    def synthesis(spec, options, output, emit, **kwargs):
        from repo2rlenv.pipelines.recipes.catalog import get_recipe
        from repo2rlenv.pipelines.recipes.terminal.draft import TerminalDraft, emit_draft

        draft = TerminalDraft(
            environment_setup="",
            environment_files=[],
            instruction="Infrastructure fixture only; this is not a scientific task.",
            tests_python="\n".join(f"def test_{i}():\n    assert True\n" for i in range(5)),
            solution_shell="#!/bin/bash\n# infrastructure fixture only\ntrue\n",
            weights=[{"name": f"test_{i}", "weight": 0.2} for i in range(5)],
            self_review="Infrastructure fixture for timeout propagation only.",
        )
        task = emit_draft(
            draft,
            tmp_path / "emitter-check",
            name="timeout-fixture",
            org="tests",
            recipe=get_recipe("seta_seed2synth"),
            lineage={},
            timeout_sec=options.test_timeout_sec,
        )
        contract = tomllib.loads((task / "task.toml").read_text())
        assert contract["verifier"]["timeout_sec"] == 120
        assert contract["environment"]["build_timeout_sec"] <= 600
        assert contract["agent"]["timeout_sec"] <= 600
        observed.append((spec, options, kwargs))
        return SimpleNamespace(emitted=0, skipped=1, skip_reasons={"fixture": 1})

    monkeypatch.setattr(run_pilot, "run_synthesis", synthesis)
    monkeypatch.setattr(run_pilot, "QualityLoop", lambda *a, **kw: pytest.fail("No task to review"))
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps([{"question_text": "test source", "input_manifest": {}}]))
    config = json.loads(Path(run_pilot.__file__).with_name("pilot-config.json").read_text())
    result = run_pilot.run(
        root=tmp_path / "run",
        endpoint="http://127.0.0.1:1/v1",
        worker_id="test-worker",
        deadline=time.time() + 7200,
        wheel=tmp_path / "fixture.whl",
        notebook_seed=seed,
        config=config,
    )
    assert result == {"status": "generation_failed", "completion_requirements_met": False}
    spec, options, kwargs = observed[0]
    assert options.max_repairs == 2
    assert spec.execution.run_id == "notebook-pilot-001"
    assert kwargs["execution_adapter"].usage_ledger is not None
    assert (tmp_path / "run/generation-summary.json").exists()
    with pytest.raises(FileExistsError, match="never automatically relaunched"):
        run_pilot.run(
            root=tmp_path / "run",
            endpoint="unused",
            worker_id="test-worker",
            deadline=time.time() + 7200,
            wheel=tmp_path / "fixture.whl",
            notebook_seed=seed,
            config=config,
        )
