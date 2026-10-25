"""Do not reconcile an extra or unresolved repair as the admitted topology."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location(
    "question_resource_profile", Path(__file__).with_name("question_repair_resource_profile.py")
)
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    prefix = "autonomous-work/autonomous-panel-999"
    return {
        "quality_repair": {
            "kind": "public_question_diagnosis",
            "target": "public_question",
            "allowance_consumed": True,
            "validation_status": "grader_candidate_validated",
            "original_materialization": prefix + "/materialization",
            "original_grading": prefix + "/grading",
            "effective_materialization": prefix + "/materialization-question-repair",
            "effective_grading": prefix + "/grading-comparison-repair",
        },
        "effective_materialization": prefix + "/materialization-question-repair",
        "effective_grading": prefix + "/grading-comparison-repair",
    }


def test_exact_one_question_repair_profile():
    module.require_question_repair(fixture(), 999)


@pytest.mark.parametrize(
    "field",
    [
        "kind",
        "target",
        "allowance_consumed",
        "validation_status",
        "original_materialization",
        "original_grading",
        "effective_materialization",
        "effective_grading",
    ],
)
def test_reject_different_or_incomplete_repair(field):
    pipeline = fixture()
    pipeline["quality_repair"][field] = False if field == "allowance_consumed" else "different"
    with pytest.raises(AssertionError):
        module.require_question_repair(pipeline, 999)


def test_reject_final_view_not_bound_to_repair():
    pipeline = fixture()
    pipeline["effective_grading"] += "-other"
    with pytest.raises(AssertionError):
        module.require_question_repair(pipeline, 999)


@pytest.mark.parametrize("native", [False, True])
def test_complete_original_cleanup(native):
    box = {"id": "a", "deleted": True, "cpu": 4, "memory": 8, "disk": 10}
    assert module.require_cleanup({"passed": True, "sandboxes": [box]}, native=native) == ["a"]


def test_harbor_cleanup_can_already_be_absent():
    assert module.require_cleanup({"passed": True, "sandboxes": []}, native=True) == []
    with pytest.raises(AssertionError):
        module.require_cleanup({"passed": True, "sandboxes": []}, native=False)


@pytest.mark.parametrize("defect", ["pending", "uncertain", "failed", "oversized", "extra"])
def test_refuse_incomplete_or_different_cleanup(defect):
    box = {"id": "a", "deleted": True, "cpu": 4, "memory": 8, "disk": 10}
    receipt = {"passed": True, "sandboxes": [box]}
    if defect == "pending":
        receipt["remaining"] = ["a"]
    elif defect == "uncertain":
        receipt["creation_uncertain"] = True
    elif defect == "failed":
        receipt["passed"] = False
    elif defect == "oversized":
        box["cpu"] = 8
    else:
        receipt["sandboxes"].append(box.copy())
    with pytest.raises(AssertionError):
        module.require_cleanup(receipt, native=True)
