"""Passing selected-output controls does not establish original-source coverage."""

import pytest
from coverage_protocol import CoverageReview
from grading_protocol import Review, check_review_source_coverage
from pydantic import ValidationError


def audit(**updates):
    return CoverageReview(
        **{
            "decision": "approve",
            "rationale": "Synthetic source audit",
            "omitted_scientific_endpoints": [],
            "unsupported_evidence_claims": [],
            "scientific_scope_changes": [],
            "remaining_validation": [],
            **updates,
        }
    )


def test_legacy_review_is_readable_but_cannot_supply_new_coverage_acceptance():
    legacy = Review(
        decision="accept_for_packaging", rationale="Legacy selected-output check", issues=[]
    )
    assert legacy.source_coverage is None
    assert legacy.observations == []
    with pytest.raises(ValueError, match="independently audit"):
        check_review_source_coverage(legacy)


def test_separate_source_approval_can_support_final_review():
    review = Review(
        decision="accept_for_packaging", rationale="fixture", issues=[], source_coverage=audit()
    )
    check_review_source_coverage(review)


@pytest.mark.parametrize("decision", ["revise", "reject"])
def test_selected_output_success_cannot_override_a_missing_source_branch(decision):
    review = Review(
        decision="accept_for_packaging",
        rationale="All selected-output controls passed",
        issues=[],
        source_coverage=audit(
            decision=decision,
            omitted_scientific_endpoints=["Another independent scientific endpoint"],
        ),
    )
    with pytest.raises(ValueError, match="approved original-source"):
        check_review_source_coverage(review)


@pytest.mark.parametrize(
    "field",
    ["omitted_scientific_endpoints", "unsupported_evidence_claims", "scientific_scope_changes"],
)
def test_original_coverage_protocol_rejects_approval_with_source_defects(field):
    with pytest.raises(ValidationError, match="empty defect lists"):
        audit(**{field: ["Unresolved source defect"]})


def test_blocked_candidate_preserves_a_source_coverage_failure():
    review = Review(
        decision="blocked",
        rationale="Requires different task construction",
        issues=["The independent terminal branch was omitted"],
        source_coverage=audit(
            decision="reject", omitted_scientific_endpoints=["Omitted terminal branch"]
        ),
    )
    check_review_source_coverage(review)
    assert review.source_coverage.omitted_scientific_endpoints == ["Omitted terminal branch"]
