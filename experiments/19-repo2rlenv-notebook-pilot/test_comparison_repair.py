"""Comparison repairs preserve frozen science and isolate public-only feedback."""

import copy
import json
from pathlib import Path

import pytest
from comparison_repair import (
    ComparisonRepair,
    freeze_comparison_revision,
    independent_repair_record,
    independent_worker_feedback,
    load_comparison_revision,
    validate_diagnosis,
)
from pydantic import ValidationError


@pytest.fixture
def context():
    return {
        "materialization_candidate": {
            "instruction": "Compute the arithmetic mean of the supplied values.",
            "oracle_code": "PRIVATE_ORACLE",
            "input_paths": ["data.csv"],
            "output_paths": ["result.csv"],
        },
        "grader_candidate": {"grader_code": "PRIVATE_GRADER", "checks": ["frozen"]},
        "independent_solution": {"code": "def compute(values):\n    return sum(values)\n"},
        "controls": {"private_expected_value": "PRIVATE_ANSWER"},
    }


def diagnosis(**changes):
    return ComparisonRepair(
        **(
            {
                "disposition": "ready",
                "target": "independent_solution",
                "instruction": None,
                "independent_issues": [
                    {
                        "public_requirement_quote": "arithmetic mean",
                        "prior_code_quote": "return sum(values)",
                    }
                ],
                "rationale": "PRIVATE_DIAGNOSIS_AND_MEASUREMENTS",
            }
            | changes
        )
    )


def test_only_public_requirement_and_prior_code_reach_independent_worker(context):
    before = copy.deepcopy(context)
    record = independent_repair_record(context, diagnosis())
    feedback = independent_worker_feedback(
        record, context["materialization_candidate"], context["grader_candidate"]
    )
    assert context == before
    assert set(feedback) == {"prior_code", "issues"}
    assert feedback["prior_code"] == context["independent_solution"]["code"]
    assert "PRIVATE_" not in json.dumps(feedback)
    assert "rationale" not in json.dumps(feedback)
    assert record["materialization_candidate"] == before["materialization_candidate"]
    assert record["grader_candidate"] == before["grader_candidate"]


def test_semantic_question_evidence_cannot_request_independent_code_changes(context):
    context["allowed_targets"] = ["public_question"]
    with pytest.raises(ValueError, match="recorded repair targets"):
        validate_diagnosis(diagnosis(), context)
    corrected = diagnosis(
        target="public_question", instruction="Source-defined question", independent_issues=[]
    )
    assert validate_diagnosis(corrected, context).target == "public_question"


@pytest.fixture
def mixed_context(context):
    from test_grading import candidate, probe

    prior = candidate().model_dump()
    context["grader_candidate"] = prior
    context["original_probes"] = {
        "disposition": "ready",
        "probes": [
            probe().model_dump(),
            probe(name="format", kind="valid_alternative").model_dump(),
        ],
        "concerns": ["Original recorded concern"],
    }
    context["allowed_targets"] = ["public_question"]
    return context


def joint_diagnosis():
    return diagnosis(
        target="public_question",
        instruction="Complete source-backed corrected question",
        independent_issues=[],
        grader_repair={
            "disposition": "ready",
            "instruction": "Corrected acceptance explanation; unchanged scientific criterion",
            "grader_code": "def compare(a, b):\n    return a == b\n",
            "rationale": "Fix both recorded defects in the same quality iteration",
        },
    )


@pytest.mark.parametrize("joint", [False, True])
def test_question_revision_retains_every_probe_and_binds_grader_inventory(mixed_context, joint):
    before = copy.deepcopy(mixed_context)
    response = joint_diagnosis()
    if not joint:
        response.grader_repair = None
    revised_question = {**before["materialization_candidate"], "instruction": response.instruction}
    frozen = freeze_comparison_revision(revised_question, mixed_context, response)
    grader, probes = load_comparison_revision(frozen)
    assert mixed_context == before
    assert frozen["materialization_candidate"] == revised_question
    assert probes.model_dump() == before["original_probes"]
    assert [c.model_dump() for c in grader.checks] == before["grader_candidate"]["checks"]
    assert grader.grader_code == (
        response.grader_repair.grader_code if joint else before["grader_candidate"]["grader_code"]
    )
    frozen["grader_candidate"]["checks"][0]["artifacts"] = ["another-output"]
    with pytest.raises(ValueError, match="bound grader edits"):
        load_comparison_revision(frozen)


def test_joint_revision_cannot_add_checks_change_mutations_or_bypass_blind_boundary(mixed_context):
    response = joint_diagnosis().model_dump()
    response["grader_repair"]["checks"] = []
    with pytest.raises(ValidationError):
        validate_diagnosis(response, mixed_context)
    response = joint_diagnosis().model_dump()
    response["grader_repair"]["probe_replacements"] = [{"script": "pass"}]
    with pytest.raises(ValidationError):
        validate_diagnosis(response, mixed_context)
    with pytest.raises(ValidationError, match="ready question repair"):
        diagnosis(grader_repair=joint_diagnosis().grader_repair)
    mixed_context.pop("original_probes")
    with pytest.raises(ValueError, match="retained original probe"):
        validate_diagnosis(joint_diagnosis(), mixed_context)


