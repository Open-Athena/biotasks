"""Small structured envelope around a coverage review and task proposal."""

import json
from typing import Literal

from pydantic import Field, model_validator
from reference_protocol import StrictModel


class TaskSpecification(StrictModel):
    disposition: Literal["draft_ready", "needs_evidence", "reference_work_required", "reject"] = (
        Field(
            description="draft_ready means a supported scientific task and output schemas, pending input materialization and executable grading validation. Choose needs_evidence for missing facts needed to define the reference, not merely uncalibrated tolerances or unproven portability."
        )
    )
    review: str = Field(
        min_length=1,
        description="Actual Markdown coverage/fidelity review with evidence citations and concrete blockers. A generic endorsement or promise of a review is not a review.",
    )
    task_brief: str = Field(
        description="Public scientific question and output schemas when draft_ready; empty string otherwise. Standalone draft with acceptance rules explicitly pending validation. No placeholders or dependence on private evidence.",
    )
    validation_handoff: str = Field(
        min_length=1,
        description="Private input derivations, endpoint lineage, scientific meaning/identity constraints and unresolved evidence questions. Executable comparator design, probe construction and tolerance calibration belong to later validation. No predicted pass/fail outcomes or invented numerical tolerances.",
    )

    @model_validator(mode="after")
    def brief_matches_disposition(self):
        if (self.disposition == "draft_ready") != bool(self.task_brief.strip()):
            raise ValueError("Only draft_ready may contain a nonempty public task brief")
        return self


class SpecificationEvidence(StrictModel):
    path: str = Field(min_length=1, description="Key in the review's evidence_text map.")
    quote: str = Field(min_length=1, description="Exact nonempty substring of that evidence.")


class SpecificationFinding(StrictModel):
    problem: str = Field(min_length=1)
    evidence: list[SpecificationEvidence] = Field(min_length=1)
    required_change: str = Field(
        min_length=1,
        description="Owning-stage action needed, or why no permitted correction is possible.",
    )


class SpecificationReview(StrictModel):
    disposition: Literal["ready", "revise", "reject"]
    assessment: str = Field(min_length=1)
    findings: list[SpecificationFinding]

    @model_validator(mode="after")
    def findings_match_disposition(self):
        if (self.disposition == "ready") != (not self.findings):
            raise ValueError("Ready requires no blocking findings; revise/reject require evidence")
        return self


def specification_review_context(context, proposal, *, parent_sha256):
    """An independent review sees evidence and operative proposals, not self-review."""
    proposal = TaskSpecification.model_validate(proposal)
    if proposal.disposition != "draft_ready":
        raise ValueError("Only a draft-ready specification can enter scientific review")
    result = dict(context)
    result.pop("files")
    result.pop("revision_context", None)
    result["specification_review"] = {
        "parent_sha256": parent_sha256,
        "task_brief_path": "proposal/task_brief",
        "validation_handoff_path": "proposal/validation_handoff",
    }
    evidence = {}
    for path, value in context["files"].items():
        evidence[path] = (
            value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
        )
    evidence["proposal/task_brief"] = proposal.task_brief
    evidence["proposal/validation_handoff"] = proposal.validation_handoff
    result["evidence_text"] = evidence
    return result


def validate_specification_review(value, context):
    """Ground findings in supplied text, without claiming semantic verification."""
    review = SpecificationReview.model_validate(value)
    for finding in review.findings:
        for item in finding.evidence:
            if item.path not in context["evidence_text"] or not item.quote.strip():
                raise ValueError("Review finding lacks a supplied evidence path and quote")
            if item.quote not in context["evidence_text"][item.path]:
                raise ValueError("Review evidence quote is absent from the cited text")
    return review
