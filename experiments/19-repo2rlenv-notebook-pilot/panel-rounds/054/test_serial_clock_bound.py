"""Uncertain, overlapping or unproven intervals must not release old holds."""

from copy import deepcopy
from decimal import Decimal

import pytest
from serial_clock_bound import observed_bound


def fixture():
    names = ["preparation", "setup", "replay", "specification", "construction", "grading", "native"]
    stages = [
        {"name": name, "status": "completed", "started": i * 100, "finished": (i + 1) * 100}
        for i, name in enumerate(names)
    ]
    pipeline = {"status": "validated", "started": 0, "finished": 700, "stages": stages}
    sessions = {
        r["name"]: {
            "started": r["started"] + 1,
            "finished": r["finished"] - 1,
            "cleanup_verified": True,
        }
        for r in stages
        if r["name"] in {"setup", "replay", "construction", "grading"}
    }
    native = [(601, 620), (621, 640), (641, 699)]
    sources = {
        "run_autonomous.py": "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188",
        "run_reference_setup.py": "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc",
        "reference_setup.py": "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
    }
    return pipeline, sessions, native, sources, Decimal("0.332280")


def test_entire_campaign_idle_and_model_time_and_both_boundary_margins_are_priced():
    result = observed_bound(*fixture())
    assert result["full_resource_profiles"] == 2
    assert Decimal(result["seconds_each_including_both_300_second_margins"]) == 1300
    assert Decimal(result["resource_upper_bound_usd"]) == 2 * Decimal("0.332280") * 1300 / 3600
    assert result["retained_usd"] == "0.50"


@pytest.mark.parametrize(
    "defect",
    [
        "infrastructure_failure",
        "stage_incomplete",
        "wrong_stage",
        "overlapping_stage",
        "missing_session",
        "no_cleanup",
        "session_before_create_window",
        "session_after_cleanup_window",
        "zero_session",
        "nan",
        "bool",
        "pipeline_too_short",
        "deadline",
        "missing_native",
        "overlapping_native",
        "native_outside",
        "unknown_source",
        "different_rate",
    ],
)
def test_refuse_ineligible_or_unproved_exposure(defect):
    pipeline, sessions, native, sources, rate = deepcopy(fixture())
    if defect == "infrastructure_failure":
        pipeline["status"] = "infrastructure_failed"
    elif defect == "stage_incomplete":
        pipeline["stages"][4]["status"] = "incomplete"
    elif defect == "wrong_stage":
        pipeline["stages"][4]["name"] = "construction-repair"
    elif defect == "overlapping_stage":
        pipeline["stages"][4]["started"] = 350
    elif defect == "missing_session":
        del sessions["construction"]
    elif defect == "no_cleanup":
        sessions["setup"]["cleanup_verified"] = False
    elif defect == "session_before_create_window":
        sessions["setup"]["started"] = 90
    elif defect == "session_after_cleanup_window":
        sessions["setup"]["finished"] = 201
    elif defect == "zero_session":
        sessions["setup"]["finished"] = sessions["setup"]["started"]
    elif defect == "nan":
        sessions["setup"]["finished"] = float("nan")
    elif defect == "bool":
        sessions["setup"]["started"] = True
    elif defect == "pipeline_too_short":
        pipeline["finished"] = 650
    elif defect == "deadline":
        pipeline["finished"] = 7201
    elif defect == "missing_native":
        native.pop()
    elif defect == "overlapping_native":
        native[1] = (619, 640)
    elif defect == "native_outside":
        native[-1] = (641, 701)
    elif defect == "unknown_source":
        sources["reference_setup.py"] = "0" * 64
    elif defect == "different_rate":
        rate = Decimal("0.1")
    with pytest.raises(AssertionError):
        observed_bound(pipeline, sessions, native, sources, rate)
