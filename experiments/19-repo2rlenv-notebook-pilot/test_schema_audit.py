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
    result.obligations[0].public_status = "not_applicable"
    assert audit(loop, task, context, "private-setting") == []
    result.obligations.clear()
    with pytest.raises(ValueError, match="every keyed access"):
        audit(loop, task, context, "missing")


def test_bad_citation_gets_one_bounded_retry(tmp_path):
    from unittest.mock import MagicMock

    task = tmp_path / "task"
    (task / "tests").mkdir(parents=True)
    source = "x = output['value']\n"
    (task / "tests/test_x.py").write_text(source)

    def response(quote):
        return SchemaAudit.model_validate(
            {
                "obligations": [
                    {
                        "expression": "output['value']",
                        "required_by_grader": True,
                        "public_status": "required",
                        "explanation": "Worker assessment",
                        "repair": "None",
                        "evidence": [{"path": "tests/test_x.py", "quote": quote}],
                    }
                ]
            }
        )

    loop = SimpleNamespace(
        directory=tmp_path / "quality",
        options=SimpleNamespace(review_model=None),
        model=MagicMock(),
    )
    context = SimpleNamespace(documents={"tests/test_x.py": source}, payload=lambda **kw: kw)
    loop.model.ask.side_effect = [response("fabricated"), response(source.strip())]
    assert audit(loop, task, context, "repair") == []
    assert loop.model.ask.call_count == 2
    loop.model.ask.side_effect = [response("fabricated"), response("still fabricated")]
    with pytest.raises(ValueError, match="supported evidence"):
        audit(loop, task, context, "fail")
    assert loop.model.ask.call_count == 4
