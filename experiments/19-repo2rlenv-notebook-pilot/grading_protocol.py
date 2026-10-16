"""Typed grader candidates and independent controls; no scientific rules here."""

import ast
from typing import Literal

from pydantic import Field, model_validator
from reference_protocol import StrictModel
from repo2rlenv.quality.loop.models import SemanticProbe


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
