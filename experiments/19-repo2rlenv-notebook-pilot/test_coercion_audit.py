"""The controller inventories conversions; GLM owns the scientific finding."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from coercion_audit import Audit, Finding, audit, inventory


def test_grounded_model_finding_becomes_blocking_issue(tmp_path):
    (tmp_path / "tests").mkdir()
    source = "assert int(submitted) == expected\n"
    (tmp_path / "tests/check.py").write_text(source)
    keys = inventory(tmp_path)
    key = next(iter(keys))
    loop = SimpleNamespace(
        model=MagicMock(),
        options=SimpleNamespace(review_model="glm"),
        directory=tmp_path / "records",
    )
    loop.model.ask.return_value = Audit(
        findings=[
            Finding(
                operation=key,
                verdict="false_acceptance",
                explanation="GLM finding",
                repair="GLM proposal",
            )
        ]
    )
    context = SimpleNamespace(
        documents={"tests/check.py": source, "instruction.md": "A count."}, payload=lambda **kw: kw
    )
    issues = audit(loop, tmp_path, context, "test")
    assert len(issues) == 1 and issues[0].severity == "blocking"
    assert issues[0].problem == "GLM finding"
    assert issues[0].evidence[0].quote == source.strip()
    assert (tmp_path / "tests/check.py").read_text() == source
    loop.model.ask.return_value = Audit(findings=[])
    with pytest.raises(ValueError, match="omitted"):
        audit(loop, tmp_path, context, "missing")
