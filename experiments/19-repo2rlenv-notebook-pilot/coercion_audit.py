"""Ask GLM to assess potentially lossy validation operations, without editing tasks."""

import ast
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.models import Citation, Issue


class Finding(BaseModel):
    operation: str
    verdict: Literal["safe", "false_acceptance", "unknown"]
    explanation: str
    repair: str


class Audit(BaseModel):
    findings: list[Finding]


def inventory(task):
    result = {}
    for path in sorted((task / "tests").rglob("*.py")):
        source = path.read_text()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", "")
            )
            if name not in {
                "astype",
                "int",
                "bool",
                "round",
                "rint",
                "floor",
                "ceil",
                "clip",
                "fillna",
                "nan_to_num",
            }:
                continue
            relative = path.relative_to(task).as_posix()
            key = f"{relative}:{node.lineno}:{ast.unparse(node)}"
            result[key] = {
                "path": relative,
                "line": node.lineno,
                "source_line": source.splitlines()[node.lineno - 1],
            }
    return result


def audit(loop, task, context, key):
    operations = inventory(task)
    if not operations:
        return []
    documents = {
        name: text
        for name, text in context.documents.items()
        if name == "instruction.md" or name.startswith("tests/")
    }
    if sum(len(x.encode()) for x in documents.values()) > 150000:
        raise ValueError("Coercion audit exceeds bounded source context")
    response = loop.model.ask(
        Audit,
        loop.options.review_model,
        files("biotasks.prompts").joinpath("notebook-coercion-audit.md").read_text(),
        context.payload(coercion_operations=operations, audit_documents=documents),
        key + "-coercion",
    )
    save_record(loop.directory / "coercion-audits" / f"{key}.json", response.model_dump())
    if len(response.findings) != len(operations) or {x.operation for x in response.findings} != set(
        operations
    ):
        raise ValueError("Coercion audit omitted or duplicated an operation")
    issues = []
    for finding in response.findings:
        if finding.verdict != "safe":
            original = operations[finding.operation]
            issues.append(
                Issue(
                    category="verifier",
                    severity="blocking",
                    problem=finding.explanation,
                    repair=finding.repair,
                    evidence=[Citation(path=original["path"], quote=original["source_line"])],
                )
            )
    return issues
