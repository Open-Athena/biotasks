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


def implementation():
    return {
        "run_autonomous.py": "66bfc69435da1de099cdfc07637913abe332344c10e6725ca82ac382fe522188",
        "run_reference_setup.py": "fc83bf2ecd9f201b4bfd8c47cb07740619d09c66fc8df5a37435eb95af5b2d0b",
        "reference_setup.py": "f71e80976057dc58d106e179076559a76658e160920d4b7620ac2c032ee607f2",
    }


@pytest.mark.parametrize("crosswire", [None, "controller", "runner", "setup"])
def test_earlier_blocking_family_requires_its_complete_exact_triple(crosswire):
    sources = {
        "run_autonomous.py": "d90fd8c6f121d46c0f6bc6faea54172f18035887ba07dca076609f2e6d16bae9",
        "run_reference_setup.py": "34ae1de16e432cb6926e9d0f56158a35d65bebe3b06b5c4769f86d53c145eb2a",
        "reference_setup.py": "a73ff8ccfbc5281a51ba55817316f33d8d3398d4227c4218f6bf0e553c3b2c83",
    }
    names = {
        "controller": "run_autonomous.py",
        "runner": "run_reference_setup.py",
        "setup": "reference_setup.py",
    }
    if crosswire is None:
        assert module.admitted_implementation(sources) == sources
    else:
        name = names[crosswire]
        sources[name] = implementation()[name]
        with pytest.raises(AssertionError):
            module.admitted_implementation(sources)


@pytest.mark.parametrize("annotated", [False, True])
def test_exact_known_creators_share_resource_lifecycle(annotated):
    sources = implementation()
    if not annotated:
        sources["run_reference_setup.py"] = (
            "e2c603cb81c65263572b6b3417ecf6828500a50e978809e579123b2da3e974fc"
        )
    assert module.admitted_implementation(sources) == sources


@pytest.mark.parametrize("name", tuple(implementation()))
def test_unknown_creator_or_lifecycle_is_refused(name):
    sources = implementation()
    sources[name] = "0" * 64
    with pytest.raises(AssertionError):
        module.admitted_implementation(sources)


def test_extra_implementation_is_refused():
    sources = implementation()
    sources["other_creator.py"] = "0" * 64
    with pytest.raises(AssertionError):
        module.admitted_implementation(sources)


def test_known_typed_repair_pair_and_mixed_versions():
    sources = implementation()
    sources["run_reference_setup.py"] = (
        "9a2354335a74410931129d58526c16d121ddce2f86b0b35806dd75378d4d60f8"
    )
    with pytest.raises(AssertionError):
        module.admitted_implementation(sources)
    sources["reference_setup.py"] = (
        "d85850aea0d2f70242d45d1abb898aac5b9b7742aaf1d14371bee775d2fea8b7"
    )
    assert module.admitted_implementation(sources) == sources
    sources["run_reference_setup.py"] = implementation()["run_reference_setup.py"]
    with pytest.raises(AssertionError):
        module.admitted_implementation(sources)


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


def test_unavailable_analytics_cannot_reduce_complete_lifetime_bound():
    session, pipeline, periods, margin = evidence()
    observed = module.closed_session_bound(session, pipeline, periods, margin)
    absent = module.closed_session_bound(session, pipeline, [], margin)
    assert absent["resource_upper_bound_usd"] == observed["resource_upper_bound_usd"]
    assert absent["priced_seconds"] == observed["priced_seconds"]
    assert absent["provider_reported_price_usd"] is None


@pytest.mark.parametrize(
    "defect",
    [
        "nan",
        "bool",
        "reversed",
        "before_pipeline",
        "after_pipeline",
        "no_cleanup",
        "invalid_periods",
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
    elif defect == "invalid_periods":
        periods = None
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


@pytest.mark.parametrize(
    "count,retained,key",
    [
        (4, "3.00", "sdk_only_four_full_lifetimes_no_serial_assumption"),
        (5, "4.00", "sdk_only_five_full_lifetimes_one_comparison_repair_no_serial_assumption"),
    ],
)
def test_admit_exact_previous_profile(count, retained, key):
    folders, amount, _ = module.admitted_profile(
        {"applied": True, "profile": key, "retained_usd": retained, "priced_sandboxes": count}
    )
    assert len(folders) == count and amount == Decimal(retained)


@pytest.mark.parametrize("defect", ["count", "amount", "unapplied", "unknown"])
def test_refuse_other_previous_profile(defect):
    previous = {
        "applied": True,
        "profile": "sdk_only_four_full_lifetimes_no_serial_assumption",
        "retained_usd": "3.00",
        "priced_sandboxes": 4,
    }
    if defect == "count":
        previous["priced_sandboxes"] = 5
    elif defect == "amount":
        previous["retained_usd"] = "5.00"
    elif defect == "unapplied":
        previous["applied"] = False
    else:
        previous["profile"] = "unknown"
    with pytest.raises(AssertionError):
        module.admitted_profile(previous)
