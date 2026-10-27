import importlib.util
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "closed_campaign_fixture", Path(__file__).with_name("reconcile_closed_campaign.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence(native=False):
    names = ["preparation", "setup", "replay", "specification", "construction", "grading"]
    bounds = [(0, 10), (10, 210), (210, 410), (410, 610), (610, 810), (810, 1410)]
    if native:
        names.append("native")
        bounds.append((1410, 1610))
    stages = [
        {"name": name, "status": "completed", "started": left, "finished": right}
        for name, (left, right) in zip(names, bounds, strict=True)
    ]
    stages[-1]["status"] = "incomplete"
    pipeline = {
        "autonomous": True,
        "operator_interventions": 0,
        "status": "infrastructure_failed",
        "failed_stage": names[-1],
        "daytona_reserved_usd": 5 if native else 4,
        "started": 0,
        "finished": bounds[-1][1],
        "stages": stages,
        "quality_repair": {
            "kind": "specification_review" if native else "comparison_diagnosis",
            "allowance_consumed": True,
            "target": "public_question",
        },
    }
    sessions = {
        name: {"started": start, "finished": start + 100, "cleanup_verified": True}
        for name, start in [
            ("setup-raw", 20),
            ("replay", 220),
            ("materialization-raw", 620),
            ("grading", 820),
        ]
    }
    if not native:
        sessions["grading-comparison-repair"] = {
            "started": 1020,
            "finished": 1120,
            "cleanup_verified": True,
        }
    return pipeline, sessions


@pytest.mark.parametrize("native,retained", [(False, "0.50"), (True, "1.50")])
def test_every_sdk_gets_both_margins_and_native_hold_is_not_refunded(native, retained):
    pipeline, sessions = evidence(native)
    before = deepcopy((pipeline, sessions))
    clocks, upper, native_hold, keep = module.price(pipeline, sessions)
    assert all(row["priced_seconds"] == "700" for row in clocks.values())
    assert native_hold == (1 if native else 0)
    assert keep == Decimal(retained) and upper + native_hold + Decimal("0.10") <= keep
    assert (pipeline, sessions) == before


def test_overlapping_sdk_lifetimes_receive_no_serialization_or_idle_discount():
    pipeline, sessions = evidence()
    sessions["grading-comparison-repair"].update(started=820, finished=1120)
    clocks, upper, _, _ = module.price(pipeline, sessions)
    assert clocks["grading"]["priced_seconds"] == "700"
    assert clocks["grading-comparison-repair"]["priced_seconds"] == "900"
    assert upper == sum(Decimal(row["resource_upper_bound_usd"]) for row in clocks.values())


@pytest.mark.parametrize(
    "defect",
    [
        "running",
        "unknown_stage",
        "wrong_failure",
        "wrong_reservation",
        "manual_edit",
        "unapproved_duration",
        "stage_overlap",
        "unknown_repair",
        "extra_repair",
        "failed_stage_completed",
    ],
)
def test_unknown_or_nonterminal_profiles_cannot_release_holds(defect):
    pipeline, sessions = evidence()
    if defect == "running":
        pipeline["status"] = "running"
    elif defect == "unknown_stage":
        pipeline["stages"].append(dict(pipeline["stages"][-1]))
    elif defect == "wrong_failure":
        pipeline["failed_stage"] = "setup"
    elif defect == "wrong_reservation":
        pipeline["daytona_reserved_usd"] = 3
    elif defect == "manual_edit":
        pipeline["operator_interventions"] = 1
    elif defect == "unapproved_duration":
        pipeline["finished"] = 7201
    elif defect == "stage_overlap":
        pipeline["stages"][1]["started"] = 0
    elif defect == "unknown_repair":
        pipeline["quality_repair"]["kind"] = "unknown"
    elif defect == "extra_repair":
        pipeline["quality_repair"]["allowance_consumed"] = False
    else:
        pipeline["stages"][-1]["status"] = "completed"
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)


@pytest.mark.parametrize("defect", ["missing", "extra", "unclosed", "before_stage", "after_stage"])
def test_incomplete_or_misbound_session_clocks_cannot_release_holds(defect):
    pipeline, sessions = evidence()
    if defect == "missing":
        del sessions["grading"]
    elif defect == "extra":
        sessions["unknown"] = dict(sessions["grading"])
    elif defect == "unclosed":
        sessions["grading"]["cleanup_verified"] = False
    elif defect == "before_stage":
        sessions["grading"]["started"] = 800
    else:
        sessions["grading"]["finished"] = 1500
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)
