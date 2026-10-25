"""Scientific failure labels cannot substitute for complete resource evidence."""

from copy import deepcopy
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    spec = spec_from_file_location("resource_shape_under_test", ROOT / relative)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["065/reconcile_sdk_only.py", "070/closed_session_bound.py"])
def classifier(request):
    return load(request.param).terminal_state


def pipeline(status):
    return {
        "status": status,
        "failed_stage": "grading" if status == "infrastructure_failed" else None,
        "stages": [
            {
                "name": name,
                "status": "completed"
                if index < 5
                else "rejected"
                if status == "rejected"
                else "incomplete",
            }
            for index, name in enumerate(
                ["preparation", "setup", "replay", "specification", "construction", "grading"]
            )
        ],
    }


@pytest.mark.parametrize(
    ("status", "host_state"), [("rejected", "SUCCEEDED"), ("infrastructure_failed", "FAILED")]
)
def test_known_terminal_outcomes_keep_distinct_host_states(classifier, status, host_state):
    assert classifier(pipeline(status)) == host_state


@pytest.mark.parametrize("status", ["rejected", "infrastructure_failed"])
@pytest.mark.parametrize(
    "defect", ["running", "earlier_incomplete", "wrong_last_state", "extra_stage", "wrong_order"]
)
def test_other_or_incomplete_topologies_are_not_admitted(classifier, status, defect):
    value = pipeline(status)
    if defect == "running":
        value["status"] = "running"
    elif defect == "earlier_incomplete":
        value["stages"][1]["status"] = "incomplete"
    elif defect == "wrong_last_state":
        value["stages"][-1]["status"] = "completed"
    elif defect == "extra_stage":
        value["stages"].append({"name": "native", "status": "completed"})
    else:
        value["stages"][2], value["stages"][3] = value["stages"][3], value["stages"][2]
    with pytest.raises(AssertionError):
        classifier(value)


@pytest.mark.parametrize("failure_stage", [None, "setup", "construction", "native"])
def test_infrastructure_failure_must_match_the_final_record(classifier, failure_stage):
    value = pipeline("infrastructure_failed")
    value["failed_stage"] = failure_stage
    with pytest.raises(AssertionError):
        classifier(value)


@pytest.mark.parametrize("defect", [None, "oversized", "missing_cleanup", "present", "too_long"])
def test_failed_run_keeps_the_same_full_resource_bound(defect):
    cases = load("065/test_reconcile_sdk_only.py")
    value, claims, cleanup = deepcopy(cases.evidence())
    value["status"] = "infrastructure_failed"
    value["failed_stage"] = "grading"
    value["stages"][-1]["status"] = "incomplete"
    if defect == "oversized":
        claims[0]["resources"]["cpu"] = 8
    elif defect == "missing_cleanup":
        cleanup["original_all_cleanup_passed"] = False
    elif defect == "present":
        cleanup["sandboxes"] = [claims[0]]
    elif defect == "too_long":
        value["finished"] = 7201
    if defect is None:
        assert cases.module.audit_shape(value, claims, cleanup) == Decimal("2.769000")
    else:
        with pytest.raises(AssertionError):
            cases.module.audit_shape(value, claims, cleanup)
