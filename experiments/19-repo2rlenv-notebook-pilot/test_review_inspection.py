"""Reviewer tools preserve reference identity and remain outside independent authoring."""

import asyncio
import hashlib
import json
import time

import pytest
from review_inspection import ReviewInspection


def snapshot(tmp_path):
    reference = tmp_path / "reference"
    trial = reference / "trial"
    trial.mkdir(parents=True)
    contents = {"trial/uv.lock": b"package = []\n", "trial/environment.txt": b""}
    for name, content in contents.items():
        (reference / name).write_bytes(content)
    outputs = tmp_path / "restored"
    outputs.mkdir()
    (outputs / "output.txt").write_bytes(b"ORIGINAL\n")
    return {
        "directory": reference,
        "hashes": {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()},
        "outputs": [
            {"path": "output.txt", "bytes": 9, "sha256": hashlib.sha256(b"ORIGINAL\n").hexdigest()}
        ],
        "restored_outputs_root": str(outputs),
    }


def test_reviewer_reads_only_bound_original_and_keeps_changed_bytes_an_evidence_gap(tmp_path):
    source = snapshot(tmp_path)
    inspection = ReviewInspection(source, tmp_path / "inspection", time.time() + 60)
    read = inspection.handlers["read_reference_file"]
    value = json.loads(asyncio.run(read(path="output.txt")))
    assert value["lines"] == [{"line": 1, "text": "ORIGINAL"}]
    assert inspection.context["inspection_evidence_sha256"] == source["hashes"]
    assert inspection.context["package_inspection"]["packages"] == {}
    assert json.loads((tmp_path / "inspection/identities.json").read_text()) == inspection.context
    (tmp_path / "restored/output.txt").write_bytes(b"MODIFIED\n")
    changed = json.loads(asyncio.run(read(path="output.txt")))
    assert "error" in changed and "lines" not in changed
    outside = json.loads(asyncio.run(read(path="../reference/trial/environment.txt")))
    assert "error" in outside and "lines" not in outside
    assert {tool["function"]["name"] for tool in inspection.tools} == set(inspection.handlers)
    assert not {"shell", "write_file", "exec"} & set(inspection.handlers)


@pytest.mark.parametrize("name", ["trial/uv.lock", "trial/environment.txt"])
def test_unbound_environment_cannot_select_review_sources(tmp_path, name):
    source = snapshot(tmp_path)
    (source["directory"] / name).write_text("altered\n")
    with pytest.raises(ValueError, match="identity changed"):
        ReviewInspection(source, tmp_path / "inspection", time.time() + 60)
    assert not (tmp_path / "inspection").exists()


def test_review_deadline_is_not_extended_by_inspection(tmp_path):
    inspection = ReviewInspection(snapshot(tmp_path), tmp_path / "inspection", time.time() - 1)
    with pytest.raises(TimeoutError):
        asyncio.run(inspection.handlers["read_reference_file"](path="output.txt"))


def test_input_samples_remain_bound_to_original_receipt_and_distinct_from_output(tmp_path):
    from grading_session import source_input_observations

    reference = tmp_path / "reference"
    (reference / "trial").mkdir(parents=True)
    path = reference / "trial/result.json"
    samples = {"files": [{"sha256": "a" * 64, "input_preview": {"text": "row1\t12\n"}}]}
    path.write_text(json.dumps({"input_observations": samples, "status": "reference_passed"}))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source = {"directory": reference, "hashes": {"trial/result.json": digest}}
    observed = source_input_observations(source)
    assert observed["status"] == "recorded" and observed["observations"] == samples
    assert observed["source"]["sha256"] == digest
    assert "not inferred schemas" in observed["scope"]
    path.write_text(json.dumps({"input_observations": {"forged": True}}))
    with pytest.raises(ValueError, match="identity changed"):
        source_input_observations(source)


def test_missing_input_samples_are_a_gap_not_a_schema_claim(tmp_path):
    from grading_session import source_input_observations

    observed = source_input_observations({"directory": tmp_path, "hashes": {}})
    assert observed["status"] == "unavailable" and "observations" not in observed
    assert "evidence gap" in observed["scope"]


def test_new_autonomous_grading_enables_inspection_with_existing_bounds():
    from run_autonomous import Pipeline

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.config = {"campaign": "synthetic"}
    pipeline.reasoning_effort = "high"
    config = pipeline.config_for("grading", "run_notebook_grader.py")
    assert config["inspect_review_evidence"] is True
    assert config["reference_seconds"] == 600 and config["verifier_seconds"] == 120
    assert config["request_timeout_seconds"] == 600 and config["max_requests"] is None
    assert "inspect_review_evidence" not in pipeline.config_for("setup", "run_reference_setup.py")


@pytest.mark.parametrize("value", [None, 0, 1, "true"])
def test_review_inspection_configuration_must_be_explicitly_boolean(value):
    from run_reference_setup import check_config

    with pytest.raises(ValueError, match="inspect_review_evidence must be boolean"):
        check_config({"reasoning_effort": "high", "inspect_review_evidence": value})


@pytest.mark.parametrize("semantic_feedback", [False, True])
def test_initial_and_repair_reviews_inspect_without_granting_tools_to_other_workers(
    tmp_path, monkeypatch, semantic_feedback
):
    from test_grading import test_orchestration_separates_probe_author_and_gates_acceptance

    test_orchestration_separates_probe_author_and_gates_acceptance(
        tmp_path,
        monkeypatch,
        repair=True,
        derived=True,
        resume=False,
        reuse_probes=False,
        contract_only=False,
        comparison_conflict=False,
        semantic_feedback=semantic_feedback,
        inspect_review=True,
    )
