"""Control-flow tests use fake workers; never claim scientific validation evidence."""

import asyncio
import importlib.util
import sys
import time
import types
from pathlib import Path

import pytest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("autonomous_test_module", HERE / "run_autonomous.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_worker_rejection_requires_explicit_disposition(tmp_path):
    path = tmp_path / "plan.json"
    m.write(path, {"disposition": "blocked", "reason": "No terminal result"})
    with pytest.raises(m.Rejected) as error:
        m.require_worker(path, "prepare", stage="preparation")
    assert error.value.evidence == str(path)
    m.write(path, {"disposition": "unknown"})
    with pytest.raises(ValueError):
        m.require_worker(path, "prepare", stage="preparation")


@pytest.mark.parametrize("failure", [None, "blocked", "infrastructure"])
def test_orchestrator_preserves_terminal_distinctions(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(m, "HERE", tmp_path)
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "private://fixture")
    monkeypatch.setenv("BIOTASKS_CONVERSION_PYTHON", "unused")
    source = tmp_path / "source.ipynb"
    source.write_text("fixture notebook")
    seed = {"source_sha256": m.digest(source)}
    called = []

    def conversion(*args, **kwargs):
        intake = tmp_path / "run/intake"
        (intake / "baseline.py").write_text("x = 1\n")
        m.write(intake / "conversion.json", {})

    monkeypatch.setattr(m.subprocess, "run", conversion)

    async def prepare(config, *, root, **kwargs):
        called.append("prepare")
        if failure == "infrastructure":
            raise ConnectionError("transport")
        m.write(root / "plan.json", {"disposition": "blocked" if failure else "prepare"})

    async def remote(config, *, root, **kwargs):
        called.append(config["entrypoint"])
        if config["entrypoint"] == "run_reference_setup.py":
            m.write(root / "outcome.json", {"disposition": "tested"})
            return {}
        if config["entrypoint"] == "run_reference_replay.py":
            (root / "replay/trials/1/outputs").mkdir(parents=True)
            return {"all_outputs_byte_identical_to_original": True}
        if config.get("materialize_task"):
            (root / "materialized").mkdir(parents=True)
            return {"status": "materialized_requires_scientific_validation"}
        return {"status": "grader_candidate_validated", "final_controls_passed": True}

    async def specify(config, *, root, **kwargs):
        called.append("specify")
        m.write(root / "specification.json", {"disposition": "draft_ready"})

    def native(config, *, root):
        called.append("native")
        return {"publication_ready": True}

    for name, attrs in {
        "run_preparation": {"run": prepare},
        "run_reference_setup": {"run": remote},
        "run_specification": {"run": specify},
        "specification_inputs": {"specification_context": lambda *a, **k: {}},
        "run_scientific_native": {"run": native},
        "iris_bootstrap": {"export_on_host": lambda *a, **k: None},
    }.items():
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace(**attrs))
    monkeypatch.setattr(m, "seal_reference", lambda raw, view, seed: view.mkdir())
    monkeypatch.setattr(m, "seal_materialization", lambda raw, view: view.mkdir())
    # Isolate fixed controller paths while exercising actual stage ordering.
    copytree = m.shutil.copytree

    def isolated_copy(source, target):
        if str(target).startswith("/work/"):
            target = tmp_path / "work" / str(target).removeprefix("/work/")
        return copytree(source, target)

    monkeypatch.setattr(m.shutil, "copytree", isolated_copy)
    copyfile = m.shutil.copyfile

    def isolated_file(source, target):
        if str(target) == "/evidence/autonomous-result.json":
            target = tmp_path / "receipt.json"
        return copyfile(source, target)

    monkeypatch.setattr(m.shutil, "copyfile", isolated_file)
    pipeline = m.Pipeline(
        dict(
            campaign="fixture",
            factory_revision="test",
            notebook_file="source.ipynb",
            task_policy={},
            daytona_budget_usd="5",
        ),
        root=tmp_path / "run",
        seed=seed,
        deadline=time.time() + 7200,
        endpoint="unused",
        credential="unused",
    )
    if failure == "infrastructure":
        with pytest.raises(ConnectionError):
            asyncio.run(pipeline.execute())
    else:
        asyncio.run(pipeline.execute())
    receipt = m.read(tmp_path / "run/pipeline.json")
    assert (
        receipt["status"]
        == {None: "validated", "blocked": "rejected", "infrastructure": "infrastructure_failed"}[
            failure
        ]
    )
    if failure:
        assert called == ["prepare"]
    else:
        assert called == [
            "prepare",
            "run_reference_setup.py",
            "run_reference_replay.py",
            "specify",
            "run_notebook_grader.py",
            "run_notebook_grader.py",
            "native",
        ]
        assert receipt["daytona_reserved_usd"] == 5
    assert receipt["operator_interventions"] == 0


def test_reference_handoff_checks_real_output_bytes(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    raw, view = tmp_path / "raw", tmp_path / "view"
    trial = raw / "setup/trials/1"
    (raw / "setup/frozen").mkdir(parents=True)
    (trial / "candidate").mkdir(parents=True)
    (trial / "outputs").mkdir()
    output = trial / "outputs/result.csv"
    output.write_text("id,value\na,1\n")
    inventory = [
        {
            "path": "result.csv",
            "exists": True,
            "bytes": output.stat().st_size,
            "sha256": m.digest(output),
        }
    ]
    m.write(
        raw / "result.json",
        {
            "status": "reference_executed_requires_review",
            "cleanup_verified": True,
            "last_passing_test": {"test": 1},
        },
    )
    m.write(raw / "outcome.json", {"disposition": "tested"})
    m.write(raw / "cleanup.json", {"passed": True})
    m.write(trial / "result.json", {"artifacts": {"artifacts": inventory}})
    m.seal_reference(raw, view, {"id": "fixture"})
    assert m.read(view / "artifact-manifest.json")["large_outputs"] == inventory
    assert m.read(view / "output-audit.json")["outputs"][0]["download_hash_verified"]
    output.write_text("id,value\na,2\n")
    with pytest.raises(ValueError, match="identity mismatch"):
        m.seal_reference(raw, tmp_path / "tampered-view", {"id": "fixture"})
