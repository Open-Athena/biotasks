"""GLM audit of literal keyed accesses against the public artifact contract."""

import ast
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict
from repo2rlenv.execution.lifecycle import save_record
from repo2rlenv.quality.loop.models import Citation, Issue


class Obligation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str
    required_by_grader: bool
    public_status: Literal["required", "optional", "absent", "not_applicable"]
    explanation: str
    repair: str
    evidence: list[Citation]


class SchemaAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    obligations: list[Obligation]


def keyed_accesses(task):
    accesses = {}
    for path in sorted((task / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    expression = ast.unparse(node)
                    accesses.setdefault(expression, []).append(
                        {"path": path.relative_to(task).as_posix(), "line": node.lineno}
                    )
    return accesses


def audit(loop, task, context, key):
    accesses = keyed_accesses(task)
    documents = {
        name: text
        for name, text in context.documents.items()
        if name == "instruction.md" or (name.startswith("tests/") and name.endswith(".py"))
    }
    if sum(len(text.encode()) for text in documents.values()) > 150_000:
        raise ValueError("Schema audit source exceeds bounded context; no truncation")
    result = loop.model.ask(
        SchemaAudit,
        loop.options.review_model,
        files("biotasks.prompts").joinpath("notebook-schema-audit.md").read_text(),
        context.payload(literal_keyed_accesses=accesses, schema_documents=documents),
        key + "-schema",
    )
    if len(result.obligations) != len(accesses) or {
        item.expression for item in result.obligations
    } != set(accesses):
        raise ValueError("Schema audit did not cover every keyed access exactly once")
    issues = []
    for item in result.obligations:
        if not item.evidence:
            raise ValueError("Schema audit requires source evidence")
        for citation in item.evidence:
            document = context.documents.get(citation.path, "")
            if not document or " ".join(citation.quote.split()) not in " ".join(document.split()):
                raise ValueError("Schema audit citation is unsupported")
        if item.required_by_grader and item.public_status != "required":
            issues.append(
                Issue(
                    category="instruction",
                    severity="blocking",
                    problem=item.explanation,
                    repair=item.repair,
                    evidence=item.evidence,
                )
            )
    save_record(loop.directory / "schema-audits" / f"{key}.json", result.model_dump())
    return issues
