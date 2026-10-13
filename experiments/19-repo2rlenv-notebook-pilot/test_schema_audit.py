from types import SimpleNamespace

import pytest
from schema_audit import SchemaAudit, audit, keyed_accesses


def test_optional_name_is_blocking_and_inventory_cannot_be_omitted(tmp_path):
    task = tmp_path / "task"
    (task / "tests").mkdir(parents=True)
    source = "value = output['quantity']\n"
    (task / "tests/test_result.py").write_text(source)
    assert set(keyed_accesses(task)) == {"output['quantity']"}
    result = SchemaAudit.model_validate(
        {
            "obligations": [
                {
                    "expression": "output['quantity']",
                    "required_by_grader": True,
                    "public_status": "optional",
                    "explanation": "Worker found schema mismatch",
                    "repair": "Worker proposed schema clarification",
                    "evidence": [{"path": "tests/test_result.py", "quote": source.strip()}],
                }
            ]
        }
    )
    loop = SimpleNamespace(
        directory=tmp_path / "quality",
        options=SimpleNamespace(review_model=None),
        model=SimpleNamespace(ask=lambda *args: result),
    )
    context = SimpleNamespace(documents={"tests/test_result.py": source}, payload=lambda **kw: kw)
    issues = audit(loop, task, context, "review")
    assert issues[0].severity == "blocking"
    assert issues[0].problem == "Worker found schema mismatch"
    result.obligations.clear()
    with pytest.raises(ValueError, match="every keyed access"):
        audit(loop, task, context, "missing")
