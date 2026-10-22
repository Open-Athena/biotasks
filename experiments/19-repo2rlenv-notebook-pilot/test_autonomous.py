"""Control-flow tests use fake workers; never claim scientific validation evidence."""

import asyncio
import hashlib
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


def test_failed_operation_log_is_available_in_small_diagnostics(tmp_path):
    root = tmp_path / "run"
    failed = root / "setup-raw/operations/0001"
    successful = root / "setup-raw/operations/0002"
    for directory, code in [(failed, 1), (successful, 0)]:
        m.write(directory / "operation.json", {"state": "returned", "process": {"exit_code": code}})
        (directory / "output.log").write_text("diagnostic output")
    partial = root / "setup-raw/operations/0003/operation.json"
    partial.parent.mkdir(parents=True)
    partial.write_text('{"state":')
    destination = tmp_path / "diagnostics"
    m.copy_diagnostics(root, destination)
    assert (destination / "setup-raw/operations/0001/output.log").read_text() == "diagnostic output"
    assert (destination / "setup-raw/operations/0001/operation.json").is_file()
    assert not (destination / "setup-raw/operations/0002/output.log").exists()
    assert (
        destination / "setup-raw/operations/0003/operation.json"
    ).read_text() == partial.read_text()


def test_unresolved_comparison_is_returned_without_changing_original_evidence(tmp_path):
    root = tmp_path / "run"
    conflict = root / "grading/independent-comparison-conflict.json"
    m.write(conflict, {"status": "unresolved", "reference": "A", "independent": "B"})
    original = conflict.read_bytes()
    destination = tmp_path / "diagnostics"
    m.copy_diagnostics(root, destination)
    assert (destination / conflict.relative_to(root)).read_bytes() == original
    assert conflict.read_bytes() == original
    # Oversized records remain in the full archive, not the bounded log transport.
    conflict.write_bytes(b"x" * 256_001)
    m.copy_diagnostics(root, tmp_path / "bounded")
    assert not (tmp_path / "bounded" / conflict.relative_to(root)).exists()


