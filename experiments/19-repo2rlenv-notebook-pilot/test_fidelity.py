"""Scientific review cannot pass through unsupported quotes or omitted criteria."""

import json
from types import SimpleNamespace

import fidelity
import pytest
from fidelity import DIMENSIONS, Assessment, validate_assessment


def assessment():
    return Assessment.model_validate(
        {
            "findings": [
                {
                    "dimension": dimension,
                    "verdict": "pass",
                    "explanation": "Supported",
                    "citations": [{"document": "source", "quote": "observed counts"}],
                }
                for dimension in sorted(DIMENSIONS)
            ],
            "blocking_findings": [],
        }
    )


def test_requires_complete_supported_findings():
    review = assessment()
    assert validate_assessment(review, {"source": "Use observed counts here."})
    review.findings[0].citations[0].quote = "invented evidence"
    with pytest.raises(ValueError, match="unsupported citation"):
        validate_assessment(review, {"source": "Use observed counts here."})


def test_unknown_and_blocking_findings_prevent_acceptance():
    review = assessment()
    review.findings[0].verdict = "unknown"
    assert not validate_assessment(review, {"source": "observed counts"})
    review.findings[0].verdict = "pass"
    review.blocking_findings.append("Data identity unverified")
    assert not validate_assessment(review, {"source": "observed counts"})


def test_duplicate_dimension_does_not_hide_missing_dimension():
    review = assessment()
    review.findings[0].dimension = review.findings[1].dimension
    with pytest.raises(ValueError, match="each scientific dimension"):
        validate_assessment(review, {"source": "observed counts"})


@pytest.mark.parametrize("content", ["invalid JSON", assessment().model_dump_json()])
def test_invalid_review_is_preserved_but_never_supported(tmp_path, monkeypatch, content):
    task = tmp_path / "task"
    task.mkdir()
    (task / "instruction.md").write_text("Unchanged fixture instructions.")
    monkeypatch.setattr(
        fidelity, "complete", lambda *a, **kw: SimpleNamespace(content=content, usage={})
    )
    result = fidelity.review(
        task=task,
        seed={"question_text": "observed counts", "input_manifest": {}},
        quality={},
        model=object(),
        directory=tmp_path / "review",
    )
    assert result["supported"] is False
    assert result["validation_error"]
    assert json.loads((tmp_path / "review/response.json").read_text())["content"] == content
    assert json.loads((tmp_path / "review/result.json").read_text()) == result
    assert (task / "instruction.md").read_text() == "Unchanged fixture instructions."
