"""Evidence-bound scientific review; does not author or repair candidate files."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.llm import complete

DIMENSIONS = {
    "observed_data",
    "methodology",
    "public_contract",
    "scientific_grading",
    "software_alternatives",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(StrictModel):
    document: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class Finding(StrictModel):
    dimension: Literal[
        "observed_data",
        "methodology",
        "public_contract",
        "scientific_grading",
        "software_alternatives",
    ]
    verdict: Literal["pass", "fail", "unknown"]
    explanation: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class Assessment(StrictModel):
    findings: list[Finding] = Field(min_length=5, max_length=5)
    blocking_findings: list[str]


def validate_assessment(assessment: Assessment, documents: dict[str, str]) -> bool:
    if {f.dimension for f in assessment.findings} != DIMENSIONS:
        raise ValueError("Assessment must cover each scientific dimension exactly once")
    for finding in assessment.findings:
        for citation in finding.citations:
            lines = documents.get(citation.document, "").splitlines()
            if not 1 <= citation.start_line <= citation.end_line <= len(lines):
                raise ValueError("Scientific review contains an unsupported citation")
            if citation.end_line - citation.start_line > 8 or not any(
                line.strip() for line in lines[citation.start_line - 1 : citation.end_line]
            ):
                raise ValueError("Scientific review citation must be short and nonempty")
    return not assessment.blocking_findings and all(
        f.verdict == "pass" for f in assessment.findings
    )


def review(*, task: Path, seed: dict, quality: dict, model, directory: Path) -> dict:
    documents = {
        "source/notebook": seed["question_text"],
        "source/manifest": json.dumps(seed["input_manifest"], sort_keys=True, indent=2),
        "execution/quality": json.dumps(quality, sort_keys=True, indent=2),
    }
    # The audit must inspect all candidate text, not silently omit a long grader.
    # Biological binaries are represented by the manifest, not decoded as text.
    limit = 250_000
    total = sum(len(v.encode()) for v in documents.values())
    for path in sorted(task.rglob("*")):
        if path.is_symlink():
            raise ValueError("Scientific audit does not follow task symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(task)
        if relative.parts[0] not in {"tests", "solution", "environment"} and relative.name not in {
            "instruction.md",
            "task.toml",
        }:
            continue
        if path.stat().st_size > limit:
            raise ValueError(
                f"Scientific audit requires explicit handling of large file: {relative}"
            )
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = json.dumps({"binary_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        total += len(text.encode())
        if total > limit:
            raise ValueError(
                "Scientific audit evidence exceeds bounded context; no truncation allowed"
            )
        documents[f"task/{relative.as_posix()}"] = text
    prompt = files("biotasks.prompts").joinpath("notebook-fidelity.md").read_text()
    directory.mkdir(parents=True, exist_ok=False)
    numbered = {
        name: "\n".join(f"{index}: {line}" for index, line in enumerate(text.splitlines(), 1))
        for name, text in documents.items()
    }
    save_record(directory / "documents.json", documents)
    save_record(directory / "input.json", {"system": prompt, "documents": numbered})
    reply = complete(
        model,
        system=prompt,
        user=json.dumps(numbered),
        max_tokens=8000,
        temperature=0,
        response_schema=Assessment.model_json_schema(),
    )
    save_record(directory / "response.json", {"content": reply.content, "usage": reply.usage})
    assessment = None
    validation_error = None
    try:
        assessment = Assessment.model_validate_json(reply.content)
        supported = validate_assessment(assessment, documents)
    except ValueError as error:
        supported = False
        validation_error = str(error)
    resolved = []
    if validation_error is None and assessment is not None:
        for finding in assessment.findings:
            for citation in finding.citations:
                resolved.append(
                    {
                        "dimension": finding.dimension,
                        **citation.model_dump(),
                        "quote": "\n".join(
                            documents[citation.document].splitlines()[
                                citation.start_line - 1 : citation.end_line
                            ]
                        ),
                    }
                )
    result = {
        "citation_format": "document-lines-v1",
        "resolved_citations": resolved,
        "assessment": assessment.model_dump() if assessment is not None else None,
        "supported": supported,
        "validation_error": validation_error,
        "limitations": "GLM evidence review, not independent execution or a reward",
    }
    save_record(directory / "result.json", result)
    return result
