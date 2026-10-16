"""Small structured envelope around a coverage review and task proposal."""

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
        description="Private proposed input derivations, comparison rules, evidence requirements and cross-output dependencies, or focused evidence requests when blocked. Distinguish proposals from validated rules; do not invent numerical tolerances.",
    )

    @model_validator(mode="after")
    def brief_matches_disposition(self):
        if (self.disposition == "draft_ready") != bool(self.task_brief.strip()):
            raise ValueError("Only draft_ready may contain a nonempty public task brief")
        return self
