"""Generated reference plans, preserved diffs, and structural admission checks.

These checks establish identity and completeness of the declared mapping. The
separate GLM review examines scientific fidelity against the original source.
"""

from __future__ import annotations

import ast
import difflib
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Change(StrictModel):
    purpose: Literal["input_staging", "export"]
    before: str = Field(min_length=1)
    after: str = Field(min_length=1)
    justification: str = Field(min_length=1)


class Artifact(StrictModel):
    path: str
    description: str = Field(min_length=1)
    source_evidence: str = Field(min_length=1)

    @model_validator(mode="after")
    def relative_path(self):
        path = PurePosixPath(self.path)
        if (
            not self.path
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != self.path
            or self.path == "."
        ):
            raise ValueError("Artifact paths must be normalized relative paths")
        return self


class Branch(StrictModel):
    name: str = Field(min_length=1)
    scientific_result: str = Field(min_length=1)
    source_evidence: str = Field(min_length=1)
    artifacts: list[str] = Field(min_length=1)


class ReferencePlan(StrictModel):
    disposition: Literal["prepare", "reject"]
    explanation: str = Field(min_length=1)
    environment_rationale: str
    setup_sh: str
    changes: list[Change]
    artifacts: list[Artifact]
    branches: list[Branch]
    excluded_outputs: list[str]
    unresolved_assumptions: list[str]

    @model_validator(mode="after")
    def coverage(self):
        if self.disposition == "reject":
            return self
        paths = [artifact.path for artifact in self.artifacts]
        names = [branch.name for branch in self.branches]
        covered = {path for branch in self.branches for path in branch.artifacts}
        if (
            not paths
            or not names
            or not self.setup_sh.strip()
            or len(set(paths)) != len(paths)
            or len(set(names)) != len(names)
            or covered != set(paths)
        ):
            raise ValueError("Declare unique branches and artifacts with a complete coverage map")
        return self


class ReferenceReview(StrictModel):
    decision: Literal["approve", "revise", "reject"]
    rationale: str = Field(min_length=1)
    omitted_scientific_results: list[str]
    scientific_changes: list[str]
    setup_or_export_problems: list[str]
    checks_for_execution: list[str]

    @model_validator(mode="after")
    def no_known_blockers(self):
        if self.decision == "approve" and (
            self.omitted_scientific_results
            or self.scientific_changes
            or self.setup_or_export_problems
        ):
            raise ValueError("Approval cannot retain known blockers")
        return self


def materialize(baseline: str, plan: ReferencePlan) -> tuple[str, str]:
    """Apply explicit, uniquely anchored edits; never overwrite the baseline."""
    if plan.disposition != "prepare":
        raise ValueError("Rejected plans cannot execute")
    script = baseline
    for change in plan.changes:
        if script.count(change.before) != 1:
            raise ValueError("Each change needs one exact, unambiguous source anchor")
        if change.purpose == "export" and not change.after.startswith(change.before):
            raise ValueError(
                "Exports may append code after an anchor, not replace source statements"
            )
        script = script.replace(change.before, change.after, 1)
    try:
        compile(ast.parse(script), "reference.py", "exec")
    except SyntaxError as error:
        raise ValueError(f"Generated reference is not valid Python: {error.msg}") from error
    diff = "".join(
        difflib.unified_diff(
            baseline.splitlines(keepends=True),
            script.splitlines(keepends=True),
            fromfile="baseline.py",
            tofile="reference.py",
        )
    )
    return script, diff
