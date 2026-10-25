"""Reject weaker or different lifecycle evidence rather than releasing its hold."""

from copy import deepcopy
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location(
    "sdk_only_bound", Path(__file__).with_name("reconcile_sdk_comparison_repair.py")
)
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact_earlier_blocking_family_is_admitted():
    module.admit_sources(module.EARLY_BLOCKING_SOURCES)


@pytest.mark.parametrize("name", tuple(module.EARLY_BLOCKING_SOURCES))
def test_earlier_family_rejects_unknown_or_crosswired_source(name):
    sources = dict(module.EARLY_BLOCKING_SOURCES)
    sources[name] = module.CONTROLLER if name == "run_autonomous.py" else "0" * 64
    with pytest.raises(AssertionError):
        module.admit_sources(sources)


def evidence():
    stages = ["preparation", "setup", "replay", "specification", "construction", "grading"]
    pipeline = {
        "status": "rejected",
        "started": 0,
        "finished": 100,
        "stages": [
            {
                "name": name,
                "status": "completed" if i < 5 else "rejected",
                "started": i * 10,
                "finished": i * 10 + 9,
            }
            for i, name in enumerate(stages)
        ],
    }
    prefix = "autonomous-work/autonomous-panel-999"
    pipeline["quality_repair"] = {
        "kind": "comparison_diagnosis",
        "target": "independent_solution",
        "allowance_consumed": True,
        "validation_status": "question_review_blocked",
        "original_materialization": prefix + "/materialization",
        "original_grading": prefix + "/grading",
        "effective_materialization": prefix + "/materialization",
        "effective_grading": prefix + "/grading-comparison-repair",
    }
    claims = [
        {
            "id": str(i),
            "owner": str(i),
            "state": "created",
            "resources": {"cpu": 4, "memory": 8, "disk": 10},
        }
        for i in range(5)
    ]
    cleanup = {
        "owners": [str(i) for i in range(5)],
        "complete": True,
        "original_all_cleanup_passed": True,
        "fresh_original_ids_absent": True,
        "sandboxes": [],
    }
    return pipeline, claims, cleanup


def test_full_concurrent_lifetimes_are_priced():
    assert module.audit_shape(*evidence()) == Decimal("3.461250")


def test_one_public_question_repair_prices_the_same_five_lifetimes():
    pipeline, claims, cleanup = evidence()
    repair = pipeline["quality_repair"]
    repair["target"] = "public_question"
    repair["validation_status"] = "independent_comparison_unresolved"
    repair["effective_materialization"] += "-question-repair"
    assert module.audit_shape(pipeline, claims, cleanup) == Decimal("3.461250")
    repair["effective_materialization"] += "-second"
    with pytest.raises(AssertionError):
        module.audit_shape(pipeline, claims, cleanup)


@pytest.mark.parametrize(
    "defect",
    [
        "extra_owner",
        "oversized",
        "duplicate",
        "still_present",
        "missing_cleanup",
        "over_lifetime",
        "native_stage",
        "overlapping_stage_records",
        "unfinished",
        "second_repair",
        "unresolved_repair",
    ],
)
def test_refuse_different_or_incomplete_profile(defect):
    p, claims, cleanup = deepcopy(evidence())
    if defect == "extra_owner":
        claims.append(deepcopy(claims[0]))
    elif defect == "oversized":
        claims[0]["resources"]["memory"] = 16
    elif defect == "duplicate":
        claims[1]["id"] = claims[0]["id"]
    elif defect == "still_present":
        cleanup["sandboxes"] = [claims[0]]
    elif defect == "missing_cleanup":
        cleanup["original_all_cleanup_passed"] = False
    elif defect == "over_lifetime":
        p["finished"] = 7201
    elif defect == "native_stage":
        p["stages"].append({"name": "native"})
    elif defect == "overlapping_stage_records":
        p["stages"][1]["started"] = 0
    elif defect == "unfinished":
        p["stages"][-1]["status"] = "incomplete"
    elif defect == "second_repair":
        p["quality_repair"]["effective_grading"] += "-second"
    elif defect == "unresolved_repair":
        p["quality_repair"]["validation_status"] = "incomplete"
    with pytest.raises(AssertionError):
        module.audit_shape(p, claims, cleanup)
