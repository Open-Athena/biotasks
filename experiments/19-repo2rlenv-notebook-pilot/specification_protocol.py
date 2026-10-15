"""Small structured envelope around a coverage review and task proposal."""

from typing import Literal

from pydantic import Field, model_validator
from reference_protocol import StrictModel


class TaskSpecification(StrictModel):
    disposition: Literal["draft_ready", "needs_evidence", "reference_work_required", "reject"]
    review: str = Field(min_length=1)
    task_brief: str
    validation_plan: str = Field(min_length=1)

    @model_validator(mode="after")
    def brief_matches_disposition(self):
        if (self.disposition == "draft_ready") != bool(self.task_brief.strip()):
            raise ValueError("Only draft_ready may contain a nonempty public task brief")
        return self
