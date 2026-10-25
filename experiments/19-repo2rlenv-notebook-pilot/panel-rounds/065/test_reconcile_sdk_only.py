"""Reject weaker or different lifecycle evidence rather than releasing its hold."""

from copy import deepcopy
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location("sdk_only_bound", Path(__file__).with_name("reconcile_sdk_only.py"))
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)


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
    claims = [
        {
            "id": str(i),
            "owner": str(i),
            "state": "created",
            "resources": {"cpu": 4, "memory": 8, "disk": 10},
        }
        for i in range(4)
    ]
    cleanup = {
        "owners": [str(i) for i in range(4)],
        "complete": True,
        "original_all_cleanup_passed": True,
        "fresh_original_ids_absent": True,
        "sandboxes": [],
    }
    return pipeline, claims, cleanup


def test_full_concurrent_lifetimes_are_priced():
    assert module.audit_shape(*evidence()) == Decimal("2.769000")


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
    with pytest.raises(AssertionError):
        module.audit_shape(p, claims, cleanup)
