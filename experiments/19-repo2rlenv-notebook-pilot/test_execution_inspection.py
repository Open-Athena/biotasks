"""Observed diagnostics remain inspectable without becoming fresh controls."""

import asyncio
import hashlib
import json
import time

import pytest
from execution_inspection import ExecutionInspection
from review_inspection import ReviewInspection
from test_review_inspection import snapshot


def record(root, number="0001", *, state="returned", stdout="boundary accepted\n"):
    directory = root / "operations" / number
    directory.mkdir(parents=True)
    argv = [
        "python",
        "-c",
        "from pathlib import Path; Path("
        + repr(str(root / "MUST_NOT_RUN"))
        + ").write_text('bad')",
    ]
    output = (json.dumps({"stdout": stdout, "stderr": "", "exit_code": 0}) + "\n").encode()
    operation = {
        "argv": argv,
        "state": state,
        "remote_label": "unique-" + number,
        "seconds": 20,
        "process": {
            "argv": argv,
            "label": "unique-" + number,
            "timeout_seconds": 20,
            "exit_code": 0,
            "timed_out": False,
            "log_sha256": hashlib.sha256(output).hexdigest(),
        },
    }
    (directory / "operation.json").write_text(json.dumps(operation))
    (directory / "output.log").write_bytes(output)
    return directory


def test_diagnostics_are_searchable_decoded_and_bound_to_originals(tmp_path):
    record(tmp_path)
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    found = json.loads(asyncio.run(reader.search_execution_evidence("boundary")))
    assert found["total_matching_lines"] == 2  # Raw JSON and decoded text, not two experiments.
    assert {x["section"] for x in found["matches"]} == {"stdout", "output"}
    value = json.loads(asyncio.run(reader.read_execution_evidence("author/0001", "stdout")))
    assert value["output_json_decoded"] and value["lines"][0]["text"] == "boundary accepted"
    assert value["operation"]["sha256"] and value["output"]["sha256"]
    assert value["decoded_output_metadata"]["exit_code"] == 0
    assert "not a complete acceptance-control inventory" in found["scope"]
    assert not (tmp_path / "MUST_NOT_RUN").exists()


@pytest.mark.parametrize("target", ["operation.json", "output.log"])
def test_modified_evidence_never_leaks_content(tmp_path, target):
    directory = record(tmp_path)
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    (directory / target).write_text("MODIFIED PRIVATE CONTENT")
    value = json.loads(
        asyncio.run(
            reader.handlers["read_execution_evidence"](operation_id="author/0001", section="stdout")
        )
    )
    assert "error" in value and "MODIFIED" not in json.dumps(value)
    assert "never ran" in value["scope"]


@pytest.mark.parametrize("defect", ["nonce", "argv", "hash"])
def test_inconsistent_completion_is_not_an_observation(tmp_path, defect):
    directory = record(tmp_path)
    path = directory / "operation.json"
    op = json.loads(path.read_text())
    op["process"][{"nonce": "label", "argv": "argv", "hash": "log_sha256"}[defect]] = "wrong"
    path.write_text(json.dumps(op))
    with pytest.raises(ValueError, match="completion receipt"):
        ExecutionInspection({"author": tmp_path}, time.time() + 60)


def test_unknown_operation_and_links_are_explicit_gaps(tmp_path):
    directory = record(tmp_path)
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    outside = tmp_path / "secret.txt"
    outside.write_text("PRIVATE")
    (directory / "output.log").unlink()
    (directory / "output.log").symlink_to(outside)
    for operation_id in ["author/0001", "../secret.txt"]:
        result = asyncio.run(
            reader.handlers["read_execution_evidence"](operation_id=operation_id, section="stdout")
        )
        assert "PRIVATE" not in result and "unavailable" in result
    with pytest.raises(ValueError, match="Linked"):
        ExecutionInspection({"author": tmp_path}, time.time() + 60)


def test_pending_operation_is_not_called_nonexistent_or_successful(tmp_path):
    record(tmp_path, state="uncertain")
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    assert not reader.catalog["author/0001"]["available"]
    assert "not disproved" in reader.catalog["author/0001"]["gap"]
    assert json.loads(asyncio.run(reader.search_execution_evidence("boundary")))["matches"] == []


