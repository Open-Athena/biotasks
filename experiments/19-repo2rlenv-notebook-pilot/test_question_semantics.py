"""Numerical agreement cannot approve an unsupported public explanation."""

import shutil

import pytest
from grading_protocol import Review, check_review_source_coverage
from question_repair import read, record, repair_context, write
from test_question_repair import original as original_fixture


@pytest.fixture
def original(tmp_path):
    return original_fixture.__wrapped__(tmp_path)


def assessment():
    return {
        "decision": "revise",
        "rationale": "Correct data did not establish the explanatory claim",
        "issues": [],
        "question_issues": [
            {
                "quote": "stated convention",
                "evidence": "Toy encoded input defines another convention",
            }
        ],
        "source_coverage": {
            "decision": "approve",
            "rationale": "The same endpoint and science remain required",
            "omitted_scientific_endpoints": [],
            "unsupported_evidence_claims": [],
            "scientific_scope_changes": [],
            "remaining_validation": [],
        },
    }


def test_acceptance_cannot_excuse_a_question_defect():
    value = assessment()
    value["decision"] = "accept_for_packaging"
    with pytest.raises(ValueError, match="public-question defects"):
        check_review_source_coverage(Review.model_validate(value))
    value.pop("question_issues")
    # The historical schema remains readable; this does not qualify a new live
    # inspection-enabled review, whose controller requires the explicit field.
    check_review_source_coverage(Review.model_validate(value))


@pytest.mark.parametrize(
    "problem", [None, "quote", "review_hash", "probe_hash", "control", "used", "cleanup", "scope"]
)
def test_question_repair_requires_bound_review_passing_basics_and_unused_allowance(
    original, tmp_path, problem
):
    grading = tmp_path / "grading"
    folder = grading / "grading/candidates/1"
    folder.mkdir(parents=True)
    write(folder / "candidate.json", {"grader_code": "unchanged comparator"})
    shutil.copyfile(folder / "candidate.json", grading / "candidate.json")
    digest = record(grading / "candidate.json")["sha256"]
    controls = [
        {"kind": kind, "passed_control": True, "candidate_sha256": digest}
        for kind in ("reference", "recomputed", "empty", "misplaced", "missing", "alternative")
    ]
    if problem == "control":
        controls[0]["passed_control"] = False
    write(folder / "controls.json", controls)
    # A failed probe annotation does not establish that the frozen scientific
    # comparator is wrong. Fresh validation will generate its own controls.
    write(
        grading / "question-defect-controls.json",
        controls + [{"kind": "probe", "passed_control": False, "candidate_sha256": digest}],
    )
    review = assessment()
    if problem == "quote":
        review["question_issues"][0]["quote"] = "Private answer not in the question"
    if problem == "scope":
        review["source_coverage"]["decision"] = "revise"
        review["source_coverage"]["omitted_scientific_endpoints"] = ["another endpoint"]
    write(grading / "review.json", review)
    write(grading / "probes.json", {"original probe": "immutable script"})
    write(
        grading / "public-question-defect.json",
        {
            "candidate_sha256": digest,
            "review_sha256": record(grading / "review.json")["sha256"],
            "controls_sha256": record(grading / "question-defect-controls.json")["sha256"],
            "probes_sha256": record(grading / "probes.json")["sha256"],
            "quality_repair_used": False,
        },
    )
    write(grading / "independent-solution.json", {"code": "independent matching program"})
    write(grading / "independent-result.json", {"status": "executed_without_answer_access"})
    write(
        grading / "result.json",
        {"status": "public_question_defect", "cleanup_verified": problem != "cleanup"},
    )
    if problem == "review_hash":
        review["rationale"] = "Changed after binding"
        write(grading / "review.json", review)
    if problem == "used":
        write(grading / "repair.json", {})
    if problem == "probe_hash":
        write(grading / "probes.json", {"replacement probe": "unbound"})
    if problem:
        with pytest.raises(ValueError):
            repair_context(original, grading)
    else:
        context = repair_context(original, grading)
        assert context["allowed_targets"] == ["public_question"]
        assert context["semantic_question_review"] == review
        assert context["grader_candidate"] == read(grading / "candidate.json")
        assert context["original_probes"] == read(grading / "probes.json")


def test_review_routes_question_to_existing_allowance_before_grader_repair(tmp_path, monkeypatch):
    from test_grading import test_orchestration_separates_probe_author_and_gates_acceptance

    test_orchestration_separates_probe_author_and_gates_acceptance(
        tmp_path,
        monkeypatch,
        repair=False,
        derived=True,
        resume=False,
        reuse_probes=False,
        contract_only=False,
        comparison_conflict=False,
        inspect_review=True,
        question_defect=True,
    )
