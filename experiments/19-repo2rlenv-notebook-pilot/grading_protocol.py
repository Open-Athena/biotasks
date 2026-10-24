"""Typed grader candidates and independent controls; no scientific rules here."""

import ast
from collections import Counter
from typing import Literal

from coverage_protocol import CoverageReview
from pydantic import Field, model_validator
from reference_protocol import StrictModel
from repo2rlenv.quality.loop.models import SemanticProbe


def artifact_interface(output_paths):
    """Describe the controller's directory arguments, independently of a task's prose."""
    return {
        "output_paths": list(output_paths),
        "path_rule": (
            "Each declared output path is relative to the supplied output root. "
            "The grader reads reference_dir / path and submission_dir / path. "
            "Directory argument names are opaque: do not append their basename "
            "or another outputs/ component unless it is part of the declared path."
        ),
        "grader_root_arguments": ["--reference-dir", "--submission-dir"],
        "solution_output_root_argument": "--output-dir",
        "native_output_root": "/workspace/outputs",
        "native_grader_submission_dir": "/workspace/outputs",
        "control_evidence": (
            "submission_before and submission_sha256 keys are relative to the "
            "actual supplied submission root; use those records to establish placement."
        ),
    }


def control_summary(controls):
    """Count recorded controls, not the grader's positive/negative rewards."""
    return {
        "controls": len(controls),
        "expected_outcomes_met": sum(c.get("passed_control") is True for c in controls),
        "by_kind": dict(sorted(Counter(c["kind"] for c in controls).items())),
        "probes_by_kind": dict(
            sorted(
                Counter(
                    (c.get("probe") or {}).get("kind", "unrecorded")
                    for c in controls
                    if c["kind"] == "probe"
                ).items()
            )
        ),
    }


