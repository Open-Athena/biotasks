"""Generated reference plans, preserved diffs, and structural admission checks.

These checks establish syntax and a nonempty, unique artifact inventory. The
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


class Artifact(StrictModel):
    path: str = Field(description="Path relative to /work/outputs.")
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


class ReferencePlan(StrictModel):
    disposition: Literal["prepare", "reject"] = Field(
        description="Required admission decision: prepare a faithful reference, or reject with a reason."
    )
    explanation: str = Field(min_length=1)
    export_code: str = Field(
        description="Only Python code to append after the unchanged baseline, saving existing terminal results. Empty only when rejecting."
    )
    artifacts: list[Artifact]
    excluded_outputs: list[str]
    unresolved_assumptions: list[str]

    @model_validator(mode="after")
    def inventory(self):
        if self.disposition == "reject":
            return self
        paths = [artifact.path for artifact in self.artifacts]
        if not paths or len(set(paths)) != len(paths):
            raise ValueError("Declare nonempty, unique endpoint artifacts")
        return self


class ReferenceReview(StrictModel):
    decision: Literal["approve", "revise", "reject"]
    rationale: str = Field(min_length=1)
    omitted_scientific_results: list[str] = Field(
        description="Defects only: eligible existing terminal scientific results missing from the plan. Empty [] if none."
    )
    prohibited_scientific_changes: list[str] = Field(
        description="Defects only: prohibited changes to the scientific analysis. Empty [] if none. "
        "Put evidence that science was preserved in rationale, never in this list."
    )
    setup_or_export_problems: list[str] = Field(
        description="Defects only: export problems or preparation crossing into environment/input setup. Empty [] if none."
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


def materialize(baseline: str, plan: ReferencePlan) -> tuple[str, str]:
    """Append returned export code to the untouched baseline and check syntax.

    These checks do not establish scientific fidelity. That requires the later
    review of the complete script and diff against the preserved baseline.
    """
    if plan.disposition != "prepare":
        raise ValueError("Rejected plans cannot execute")
    if not plan.export_code.strip():
        raise ValueError("A prepare plan must include nonempty export code")
    # Separate from a final comment or statement even when the baseline has no
    # trailing newline. The original text remains an exact prefix.
    script = baseline + "\n\n" + plan.export_code
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
