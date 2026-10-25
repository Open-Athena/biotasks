"""Admit exactly the recorded one-question-repair resource topology."""


def require_question_repair(pipeline, number):
    prefix = f"autonomous-work/autonomous-panel-{number:03}"
    repair = pipeline["quality_repair"]
    assert repair["kind"] == "public_question_diagnosis"
    assert repair["target"] == "public_question"
    assert repair["allowance_consumed"] is True
    assert repair["validation_status"] == "grader_candidate_validated"
    assert repair["original_materialization"] == prefix + "/materialization"
    assert repair["original_grading"] == prefix + "/grading"
    assert repair["effective_materialization"] == prefix + "/materialization-question-repair"
    assert repair["effective_grading"] == prefix + "/grading-comparison-repair"
    assert pipeline["effective_materialization"] == repair["effective_materialization"]
    assert pipeline["effective_grading"] == repair["effective_grading"]


def require_cleanup(receipt, *, native):
    """Harbor can delete its sandbox before the outer owner cleanup lists it."""
    assert receipt["passed"]
    assert not receipt.get("creation_uncertain") and not receipt.get("remaining")
    boxes = receipt["sandboxes"]
    assert len(boxes) in ((0, 1) if native else (1,))
    for box in boxes:
        assert box["deleted"]
        assert {k: box[k] for k in ("cpu", "memory", "disk")} == {
            "cpu": 4,
            "memory": 8,
            "disk": 10,
        }
    return [box["id"] for box in boxes]
