"""Choose a comparison repair without forwarding private answers to a solver."""

from typing import Literal

from grading_protocol import StrictModel
from pydantic import Field, model_validator


class PublicCodeIssue(StrictModel):
    public_requirement_quote: str = Field(min_length=1)
    prior_code_quote: str = Field(min_length=1)


class ComparisonRepair(StrictModel):
    disposition: Literal["ready", "blocked"]
    target: Literal["public_question", "independent_solution", "none"]
    instruction: str | None
    independent_issues: list[PublicCodeIssue]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_target(self):
        if self.disposition == "blocked":
            if self.target != "none" or self.instruction is not None or self.independent_issues:
                raise ValueError("A blocked diagnosis proposes no artifact changes")
        elif self.target == "public_question":
            if not self.instruction or not self.instruction.strip() or self.independent_issues:
                raise ValueError("Question repair needs complete text and no code-repair issues")
        elif self.target == "independent_solution":
            if self.instruction is not None or not self.independent_issues:
                raise ValueError(
                    "Independent repair retains the question and identifies code issues"
                )
        else:
            raise ValueError("A ready diagnosis must select a repair target")
        return self


def validate_diagnosis(value, context):
    """Code feedback may quote only information already visible to its author."""
    value = ComparisonRepair.model_validate(value)
    if value.target == "independent_solution":
        instruction = context["materialization_candidate"]["instruction"]
        code = context["independent_solution"]["code"]
        for issue in value.independent_issues:
            if (
                not issue.public_requirement_quote.strip()
                or issue.public_requirement_quote not in instruction
                or not issue.prior_code_quote.strip()
                or issue.prior_code_quote not in code
            ):
                raise ValueError(
                    "Repair feedback must quote the public question and prior code exactly"
                )
    return value


def independent_repair_record(context, response):
    value = validate_diagnosis(response, context)
    if value.target != "independent_solution":
        raise ValueError("Independent repair requires the corresponding worker diagnosis")
    return {
        "materialization_candidate": context["materialization_candidate"],
        "grader_candidate": context["grader_candidate"],
        "prior_code": context["independent_solution"]["code"],
        "issues": [item.model_dump() for item in value.independent_issues],
    }


def independent_worker_feedback(record, materialization, grader):
    """Project a host-only record onto public question / prior-code evidence only."""
    if set(record) != {"materialization_candidate", "grader_candidate", "prior_code", "issues"}:
        raise ValueError("Unexpected independent-repair record fields")
    if not isinstance(record["prior_code"], str) or not record["prior_code"].strip():
        raise ValueError("Independent repair needs its prior worker code")
    if (
        record["materialization_candidate"] != materialization
        or record["grader_candidate"] != grader
    ):
        raise ValueError("Independent repair belongs to different frozen scientific artifacts")
    response = ComparisonRepair(
        disposition="ready",
        target="independent_solution",
        instruction=None,
        independent_issues=record["issues"],
        rationale="Host validation of public-only feedback",
    )
    validate_diagnosis(
        response,
        {
            "materialization_candidate": materialization,
            "independent_solution": {"code": record["prior_code"]},
        },
    )
    # Do not forward the private diagnosis, grader, source, reference values or
    # failed-control messages. All transmitted strings were public to this worker
    # or written by its own earlier implementation.
    return {"prior_code": record["prior_code"], "issues": record["issues"]}
