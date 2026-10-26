"""An unrelated failure or incomplete lifetime cannot release a resource hold."""

from copy import deepcopy
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location("three_sdk", Path(__file__).with_name("reconcile_three_sdk.py"))
assert spec and spec.loader
module = module_from_spec(spec)
spec.loader.exec_module(module)


def pipeline(profile):
    rows = [
        {"name": name, "status": "completed", "started": i * 10, "finished": (i + 1) * 10}
        for i, name in enumerate(
            ("preparation", "setup", "replay", "specification", "construction")
        )
    ]
    result = {
        "status": "infrastructure_failed",
        "daytona_reserved_usd": 3,
        "started": 0,
        "finished": 50,
        "stages": rows,
        "failed_stage": "grading",
    }
    if profile == "construction_incomplete":
        result["failed_stage"] = "construction"
        rows[-1]["status"] = "incomplete"
        result["quality_repair"] = {
            "kind": "specification_review",
            "allowance_consumed": True,
            "target": "task_specification",
            "validation_status": "ready",
        }
    return result


@pytest.mark.parametrize("profile", tuple(module.SOURCES))
def test_exact_closed_prefix_profile(profile):
    budget = "3.00" if profile == "underfunded_before_grading" else "5.00"
    assert module.audit_profile(pipeline(profile), module.SOURCES[profile], budget) == profile


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_creator",
        "crosswired_family",
        "native_dispatch",
        "running",
        "scientific_rejection",
        "wrong_reservation",
        "incomplete_setup",
        "wrong_budget",
        "extra_repair",
        "overlap",
        "deadline",
    ],
)
def test_underfunded_profile_refuses_unproven_exposure(defect):
    value = pipeline("underfunded_before_grading")
    sources = deepcopy(module.SOURCES["underfunded_before_grading"])
    budget = "3.00"
    if defect == "unknown_creator":
        sources["reference_setup.py"] = "0" * 64
    elif defect == "crosswired_family":
        sources = module.SOURCES["construction_incomplete"]
    elif defect == "native_dispatch":
        value["stages"].append({"name": "native", "status": "incomplete"})
    elif defect == "running":
        value["status"] = "running"
    elif defect == "scientific_rejection":
        value["status"] = "rejected"
    elif defect == "wrong_reservation":
        value["daytona_reserved_usd"] = 4
    elif defect == "incomplete_setup":
        value["stages"][1]["status"] = "incomplete"
    elif defect == "wrong_budget":
        budget = "5.00"
    elif defect == "extra_repair":
        value["quality_repair"] = {"kind": "generated_construction"}
    elif defect == "overlap":
        value["stages"][2]["started"] = 0
    elif defect == "deadline":
        value["finished"] = 7201
    with pytest.raises(AssertionError):
        module.audit_profile(value, sources, budget)


@pytest.mark.parametrize(
    "key,value",
    [
        ("kind", "generated_construction"),
        ("target", "independent_solution"),
        ("allowance_consumed", False),
        ("validation_status", "blocked"),
    ],
)
def test_model_only_repair_cannot_be_crosswired_with_another_resource_topology(key, value):
    candidate = pipeline("construction_incomplete")
    candidate["quality_repair"][key] = value
    with pytest.raises(AssertionError):
        module.audit_profile(candidate, module.SOURCES["construction_incomplete"], "5.00")


@pytest.mark.parametrize(
    "upper,expected", [("0.143", "0.25"), ("0.151", "0.50"), ("0.401", "0.75"), ("0.901", "1.25")]
)
def test_rounding_never_releases_the_safety_margin(upper, expected):
    value = Decimal(upper)
    assert module.retained(value) == Decimal(expected)
    assert module.retained(value) >= value + Decimal("0.10")


@pytest.mark.parametrize("upper", ["0", "-1", "1", "NaN", "Infinity"])
def test_unbounded_or_invalid_exposure_is_refused(upper):
    with pytest.raises(AssertionError):
        module.retained(Decimal(upper))