def test_inner_failure_is_visible_despite_successful_outer_controller(tmp_path):
    directory = record(tmp_path)
    output = json.dumps({"stdout": "", "stderr": "inner failed", "exit_code": 7}).encode()
    (directory / "output.log").write_bytes(output)
    operation = json.loads((directory / "operation.json").read_text())
    operation["process"]["log_sha256"] = hashlib.sha256(output).hexdigest()
    (directory / "operation.json").write_text(json.dumps(operation))
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    result = json.loads(asyncio.run(reader.read_execution_evidence("author/0001", "stderr")))
    assert result["exit_code"] == 0  # Controller transport exited normally.
    assert result["decoded_output_metadata"]["exit_code"] == 7
    assert result["lines"][0]["text"] == "inner failed"


def test_binary_log_is_an_explicit_gap_not_a_false_negative(tmp_path):
    directory = record(tmp_path)
    output = b"\xff\xfe"
    (directory / "output.log").write_bytes(output)
    operation = json.loads((directory / "operation.json").read_text())
    operation["process"]["log_sha256"] = hashlib.sha256(output).hexdigest()
    (directory / "operation.json").write_text(json.dumps(operation))
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    assert reader.catalog["author/0001"]["gap"].startswith("Recorded binary output")
    assert not reader.catalog["author/0001"]["available"]


def test_prior_author_evidence_survives_a_repair_stage_boundary(tmp_path):
    original = tmp_path / "original"
    repair = tmp_path / "repair"
    record(original, stdout="earlier calibration\n")
    record(repair, stdout="repair observation\n")
    reader = ExecutionInspection({"prior1": original, "current": repair}, time.time() + 60)
    result = json.loads(asyncio.run(reader.search_execution_evidence("earlier calibration")))
    assert {row["operation_id"] for row in result["matches"]} == {"prior1/0001"}
    assert set(reader.catalog) == {"prior1/0001", "current/0001"}


@pytest.mark.parametrize("roots", [None, "old", [""], ["."], ["../old"], ["/old"], ["a//b"]])
def test_observation_config_cannot_grant_arbitrary_filesystem_access(roots):
    from run_reference_setup import check_config

    with pytest.raises(ValueError, match="Review observation directories"):
        check_config(
            {
                "reasoning_effort": "high",
                "entrypoint": "run_notebook_grader.py",
                "inspect_review_evidence": True,
                "review_observation_directories": roots,
            }
        )


def test_positive_windows_and_deadline_preserve_inspection_boundaries(tmp_path):
    record(tmp_path, stdout="alpha\n0123456789\nomega\n")
    reader = ExecutionInspection({"author": tmp_path}, time.time() + 60)
    value = json.loads(
        asyncio.run(reader.read_execution_evidence("author/0001", "stdout", 2, 2, 5, None))
    )
    assert value["lines"] == [{"line": 2, "text": "456789", "full_line_characters": 10}]
    reader.deadline = time.time() - 1
    with pytest.raises(TimeoutError):
        asyncio.run(reader.search_execution_evidence("boundary"))


def test_refresh_keeps_prior_manifests_and_refuses_rewritten_completed_evidence(tmp_path):
    source = snapshot(tmp_path)
    stage = tmp_path / "stage"
    first = record(stage)
    reviewer = ReviewInspection(source, tmp_path / "inspection", time.time() + 60)
    reviewer.refresh_execution_evidence({"current": stage})
    digest = reviewer.context["execution_inspection"]["manifest_sha256"]
    record(stage, "0002")
    reviewer.refresh_execution_evidence({"current": stage})
    assert digest != reviewer.context["execution_inspection"]["manifest_sha256"]
    assert len(list((tmp_path / "inspection/execution-manifests").glob("*.json"))) == 2
    assert {t["function"]["name"] for t in reviewer.tools} == set(reviewer.handlers)
    (first / "operation.json").unlink()
    with pytest.raises((ValueError, OSError)):
        reviewer.refresh_execution_evidence({"current": stage})
