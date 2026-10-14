"""Generated reference plans, preserved diffs, and structural admission checks.

These checks establish identity and completeness of the declared mapping. The
separate GLM review examines scientific fidelity against the original source.
"""

from __future__ import annotations

import ast
import builtins
import difflib
import io
import tokenize
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from reference_environment import validate_environment


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Change(StrictModel):
    purpose: Literal["input_staging", "export", "capture"]
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
    disposition: Literal["prepare", "reject"] = Field(
        description="Required admission decision: prepare a faithful reference, or reject with a reason."
    )
    explanation: str = Field(min_length=1)
    environment_rationale: str
    pyproject_toml: str
    system_packages: list[str]
    stage_inputs_sh: str
    changes: list[Change]
    artifacts: list[Artifact]
    branches: list[Branch] = Field(
        description="JSON array of scientific branch records, not a string."
    )
    excluded_outputs: list[str]
    unresolved_assumptions: list[str]

    @model_validator(mode="after")
    def coverage(self):
        if self.disposition == "reject":
            return self
        validate_environment(self.pyproject_toml, self.system_packages)
        paths = [artifact.path for artifact in self.artifacts]
        names = [branch.name for branch in self.branches]
        covered = {path for branch in self.branches for path in branch.artifacts}
        if (
            not paths
            or not names
            or len(set(paths)) != len(paths)
            or len(set(names)) != len(names)
            or covered != set(paths)
        ):
            raise ValueError("Declare unique branches and artifacts with a complete coverage map")
        return self


class ReferenceReview(StrictModel):
    decision: Literal["approve", "revise", "reject"]
    rationale: str = Field(min_length=1)
    omitted_scientific_results: list[str] = Field(
        description="Defects only: required scientific results missing from the plan. Empty [] if none."
    )
    prohibited_scientific_changes: list[str] = Field(
        description="Defects only: prohibited changes to the scientific analysis. Empty [] if none. "
        "Put evidence that science was preserved in rationale, never in this list."
    )
    setup_or_export_problems: list[str] = Field(
        description="Defects only: known setup or export problems. Empty [] if none."
    )
    checks_for_execution: list[str] = Field(
        description="Uncertainties to check against execution evidence, not known defects or "
        "permission to add profiling or alter the source."
    )

    @model_validator(mode="after")
    def no_known_blockers(self):
        populated = [
            field
            for field in (
                "omitted_scientific_results",
                "prohibited_scientific_changes",
                "setup_or_export_problems",
            )
            if getattr(self, field)
        ]
        if self.decision == "approve" and populated:
            raise ValueError(
                "Approval cannot retain known blockers: "
                + ", ".join(populated)
                + ". These lists contain defects only and must be [] to approve. "
                "Put positive findings and 'none detected' explanations in rationale. "
                "If a defect exists, choose revise or reject; do not clear a real defect."
            )
        return self


def validate_capture(script: str, change: Change) -> None:
    """Permit only a fresh binding of an otherwise identical standalone call."""
    try:
        before = ast.parse(change.before).body
        after = ast.parse(change.after).body
        source = ast.parse(script)
    except SyntaxError as error:
        raise ValueError("Capture must contain valid standalone Python") from error
    if (
        len(before) != 1
        or len(after) != 1
        or not isinstance(before[0], ast.Expr)
        or not isinstance(before[0].value, ast.Call)
        or not isinstance(after[0], ast.Assign)
        or len(after[0].targets) != 1
        or not isinstance(after[0].targets[0], ast.Name)
        or ast.dump(before[0].value) != ast.dump(after[0].value)
    ):
        raise ValueError("Capture may only bind an unchanged standalone call to a fresh name")
    if not any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and ast.get_source_segment(script, node) == change.before.strip()
        for node in ast.walk(source)
    ):
        raise ValueError("Capture anchor must identify a complete standalone call in the source")
    names = {
        token.string
        for token in tokenize.generate_tokens(io.StringIO(script).readline)
        if token.type == tokenize.NAME
    }
    if after[0].targets[0].id in names | set(dir(builtins)):
        raise ValueError("Capture target must be a fresh name, not an existing name or builtin")


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
        if change.purpose == "capture":
            validate_capture(script, change)
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
