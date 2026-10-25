"""A missing/invalid lifecycle or provider discrepancy cannot release a hold."""

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location(
    "closed_session_bound", Path(__file__).with_name("closed_session_bound.py")
)
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)


def evidence():
    start = 1790000000
    session = {"started": start, "finished": start + 100, "cleanup_verified": True}
    pipeline = {"started": start - 10, "finished": start + 110}
    periods = [
        {
            "startAt": datetime.fromtimestamp(start + 1, UTC).isoformat(),
            "endAt": datetime.fromtimestamp(start + 99, UTC).isoformat(),
            "cpu": 4,
            "ramGB": 8,
            "diskGB": 10,
            "gpu": 0,
            "price": 0.001,
        }
    ]
    return session, pipeline, periods, 300


def test_entire_session_and_both_cleanup_margins_are_priced():
    result = module.closed_session_bound(*evidence())
    assert Decimal(result["priced_seconds"]) == 700
    assert Decimal(result["resource_upper_bound_usd"]) == 700 * module.RATE / 3600
    assert Decimal(result["provider_reported_price_usd"]) == Decimal("0.001")


def test_provider_gaps_do_not_reduce_the_bound():
    arguments = evidence()
    first = module.closed_session_bound(*arguments)
    arguments[2][0]["endAt"] = datetime.fromtimestamp(arguments[0]["started"] + 2, UTC).isoformat()
    assert (
        module.closed_session_bound(*arguments)["resource_upper_bound_usd"]
        == first["resource_upper_bound_usd"]
    )


@pytest.mark.parametrize(
    "defect",
    [
        "nan",
        "bool",
        "reversed",
        "before_pipeline",
        "after_pipeline",
        "no_cleanup",
        "no_periods",
        "gpu",
        "larger_resource",
        "negative_price",
        "excess_price",
        "outside",
        "overlap",
        "different_margin",
    ],
)
def test_refuse_incomplete_or_inconsistent_lifetimes(defect):
    session, pipeline, periods, margin = deepcopy(evidence())
    if defect == "nan":
        session["started"] = float("nan")
    elif defect == "bool":
        session["started"] = True
    elif defect == "reversed":
        session["finished"] = session["started"]
    elif defect == "before_pipeline":
        session["started"] -= 100
    elif defect == "after_pipeline":
        session["finished"] += 100
    elif defect == "no_cleanup":
        session["cleanup_verified"] = False
    elif defect == "no_periods":
        periods.clear()
    elif defect == "gpu":
        periods[0]["gpu"] = 1
    elif defect == "larger_resource":
        periods[0]["ramGB"] = 16
    elif defect == "negative_price":
        periods[0]["price"] = -1
    elif defect == "excess_price":
        periods[0]["price"] = 100
    elif defect == "outside":
        periods[0]["startAt"] = datetime.fromtimestamp(session["started"] - 1, UTC).isoformat()
    elif defect == "overlap":
        periods.append(periods[0].copy())
    elif defect == "different_margin":
        margin = 0
    with pytest.raises(AssertionError):
        module.closed_session_bound(session, pipeline, periods, margin)
