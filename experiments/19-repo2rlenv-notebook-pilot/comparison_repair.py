"""Choose a comparison repair without forwarding private answers to a solver."""

from typing import Literal

from grading_protocol import (
    Grader,
    GraderRepairSubmission,
    Probes,
    StrictModel,
    apply_probe_expectations,
    bind_repair_checks,
    check_repair_inventory,
)
from pydantic import Field, model_validator


class PublicCodeIssue(StrictModel):
    public_requirement_quote: str = Field(min_length=1)
    prior_code_quote: str = Field(min_length=1)


class ComparisonRepair(StrictModel):
    disposition: Literal["ready", "blocked"]
    target: Literal["public_question", "independent_solution", "none"]
    instruction: str | None
    independent_issues: list[PublicCodeIssue]
    grader_repair: GraderRepairSubmission | None = None
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_target(self):
        if self.grader_repair is not None and (
            self.disposition != "ready"
            or self.target != "public_question"
            or self.grader_repair.disposition != "ready"
        ):
            raise ValueError("A joint grader revision requires a ready question repair")
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
    if value.disposition == "ready" and value.target not in context.get(
        "allowed_targets", ["public_question", "independent_solution"]
    ):
        raise ValueError("This evidence permits only the recorded repair targets")
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
    if value.grader_repair is not None:
        if "original_probes" not in context:
            raise ValueError("Joint revision requires retained original probe evidence")
        revised_grading(context, value.grader_repair)
    return value


def revised_grading(context, repair):
    """Bind edits to the original checks and mutation scripts, never new science."""
    prior = Grader.model_validate(context["grader_candidate"])
    probes = Probes.model_validate(context["original_probes"])
    if repair is None:
        return prior, probes
    bound = bind_repair_checks(repair, prior.checks, prior_candidate=prior)
    check_repair_inventory(bound.checks, prior.checks)
    return apply_probe_expectations(bound, probes)


def freeze_comparison_revision(materialization, context, response):
    """Seal one coherent generated revision for fresh independent validation.

    Like upstream's multi-edit repair, this creates a separate candidate. Typed
    field binding is used here because these pre-Harbor artifacts are not yet a
    task tree accepted by upstream apply_repair. No prior acceptance is reused.
    """
    diagnosis = validate_diagnosis(response, context)
    frozen = {
        "materialization_candidate": materialization,
        "grader_candidate": context["grader_candidate"],
    }
    if "original_probes" in context:
        grader, _ = revised_grading(context, diagnosis.grader_repair)
        frozen["grader_candidate"] = grader.model_dump()
        frozen["quality_revision"] = {
            "grader_candidate": context["grader_candidate"],
            "original_probes": context["original_probes"],
            "grader_repair": diagnosis.grader_repair.model_dump()
            if diagnosis.grader_repair is not None
            else None,
        }
    return frozen


def load_comparison_revision(frozen):
    """Revalidate the sealed typed edit and retain all original probe scripts."""
    revision = frozen["quality_revision"]
    repair = revision["grader_repair"]
    if repair is not None:
        repair = GraderRepairSubmission.model_validate(repair)
        if repair.disposition != "ready":
            raise ValueError("A frozen quality revision requires a ready grader repair")
    grader, probes = revised_grading(revision, repair)
    if grader.model_dump() != frozen["grader_candidate"]:
        raise ValueError("Frozen quality revision differs from its bound grader edits")
    return grader, probes


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