def test_rejected_draft_feedback_is_preserved_in_failure_diagnostics(tmp_path):
    root = tmp_path / "run"
    draft = root / "preparation/prepare/artifact-stage/draft.json"
    m.write(draft, {"status": "unvalidated", "validation_error": "synthetic invalid artifact"})
    original = draft.read_bytes()
    destination = tmp_path / "diagnostics"
    m.copy_diagnostics(root, destination)
    assert (destination / draft.relative_to(root)).read_bytes() == original
    assert draft.read_bytes() == original


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "blocked",
        "infrastructure",
        "construction",
        "grading",
        "native",
        "question",
        "question-blocked",
        "question-failed",
        "question-used",
    ],
)
@pytest.mark.parametrize("reviewed", [False, True])
def test_orchestrator_preserves_terminal_distinctions(tmp_path, monkeypatch, failure, reviewed):
    monkeypatch.setattr(m, "HERE", tmp_path)
    monkeypatch.setenv("BIOTASKS_ARTIFACT_PREFIX", "private://fixture")
    monkeypatch.setenv("BIOTASKS_CONVERSION_PYTHON", "unused")
    source = tmp_path / "source.ipynb"
    source.write_text("fixture notebook")
    seed = {"source_sha256": m.digest(source), "provenance": {"id": "fixture"}}
    license_text = "Original fixture license"
    notices = {
        "source_provenance": seed["provenance"],
        "notebook_source_sha256": seed["source_sha256"],
        "notebook_license": {
            "text": license_text,
            "sha256": hashlib.sha256(license_text.encode()).hexdigest(),
        },
        "reviewed_inputs": [
            {
                "sha256": "b" * 64,
                "bytes": 123,
                "source_url": "https://example.org/data",
                "terms": "Fixture reviewed terms",
            }
        ],
    }
    m.write(tmp_path / "notices.json", notices)
    called = []

    def conversion(*args, **kwargs):
        intake = tmp_path / "run/intake"
        (intake / "baseline.py").write_text("x = 1\n")
        m.write(intake / "conversion.json", {})

    monkeypatch.setattr(m.subprocess, "run", conversion)

    async def prepare(config, *, root, **kwargs):
        assert config["reasoning_effort"] == "high"
        assert config["max_requests"] == 2
        called.append("prepare")
        if failure == "infrastructure":
            raise ConnectionError("transport")
        m.write(
            root / "plan.json", {"disposition": "blocked" if failure == "blocked" else "prepare"}
        )

    async def remote(config, *, root, **kwargs):
        assert config["reasoning_effort"] == "high"
        called.append(config["entrypoint"])
        if config["entrypoint"] == "run_reference_setup.py":
            m.write(root / "outcome.json", {"disposition": "tested"})
            return {}
        if config["entrypoint"] == "run_reference_replay.py":
            (root / "replay/trials/1/outputs").mkdir(parents=True)
            result = {
                "all_outputs_byte_identical_to_original": False,
                "status": "repeatability_observed_requires_comparison_review",
            }
            m.write(root / "result.json", result)
            return result
        if config.get("materialize_task"):
            if failure == "construction":
                m.write(root / "materialization-candidate.json", {"disposition": "blocked"})
                return {"status": "materialization_blocked"}
            (root / "materialized").mkdir(parents=True)
            return {"status": "materialized_requires_scientific_validation"}
        if failure == "grading":
            result = {"status": "independent_solution_blocked", "final_controls_passed": False}
            m.write(root / "result.json", result)
            return result
        if failure and failure.startswith("question"):
            if root.name == "grading":
                m.write(
                    root / "result.json",
                    {"status": "independent_comparison_unresolved", "cleanup_verified": True},
                )
                if failure == "question-used":
                    m.write(root / "repair.json", {"original": "already consumed"})
                return m.read(root / "result.json")
            assert root.name == "grading-question-repair"
            assert config["allow_quality_repair"] is False
            assert not any(key.startswith("resume_") for key in config)
            assert config["materialization_directory"].endswith("materialization-question-repair")
            assert (
                m.read(tmp_path / "run/grading/result.json")["status"]
                == "independent_comparison_unresolved"
            )
            assert m.read(tmp_path / config["frozen_grader_file"])["grader_candidate"] == {
                "grader": "unchanged"
            }
            assert m.os.environ["BIOTASKS_ARTIFACT_PREFIX"].endswith(
                "/stages/grading-question-repair"
            )
            if failure == "question-failed":
                m.write(root / "result.json", {"status": "independent_comparison_unresolved"})
                return m.read(root / "result.json")
        return {"status": "grader_candidate_validated", "final_controls_passed": True}

    async def specify(config, *, root, **kwargs):
        assert config["reasoning_effort"] == "high"
        called.append("specify")
        if config.get("question_repair"):
            assert config["inspect_packages"] and config["output_format"] == "tools"
            m.write(
                root / "question-repair.json",
                {
                    "disposition": "blocked" if failure == "question-blocked" else "ready",
                    "instruction": "Worker correction",
                    "rationale": "Worker evidence",
                },
            )
            return
        m.write(root / "specification.json", {"disposition": "draft_ready"})

    def native(config, *, root):
        assert config["reasoning_effort"] == "high"
        called.append("native")
        if failure == "question":
            assert config["grading_directory"].endswith("grading-question-repair")
            assert config["materialization_directory"].endswith("materialization-question-repair")
        recorded = m.read(tmp_path / config["attribution_file"])
        assert recorded == (
            notices
            if reviewed
            else {"notebook": seed, "publication_status": "Not assessed; local validated task only"}
        )
        return {"publication_ready": failure != "native"}

    for name, attrs in {
        "run_preparation": {"run": prepare},
        "run_reference_setup": {"run": remote},
        "run_specification": {"run": specify},
        "specification_inputs": {"specification_context": lambda *a, **k: {}},
        "run_scientific_native": {"run": native},
        "iris_bootstrap": {"export_on_host": lambda *a, **k: None},
    }.items():
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace(**attrs))
    monkeypatch.setattr(
        m, "seal_reference", lambda raw, view, seed: (view / "trial/outputs").mkdir(parents=True)
    )
    monkeypatch.setattr(m, "copy_diagnostics", lambda root: None)

    def seal_materialization(raw, view):
        view.mkdir()
        m.write(
            view / "manifest.json",
            {"inputs": [{"path": "data.dat", "sha256": "b" * 64, "bytes": 123}]},
        )

    monkeypatch.setattr(m, "seal_materialization", seal_materialization)
    if failure and failure.startswith("question"):
        import question_repair

        monkeypatch.setattr(
            question_repair,
            "repair_context",
            lambda *args: {"grader_candidate": {"grader": "unchanged"}},
        )

        def revision(original, destination, response):
            copytree(original, destination)
            m.write(destination / "candidate.json", {"instruction": response["instruction"]})

        monkeypatch.setattr(question_repair, "revise_question", revision)
    # Isolate fixed controller paths while exercising actual stage ordering.
    copytree = m.shutil.copytree

    def isolated_copy(source, target):
        if str(target).startswith("/work/"):
            target = tmp_path / "work" / str(target).removeprefix("/work/")
        return copytree(source, target)

    monkeypatch.setattr(m.shutil, "copytree", isolated_copy)
    copyfile = m.shutil.copyfile

    def isolated_file(source, target, **kwargs):
        if str(target).startswith("/evidence/"):
            target = tmp_path / "evidence" / str(target).removeprefix("/evidence/")
            target.parent.mkdir(parents=True, exist_ok=True)
        return copyfile(source, target, **kwargs)

    monkeypatch.setattr(m.shutil, "copyfile", isolated_file)
    pipeline = m.Pipeline(
        dict(
            campaign="fixture",
            factory_revision="test",
            notebook_file="source.ipynb",
            task_policy={},
            daytona_budget_usd="5",
            **({"source_notices_file": "notices.json"} if reviewed else {}),
        ),
        root=tmp_path / "run",
        seed=seed,
        deadline=time.time() + 7200,
        endpoint="unused",
        credential="unused",
    )
    if failure in {"infrastructure", "native"}:
        with pytest.raises(ConnectionError if failure == "infrastructure" else RuntimeError):
            asyncio.run(pipeline.execute())
    else:
        asyncio.run(pipeline.execute())
    receipt = m.read(tmp_path / "run/pipeline.json")
    assert (
        receipt["status"]
        == {
            None: "validated",
            "blocked": "rejected",
            "infrastructure": "infrastructure_failed",
            "construction": "rejected",
            "grading": "rejected",
            "native": "infrastructure_failed",
            "question": "validated",
            "question-blocked": "rejected",
            "question-failed": "rejected",
            "question-used": "rejected",
        }[failure]
    )
    if failure in {"blocked", "infrastructure"}:
        assert called == ["prepare"]
    elif failure and failure.startswith("question"):
        assert called.count("specify") == (1 if failure == "question-used" else 2)
        assert called.count("run_notebook_grader.py") == (
            2 if failure in {"question-blocked", "question-used"} else 3
        )
        if failure != "question-used":
            assert receipt["quality_repair"]["allowance_consumed"]
        else:
            assert "quality_repair" not in receipt
        assert receipt["daytona_reserved_usd"] == (5 if failure == "question" else 4)
        assert len(receipt["stages"]) == (7 if failure == "question" else 6)
    else:
        expected = [
            "prepare",
            "run_reference_setup.py",
            "run_reference_replay.py",
            "specify",
            "run_notebook_grader.py",
            "run_notebook_grader.py",
            "native",
        ]
        stop = {"construction": 5, "grading": 6}.get(failure, 7)
        assert called == expected[:stop]
        assert receipt["daytona_reserved_usd"] == stop - 2
    if failure in {"construction", "grading"}:
        assert receipt["rejection"]["stage"] == failure
        assert receipt["stages"][-1]["status"] == "rejected"
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
