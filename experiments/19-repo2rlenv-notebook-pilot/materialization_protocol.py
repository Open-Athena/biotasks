"""Worker-authored scientific task inputs and executable solution, no seed rules."""

import ast
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, model_validator
from reference_protocol import StrictModel


def relative_paths(paths):
    if len(paths) != len(set(paths)):
        raise ValueError("Artifact paths must be unique")
    for name in paths:
        path = PurePosixPath(name)
        if name in {"", "."} or path.is_absolute() or ".." in path.parts or str(path) != name:
            raise ValueError("Expected normalized relative artifact path")


class OperationUse(StrictModel):
    operation_ids: list[str]
    role: Literal[
        "result",
        "supplied_input",
        "support",
        "redundant",
        "presentation",
        "diagnostic",
        "not_executed",
    ]
    artifact_paths: list[str]
    counterpart_id: str | None
    rationale: str = Field(min_length=1)


class Materialization(StrictModel):
    disposition: Literal["ready", "blocked"]
    instruction: str
    input_paths: list[str] = Field(
        description="Paths relative to the input root, e.g. data.csv, not inputs/data.csv."
    )
    output_paths: list[str] = Field(
        description="Paths relative to each output root, e.g. result.csv, not outputs/result.csv."
    )
    derive_code: str
    oracle_code: str
    rationale: str = Field(min_length=1)
    # Historical artifacts remain readable. Current construction validates this
    # against a controller-generated inventory of every original source call.
    operation_coverage: list[OperationUse] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_bundle(self):
        if self.disposition == "blocked":
            return self
        if not self.instruction.strip() or not self.input_paths or not self.output_paths:
            raise ValueError("Ready bundle requires instructions, inputs and outputs")
        relative_paths(self.input_paths)
        relative_paths(self.output_paths)
        for source in (self.derive_code, self.oracle_code):
            if not source.strip():
                raise ValueError("Ready bundle requires derivation and oracle programs")
            try:
                ast.parse(source)
            except SyntaxError as error:
                raise ValueError(str(error)) from error
        return self
