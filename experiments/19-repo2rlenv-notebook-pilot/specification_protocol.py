"""Small structured envelope around a coverage review and task proposal."""

from typing import Literal

from pydantic import Field, model_validator
from reference_protocol import StrictModel


class TaskSpecification(StrictModel):
    disposition: Literal["draft_ready", "needs_evidence", "reference_work_required", "reject"] = Field(
        description="Choose needs_evidence when a consequential method/default/identity is unresolved. draft_ready requires a complete self-contained public brief with no guessed science."
    )
    review: str = Field(
        min_length=1,
        description="Actual Markdown coverage/fidelity review with evidence citations and concrete blockers. A generic endorsement or promise of a review is not a review.",
    )
    task_brief: str = Field(
        description="Complete standalone solver instructions when draft_ready; empty string otherwise. Never a placeholder, summary or cross-reference to the private plan. The solver will receive only this field and the public input files.",
    )
    validation_plan: str = Field(
        min_length=1,
        description="Return the actual factory-facing validation plan or precise evidence requests in full. Private means excluded from solver-visible files, not withheld from this response. Include checks/controls still needed; do not invent numeric tolerances.",
    )

    @model_validator(mode="after")
    def brief_matches_disposition(self):
        if (self.disposition == "draft_ready") != bool(self.task_brief.strip()):
            raise ValueError("Only draft_ready may contain a nonempty public task brief")
        return self
