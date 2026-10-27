import importlib.util
from copy import deepcopy
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


def test_observed_refinement_charges_all_overlapping_lifetimes_and_both_margins():
    sessions, pipeline = evidence()
    full = module.full_profile(sessions, pipeline)
    prior = {**deepcopy(full), "applied": True}
    result = module.observed_profile(full, prior)
    # Five simultaneous100-second sessions each cost700seconds, never just
    # one shared interval. The300-second allowance is included at both ends.
    assert result["observed_full_lifetimes_resource_bound_usd"] == "0.323050"
    assert result["retained_usd"] == "0.50"
    assert prior["retained_usd"] == "4.00"


@pytest.mark.parametrize(
    "defect", ["unapplied", "clock", "full_price", "margin", "hold", "missing_session"]
)
def test_refinement_rejects_unapplied_or_different_preceding_proofs(defect):
    sessions, pipeline = evidence()
    full = module.full_profile(sessions, pipeline)
    prior = {**deepcopy(full), "applied": True}
    if defect == "unapplied":
        prior["applied"] = False
    elif defect == "clock":
        prior["actual_clock_cross_checks"]["replay"]["session_started"] = "99"
    elif defect == "full_price":
        prior["full_profile_resource_bound_usd"] = "0.01"
    elif defect == "margin":
        prior["margin_usd"] = "0"
    elif defect == "hold":
        prior["retained_usd"] = "1.00"
    else:
        prior["actual_clock_cross_checks"].pop("replay")
    with pytest.raises(AssertionError):
        module.observed_profile(full, prior)
