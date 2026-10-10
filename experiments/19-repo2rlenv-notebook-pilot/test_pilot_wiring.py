"""Exercise actual input schemas and quotas without model or cloud dispatch."""

import json
import time
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