def test_joint_revision_executes_new_grader_without_reusing_old_acceptance(mixed_context, tmp_path):
    import subprocess
    import sys

    from test_grading import CODE

    # The original byte comparator rejects a different encoding of the same
    # numeric result. The complete revised program must actually replace it;
    # a question-only revision would leave the legitimate alternative failing.
    numeric = CODE.replace(
        "(Path(a.reference_dir)/'value.txt').read_text()==(Path(a.submission_dir)/'value.txt').read_text()",
        "float((Path(a.reference_dir)/'value.txt').read_text())==float((Path(a.submission_dir)/'value.txt').read_text())",
    )
    response = joint_diagnosis()
    response.grader_repair.grader_code = numeric
    frozen = freeze_comparison_revision(
        mixed_context["materialization_candidate"], mixed_context, response
    )
    revised, _ = load_comparison_revision(frozen)
    reference, submission = tmp_path / "reference", tmp_path / "submission"
    reference.mkdir()
    submission.mkdir()
    (reference / "value.txt").write_text("1")

    def execute(code, value):
        (submission / "value.txt").write_text(value)
        program, report = tmp_path / "grade.py", tmp_path / "report.json"
        program.write_text(code)
        subprocess.run(
            [
                sys.executable,
                str(program),
                "--reference-dir",
                str(reference),
                "--submission-dir",
                str(submission),
                "--report",
                str(report),
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )
        return json.loads(report.read_text())["passed"]

    assert not execute(CODE, "1.0\n")
    assert execute(revised.grader_code, "1.0\n")
    assert not execute(revised.grader_code, "2.0\n")
    assert mixed_context["grader_candidate"]["grader_code"] == CODE


@pytest.mark.parametrize(
    "field,value",
    [
        ("public_requirement_quote", "PRIVATE_ANSWER"),
        ("public_requirement_quote", " "),
        ("prior_code_quote", "replacement implementation"),
        ("prior_code_quote", "\n"),
    ],
)
def test_feedback_quotes_cannot_invent_private_or_replacement_information(context, field, value):
    response = diagnosis().model_dump()
    response["independent_issues"][0][field] = value
    with pytest.raises(ValueError, match="quote"):
        validate_diagnosis(response, context)


@pytest.mark.parametrize("field", ["materialization_candidate", "grader_candidate"])
def test_feedback_rejects_other_scientific_artifacts(context, field):
    record = independent_repair_record(context, diagnosis())
    record[field] = {"changed": True}
    with pytest.raises(ValueError, match="different frozen"):
        independent_worker_feedback(
            record, context["materialization_candidate"], context["grader_candidate"]
        )


def test_feedback_rejects_unexpected_private_field(context):
    record = independent_repair_record(context, diagnosis())
    record["private_reasoning"] = "PRIVATE_ANSWER"
    with pytest.raises(ValueError, match="Unexpected"):
        independent_worker_feedback(
            record, context["materialization_candidate"], context["grader_candidate"]
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"target": "none"},
        {"instruction": "Change the public question"},
        {"independent_issues": []},
        {"disposition": "blocked"},
    ],
)
def test_target_is_unambiguous(changes):
    with pytest.raises(ValidationError):
        diagnosis(**changes)


def test_question_and_blocked_targets_do_not_create_independent_feedback(context):
    for response in [
        diagnosis(
            target="public_question",
            instruction="Complete corrected question",
            independent_issues=[],
        ),
        diagnosis(disposition="blocked", target="none", independent_issues=[]),
    ]:
        assert validate_diagnosis(response, context) == response
        with pytest.raises(ValueError, match="corresponding"):
            independent_repair_record(context, response)


def test_diagnostic_worker_rejects_private_quote_then_records_typed_target(
    tmp_path, monkeypatch, context
):
    import asyncio
    import time

    import run_specification as module

    inputs = {"revision_context": context}
    for name, data in [("policy.json", {}), ("revision.json", context), ("input.json", inputs)]:
        (tmp_path / name).write_text(json.dumps(data))
    monkeypatch.setattr(module, "specification_context", lambda *a, **k: inputs)
    requests = []

    async def complete(payload):
        requests.append(payload)
        response = diagnosis().model_dump()
        if len(requests) == 1:
            response["independent_issues"][0]["public_requirement_quote"] = "PRIVATE_ANSWER"
        else:
            assert "must quote" in payload["messages"][-1]["content"]
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": str(len(requests)),
                                "type": "function",
                                "function": {
                                    "name": "submit_artifact",
                                    "arguments": json.dumps(response),
                                },
                            }
                        ],
                    },
                }
            ]
        }

    config = {
        "entrypoint": "run_specification.py",
        "comparison_repair": True,
        "revision_context_file": str(tmp_path / "revision.json"),
        "reference_directory": str(tmp_path / "reference"),
        "policy_file": str(tmp_path / "policy.json"),
        "input_file": str(tmp_path / "input.json"),
        "output_format": "tools",
        "max_requests": None,
        "request_timeout_seconds": 30,
        "reasoning_effort": "high",
    }
    root = tmp_path / "worker"
    asyncio.run(
        module.run(
            config,
            root=root,
            endpoint="unused",
            credential="unused",
            deadline=time.time() + 30,
            complete=complete,
        )
    )
    assert len(requests) == 2
    assert json.loads((root / "comparison-repair.json").read_text()) == diagnosis().model_dump()
    assert not (root / "question-repair.json").exists()
    assert not (root / "specification.json").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"allow_quality_repair": True},
        {"frozen_grader_file": None},
        {"resume_independent_directory": "previous"},
        {"independent_repair_file": "/outside/record.json"},
        {"independent_repair_file": "../record.json"},
    ],
)
def test_independent_repair_configuration_cannot_add_an_allowance_or_escape_checkpoint(changes):
    from run_reference_setup import check_config

    config = json.loads((Path(__file__).parent / "grading-config.json").read_text())
    for key in list(config):
        if key.startswith("resume_"):
            config.pop(key)
    config.update(
        allow_quality_repair=False,
        frozen_grader_file="frozen.json",
        independent_repair_file="repair.json",
    )
    check_config(config)
    config.update(changes)
    with pytest.raises(ValueError):
        check_config(config)
