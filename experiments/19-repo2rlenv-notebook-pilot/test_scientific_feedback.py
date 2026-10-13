"""Only validated GLM failures for the current task may drive repair."""

from types import SimpleNamespace

import pytest
from repo2rlenv.quality.loop.artifacts import task_identity
from repo2rlenv.quality.loop.runner import QualityLoop
from scientific_feedback import ScientificFeedbackLoop
from test_execution_integration import bundle
from test_fidelity import assessment


def test_feedback_is_blocking_only_for_its_exact_task(tmp_path, monkeypatch):
    task = bundle(tmp_path)
    review = SimpleNamespace(issues=[])
    review.model_copy = lambda *, update: SimpleNamespace(
        **update, model_dump=lambda **kw: {"issues": [i.model_dump() for i in update["issues"]]}
    )
    monkeypatch.setattr(QualityLoop, "_review", lambda *a, **kw: (review, "original-context"))
    loop = object.__new__(ScientificFeedbackLoop)
    loop.directory = tmp_path / "quality"
    scientific = assessment()
    for finding in scientific.findings:
        finding.citations[0].document = "task/instruction.md"
    scientific.findings[0].verdict = "fail"
    scientific.findings[0].explanation = "GLM-authored fixture finding"
    feedback = {
        "bundle_hash": task_identity(task),
        "assessment": scientific.model_dump(),
        "documents": {"task/instruction.md": (task / "instruction.md").read_text()},
    }
    loop.set_scientific_feedback(feedback)
    result, context = loop._review(task, [], "before")
    assert context == "original-context"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "blocking"
    assert result.issues[0].problem == "GLM-authored fixture finding"
    feedback["bundle_hash"] = "sha256:" + "0" * 64
    assert loop._review(task, [], "changed") == (review, "original-context")
    feedback["assessment"]["findings"][0]["citations"][0]["line"] = 999999
    with pytest.raises(ValueError, match="unsupported citation"):
        loop.set_scientific_feedback(feedback)