class Check(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    kind: Literal["structural", "scientific"]
    artifacts: list[str] = Field(min_length=1)
    public_requirement: str = Field(min_length=1)


class Grader(StrictModel):
    disposition: Literal["ready", "blocked"]
    instruction: str
    grader_code: str
    checks: list[Check]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def unique_checks(self):
        if self.disposition == "blocked":
            return self
        if not self.instruction.strip() or not self.grader_code.strip() or not self.checks:
            raise ValueError("A ready candidate requires instructions, code and checks")
        try:
            ast.parse(self.grader_code)
        except SyntaxError as error:
            raise ValueError(str(error)) from error
        ids = [c.id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("Check IDs must be unique")
        return self


class Probe(SemanticProbe):
    check_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def python_script(self):
        try:
            ast.parse(self.script)
        except SyntaxError as error:
            raise ValueError(str(error)) from error
        return self


class Probes(StrictModel):
    disposition: Literal["ready", "blocked"]
    probes: list[Probe]
    concerns: list[str]

    @model_validator(mode="after")
    def unique_names(self):
        if self.disposition == "blocked":
            if not self.concerns:
                raise ValueError("Explain a blocked probe suite")
            return self
        names = [p.name for p in self.probes]
        if len(names) != len(set(names)):
            raise ValueError("Probe names must be unique")
        if not any(p.kind == "valid_alternative" for p in self.probes):
            raise ValueError("Include a justified valid representation control")
        return self


class PublicQuestionIssue(StrictModel):
    quote: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class ScientificAudit(StrictModel):
    output_paths: list[str] = Field(min_length=1)
    decision: Literal["approve", "unresolved", "defect"]
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    blockers: list[str]

    @model_validator(mode="after")
    def consistent(self):
        if len(set(self.output_paths)) != len(self.output_paths):
            raise ValueError("An audit must not repeat output paths")
        if any(not value.strip() for value in [self.rationale, *self.evidence]):
            raise ValueError("Scientific audits require explicit reasoning and evidence")
        if self.decision == "approve" and self.blockers:
            raise ValueError("Scientific approval cannot retain blockers")
        if self.decision != "approve" and not any(value.strip() for value in self.blockers):
            raise ValueError("Explain unresolved scientific admission or a defect")
        return self


class ScientificAdmission(StrictModel):
    comparisons: list[ScientificAudit] = Field(min_length=1)
    answer_isolation: ScientificAudit


class Review(StrictModel):
    decision: Literal["accept_for_packaging", "revise", "blocked"]
    rationale: str = Field(min_length=1)
    issues: list[str]
    # Legacy records remain readable; new live reviews must supply this audit.
    source_coverage: CoverageReview | None = None
    # Historical records omit this field; new inspection-enabled reviews must
    # explicitly assess the base question separately from the grader addendum.
    question_issues: list[PublicQuestionIssue] = Field(default_factory=list)
    # Historical reviews remain readable; the live controller requires this.
    scientific_admission: ScientificAdmission | None = None


class LiveReview(Review):
    scientific_admission: ScientificAdmission


def check_review_scientific_admission(review, output_paths):
    """Require explicit final-output coverage, not infer scientific truth."""
    admission = review.scientific_admission
    if admission is None:
        raise ValueError("Explicitly assess scientific_admission for the final outputs")
    expected = set(output_paths)
    if not expected or len(expected) != len(output_paths):
        raise ValueError("Controller output inventory must be nonempty and unique")
    covered = [path for audit in admission.comparisons for path in audit.output_paths]
    if len(set(covered)) != len(covered) or set(covered) != expected:
        raise ValueError("Comparison audits must cover each final output exactly once")
    if set(admission.answer_isolation.output_paths) != expected:
        raise ValueError("Answer-isolation review must assess the entire final output set")
    audits = [*admission.comparisons, admission.answer_isolation]
    if review.decision == "accept_for_packaging" and any(
        audit.decision != "approve" for audit in audits
    ):
        raise ValueError("Acceptance requires scientific equivalence and answer isolation")


def check_review_source_coverage(review):
    if review.decision == "accept_for_packaging" and review.question_issues:
        raise ValueError("Acceptance requires no unresolved public-question defects")
    if review.source_coverage is None:
        raise ValueError("Review must independently audit original-source endpoint coverage")
    if review.decision == "accept_for_packaging" and review.source_coverage.decision != "approve":
        raise ValueError("Acceptance requires approved original-source endpoint coverage")


class ProbeExpectation(StrictModel):
    name: str = Field(min_length=1)
    check_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    kind: Literal["wrong_solution", "valid_alternative"] | None = Field(
        default=None,
        description=(
            "Null retains the original classification. Correct an originally mislabeled "
            "mutation only when its unchanged script and public scientific rules justify "
            "the classification; observed grader agreement alone is insufficient. "
            "All scientific checks must retain wrong-result coverage."
        ),
    )


class CheckDescription(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    public_requirement: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class GraderRepair(Grader):
    check_descriptions: list[CheckDescription] = Field(default_factory=list)
    probe_expectations: list[ProbeExpectation] = Field(default_factory=list)
    probe_concerns: list[str] | None = Field(
        default=None,
        description=(
            "Optional complete replacement of suite-level concern annotations, justified "
            "by the recorded mutation and evidence. Null preserves the original concerns. "
            "Cannot change scripts, scientific challenges or intended outcomes."
        ),
    )


class GraderRepairSubmission(StrictModel):
    """Editable repair fields; check identities and coverage stay controller-owned."""

    disposition: Literal["ready", "blocked"]
    instruction: str | None = Field(
        default=None,
        description="Null preserves the exact prior acceptance addendum; otherwise return its complete replacement.",
    )
    grader_code: str | None = Field(
        default=None,
        description="Null preserves the exact prior grader program; otherwise return its complete replacement.",
    )
    rationale: str = Field(min_length=1)
    check_descriptions: list[CheckDescription] = Field(default_factory=list)
    probe_expectations: list[ProbeExpectation] = Field(default_factory=list)
    probe_concerns: list[str] | None = None


def bind_repair_checks(submission, frozen_checks, *, prior_candidate=None):
    """Resolve explicitly retained fields and preserve the original check inventory."""
    fields = submission.model_dump()
    for name in ("instruction", "grader_code"):
        if fields[name] is None:
            if prior_candidate is None:
                raise ValueError("Retained repair fields require the exact prior candidate")
            fields[name] = getattr(prior_candidate, name)
    descriptions = {item.id: item for item in submission.check_descriptions}
    if len(descriptions) != len(submission.check_descriptions):
        raise ValueError("Duplicate check description updates")
    if set(descriptions) - {check.id for check in frozen_checks}:
        raise ValueError("Description update refers to an unknown check")
    checks = []
    for check in frozen_checks:
        value = check.model_dump()
        if update := descriptions.get(check.id):
            value["public_requirement"] = update.public_requirement
        checks.append(value)
    return GraderRepair.model_validate({**fields, "checks": checks})


def check_repair_inventory(candidate_checks, frozen_checks):
    """Permit explanatory corrections, retaining every check's identity and coverage."""

    def inventory(checks):
        return [check.model_dump(exclude={"public_requirement"}) for check in checks]

    if inventory(candidate_checks) != inventory(frozen_checks):
        raise ValueError(
            "Repair cannot change the frozen check inventory; report a blocker if coverage must change"
        )


def apply_probe_expectations(repair, original):
    """Correct model-authored annotations without changing any scientific mutation."""
    candidate = Grader.model_validate(
        repair.model_dump(exclude={"check_descriptions", "probe_expectations", "probe_concerns"})
    )
    if candidate.disposition == "blocked":
        return candidate, original
    updates = {item.name: item for item in repair.probe_expectations}
    if len(updates) != len(repair.probe_expectations):
        raise ValueError("Duplicate probe expectation updates")
    if set(updates) - {probe.name for probe in original.probes}:
        raise ValueError("Expectation update refers to an unknown probe")
    probes = []
    for probe in original.probes:
        update = updates.get(probe.name)
        if update:
            if len(update.check_ids) != len(set(update.check_ids)):
                raise ValueError("Duplicate probe check IDs")
            kind = probe.kind if update.kind is None else update.kind
            if probe.kind == kind == "valid_alternative" and update.check_ids != probe.check_ids:
                raise ValueError("Valid-alternative expectations stay fixed: all checks must pass")
            # Scripts, names, focus and source evidence remain immutable. Kind
            # corrections are explicit annotations, checked by fresh execution
            # and independent review; coverage is enforced below.
            probe = Probe.model_validate(
                {
                    **probe.model_dump(),
                    "kind": kind,
                    "check_ids": update.check_ids,
                    "rationale": update.rationale,
                }
            )
        probes.append(probe)
    revised = Probes.model_validate(
        {
            **original.model_dump(),
            "probes": probes,
            "concerns": original.concerns
            if repair.probe_concerns is None
            else repair.probe_concerns,
        }
    )
    check_probes(revised, candidate)
    return candidate, revised


def check_coverage(candidate, paths):
    known = set(paths)
    if any(set(c.artifacts) - known for c in candidate.checks):
        raise ValueError("Checks refer to unknown output artifacts")
    science = {p for c in candidate.checks if c.kind == "scientific" for p in c.artifacts}
    if science != known:
        raise ValueError("Every required artifact needs a scientific check")


def check_probes(suite, candidate):
    ids = {c.id for c in candidate.checks}
    scientific = {c.id for c in candidate.checks if c.kind == "scientific"}
    covered = set()
    for p in suite.probes:
        if set(p.check_ids) - ids:
            raise ValueError("Probe refers to unknown checks")
        if p.kind == "wrong_solution":
            covered.update(p.check_ids)
    if scientific - covered:
        raise ValueError(
            "Missing wrong-result controls for scientific checks: "
            + str(sorted(scientific - covered))
        )


def parse_report(report, candidate):
    if (
        not isinstance(report, dict)
        or set(report) != {"passed", "checks"}
        or type(report["passed"]) is not bool
    ):
        raise ValueError("Invalid verifier report object")
    rows = report["checks"]
    if not isinstance(rows, list) or any(
        not isinstance(r, dict)
        or set(r) != {"id", "passed", "message"}
        or not isinstance(r["id"], str)
        or type(r["passed"]) is not bool
        or not isinstance(r["message"], str)
        for r in rows
    ):
        raise ValueError("Invalid per-check results")
    actual = [r["id"] for r in rows]
    if len(actual) != len(set(actual)) or set(actual) != {c.id for c in candidate.checks}:
        raise ValueError("Verifier skipped, duplicated or invented a check")
    if report["passed"] != all(r["passed"] for r in rows):
        raise ValueError("Overall reward disagrees with named checks")
    return report


class AlternativeSolution(StrictModel):
    disposition: Literal["ready", "blocked"]
    code: str
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def executable(self):
        if self.disposition == "ready":
            if not self.code.strip():
                raise ValueError("A ready independent solution requires code")
            try:
                ast.parse(self.code)
            except SyntaxError as error:
                raise ValueError(str(error)) from error
        return self


class ContractText(StrictModel):
    disposition: Literal["ready", "blocked"]
    instruction: str
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def ready_text(self):
        if self.disposition == "ready" and not self.instruction.strip():
            raise ValueError("Ready contract text cannot be empty")
        return self


def apply_contract_text(candidate, text):
    """The worker can change prose only; executable code/checks stay identical."""
    if text.disposition != "ready":
        raise ValueError("Cannot apply blocked contract text")
    return candidate.model_copy(
        update={"instruction": text.instruction, "rationale": text.rationale}
    )
