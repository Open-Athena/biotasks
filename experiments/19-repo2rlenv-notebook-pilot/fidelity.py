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
    quote: str = Field(min_length=1)


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
            if not citation.quote.strip() or citation.quote not in documents.get(
                citation.document, ""
            ):
                raise ValueError("Scientific review contains an unsupported citation")
    return not assessment.blocking_findings and all(
        f.verdict == "pass" for f in assessment.findings
    )


def review(*, task: Path, seed: dict, quality: dict, model, directory: Path) -> dict:
    documents = {
        "source/notebook": seed["question_text"],
        "source/manifest": json.dumps(seed["input_manifest"], sort_keys=True),
        "execution/quality": json.dumps(quality, sort_keys=True),
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
    save_record(directory / "input.json", {"system": prompt, "documents": documents})
    reply = complete(
        model,
        system=prompt,
        user=json.dumps(documents),
        max_tokens=8000,
        temperature=0,
        response_schema=Assessment.model_json_schema(),
    )
    save_record(directory / "response.json", {"content": reply.content, "usage": reply.usage})
    assessment = Assessment.model_validate_json(reply.content)
    supported = validate_assessment(assessment, documents)
    result = {
        "assessment": assessment.model_dump(),
        "supported": supported,
        "limitations": "GLM evidence review, not independent execution or a reward",
    }
    save_record(directory / "result.json", result)
    return result
