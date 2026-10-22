"""Typed grader candidates and independent controls; no scientific rules here."""

import ast
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


class Review(StrictModel):
    decision: Literal["accept_for_packaging", "revise", "blocked"]
    rationale: str = Field(min_length=1)
    issues: list[str]
    # Legacy records remain readable; new live reviews must supply this audit.
    source_coverage: CoverageReview | None = None


def check_review_source_coverage(review):
    if review.source_coverage is None:
        raise ValueError("Review must independently audit original-source endpoint coverage")
    if review.decision == "accept_for_packaging" and review.source_coverage.decision != "approve":
        raise ValueError("Acceptance requires approved original-source endpoint coverage")


class ProbeExpectation(StrictModel):
    name: str = Field(min_length=1)
    check_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class GraderRepair(Grader):
    probe_expectations: list[ProbeExpectation] = Field(default_factory=list)


def apply_probe_expectations(repair, original):
    """Correct model-authored annotations without changing any scientific mutation."""
    candidate = Grader.model_validate(repair.model_dump(exclude={"probe_expectations"}))
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
            if probe.kind == "valid_alternative" and update.check_ids != probe.check_ids:
                raise ValueError("Valid-alternative expectations stay fixed: all checks must pass")
            # The schema has no script/kind/intent fields; all original mutation
            # bytes, names, kinds, focus and source evidence are copied unchanged.
            probe = Probe.model_validate(
                {**probe.model_dump(), "check_ids": update.check_ids, "rationale": update.rationale}
            )
        probes.append(probe)
    revised = Probes.model_validate({**original.model_dump(), "probes": probes})
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
