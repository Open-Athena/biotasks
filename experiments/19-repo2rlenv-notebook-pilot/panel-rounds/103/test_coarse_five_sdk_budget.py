import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "coarse_five_sdk_fixture", Path(__file__).with_name("coarse_five_sdk_budget.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence():
    return {
        name: {"started": 100, "finished": 200, "cleanup_verified": True} for name in module.FOLDERS
    }, {"started": 0, "finished": 10000}


def test_full_profile_is_charged_for_every_session_without_overlap_credit():
    sessions, pipeline = evidence()
    result = module.full_profile(sessions, pipeline)
    assert result["retained_usd"] == "4.00" and result["priced_seconds_per_sandbox"] == 8100
    assert result["full_profile_resource_bound_usd"] == "3.738150"


@pytest.mark.parametrize("defect", ["missing", "extra", "unclean", "too_long", "outside"])
def test_unknown_or_unclosed_profiles_are_not_reconciled(defect):
    sessions, pipeline = evidence()
    if defect == "missing":
        sessions.pop("replay")
    elif defect == "extra":
        sessions["unrecorded"] = dict(sessions["replay"])
    elif defect == "unclean":
        sessions["replay"]["cleanup_verified"] = False
    elif defect == "too_long":
        sessions["replay"]["finished"] = 9000
    elif defect == "outside":
        sessions["replay"]["started"] = -1
    with pytest.raises(AssertionError):
        module.full_profile(sessions, pipeline)
