"""Execution success cannot override incomplete scientific admission."""

import copy

import pytest
from grading_protocol import (
    LiveReview,
    Review,
    ScientificAdmission,
    check_review_scientific_admission,
)
from pydantic import ValidationError


def assessment():
    audit = {
        "output_paths": ["result.csv"],
        "decision": "approve",
        "rationale": "Same quantity with justified representational freedom",
        "evidence": ["Source definition and independent comparison report"],
        "blockers": [],
    }
    return {
        "comparisons": [audit],
        "answer_isolation": {**copy.deepcopy(audit), "evidence": ["Inspected installed assets"]},
    }


def review(admission, *, decision="accept_for_packaging"):
    return Review(
        decision=decision,
        rationale="Recorded numerical controls passed",
        issues=[],
        scientific_admission=admission,
    )


def test_historical_review_remains_readable_but_cannot_clear_new_admission():
    old = Review(decision="accept_for_packaging", rationale="Historical record", issues=[])
    assert old.scientific_admission is None
    with pytest.raises(ValueError, match="Explicitly assess"):
        check_review_scientific_admission(old, ["result.csv"])


def test_live_response_schema_requires_admission_in_the_same_review_stage():
    assert "scientific_admission" in LiveReview.model_json_schema()["required"]
    with pytest.raises(ValidationError, match="scientific_admission"):
        LiveReview(decision="blocked", rationale="Missing explicit audit", issues=[])


@pytest.mark.parametrize("category", ["comparisons", "answer_isolation"])
@pytest.mark.parametrize("decision", ["unresolved", "defect"])
def test_numerical_success_cannot_override_a_scientific_blocker(category, decision):
    value = assessment()
    audit = value[category][0] if category == "comparisons" else value[category]
    audit.update(decision=decision, blockers=["Evidence does not establish this claim"])
    with pytest.raises(ValueError, match="scientific equivalence and answer isolation"):
        check_review_scientific_admission(review(value), ["result.csv"])
    check_review_scientific_admission(review(value, decision="blocked"), ["result.csv"])


def test_earlier_export_review_cannot_clear_a_recovered_endpoint():
    value = assessment()
    with pytest.raises(ValueError, match="each final output"):
        check_review_scientific_admission(review(value), ["result.csv", "recovered.csv"])
    value["comparisons"][0]["output_paths"].append("recovered.csv")
    with pytest.raises(ValueError, match="entire final output"):
        check_review_scientific_admission(review(value), ["result.csv", "recovered.csv"])
    value["answer_isolation"]["output_paths"].append("recovered.csv")
    check_review_scientific_admission(review(value), ["result.csv", "recovered.csv"])


def test_duplicate_or_unknown_comparison_is_not_complete_coverage():
    value = assessment()
    value["comparisons"].append(copy.deepcopy(value["comparisons"][0]))
    with pytest.raises(ValueError, match="exactly once"):
        check_review_scientific_admission(review(value), ["result.csv"])
    value = assessment()
    value["comparisons"][0]["output_paths"] = ["unrelated.csv"]
    with pytest.raises(ValueError, match="exactly once"):
        check_review_scientific_admission(review(value), ["result.csv"])


@pytest.mark.parametrize("field", ["evidence", "blockers", "rationale"])
def test_approval_needs_nonempty_evidence_and_no_blockers(field):
    value = assessment()
    value["answer_isolation"][field] = (
        ["Unresolved concern"] if field == "blockers" else [] if field == "evidence" else " "
    )
    with pytest.raises(ValidationError):
        ScientificAdmission.model_validate(value)


def test_current_review_roundtrip_retains_scientific_admission():
    current = review(assessment())
    archived = Review.model_validate_json(current.model_dump_json())
    check_review_scientific_admission(archived, ["result.csv"])
