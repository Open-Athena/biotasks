import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "closed_sdk_prefix_fixture", Path(__file__).with_name("reconcile_closed_sdk_prefix.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence(*, replay=False):
    pipeline = {
        "started": 0,
        "finished": 1000,
        "operator_interventions": 0,
        "quality_repair": None,
        "daytona_reserved_usd": 2 if replay else 1,
        "status": "infrastructure_failed" if replay else "rejected",
        "failed_stage": "replay" if replay else None,
        "stages": [
            {"name": "preparation", "status": "completed", "started": 0, "finished": 50},
            {
                "name": "setup",
                "status": "completed" if replay else "rejected",
                "started": 50,
                "finished": 400,
            },
        ],
    }
    if replay:
        pipeline["stages"].append(
            {"name": "replay", "status": "incomplete", "started": 400, "finished": 1000}
        )
    sessions = {"setup-raw": {"started": 100, "finished": 350, "cleanup_verified": True}}
    if replay:
        sessions["replay"] = {"started": 450, "finished": 950, "cleanup_verified": True}
    return pipeline, sessions


@pytest.mark.parametrize("replay,expected", [(False, "0.25"), (True, "0.50")])
def test_complete_lifetimes_receive_both_cleanup_margins(replay, expected):
    pipeline, sessions = evidence(replay=replay)
    records, upper, retained = module.price(pipeline, sessions)
    assert str(retained) == expected
    assert records["setup-raw"]["priced_seconds"] == "850"
    if replay:
        assert records["replay"]["priced_seconds"] == "1100"
    assert upper > 0
    assert sessions["setup-raw"]["finished"] == 350


@pytest.mark.parametrize(
    "defect",
    [
        "native",
        "extra_stage",
        "repair",
        "manual_edit",
        "not_terminal",
        "wrong_failure",
        "reservation",
        "too_long",
        "stage_overlap",
    ],
)
def test_unknown_or_incomplete_campaign_shapes_keep_their_holds(defect):
    pipeline, _ = evidence(replay=True)
    if defect == "native":
        pipeline["stages"][-1]["name"] = "native"
    elif defect == "extra_stage":
        pipeline["stages"].append(deepcopy(pipeline["stages"][-1]))
    elif defect == "repair":
        pipeline["quality_repair"] = {"kind": "unknown"}
    elif defect == "manual_edit":
        pipeline["operator_interventions"] = 1
    elif defect == "not_terminal":
        pipeline["status"] = "running"
    elif defect == "wrong_failure":
        pipeline["failed_stage"] = "setup"
    elif defect == "reservation":
        pipeline["daytona_reserved_usd"] = 1
    elif defect == "too_long":
        pipeline["finished"] = 7201
    else:
        pipeline["stages"][-1]["started"] = 399
    with pytest.raises(AssertionError):
        module.profile(pipeline)


@pytest.mark.parametrize("defect", ["missing", "extra", "unclean", "before_stage", "after_stage"])
def test_unclosed_missing_or_misbound_session_clocks_cannot_release_funds(defect):
    pipeline, sessions = evidence(replay=True)
    if defect == "missing":
        del sessions["replay"]
    elif defect == "extra":
        sessions["unexpected"] = dict(sessions["replay"])
    elif defect == "unclean":
        sessions["replay"]["cleanup_verified"] = False
    elif defect == "before_stage":
        sessions["replay"]["started"] = 399
    else:
        sessions["replay"]["finished"] = 1001
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)
