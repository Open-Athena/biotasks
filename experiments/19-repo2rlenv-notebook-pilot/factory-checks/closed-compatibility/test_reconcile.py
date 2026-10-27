import copy

import pytest
from reconcile import CREATOR, CREATOR_SHA, bounded_control


def evidence():
    return (
        {
            "resources": {"cpus": 4, "memory_gib": 8, "disk_gib": 10, "gpu": False},
            "seconds": 300,
            "cleanup_seconds": 180,
            "reservation_usd": "1.00",
            "model_calls": 0,
            "source_sha256": {CREATOR: CREATOR_SHA},
            "owner": "fixture",
        },
        {
            "status": "compatibility_observed",
            "cleanup_verified": True,
            "new_model_calls": 0,
            "scientific_computation": False,
            "cases": [{"passed": True}] * 3,
            "started": 100,
            "finished": 110,
        },
        {
            "state": "created",
            "owner": "fixture",
            "id": "one",
            "resources": {"cpu": 4, "memory": 8, "disk": 10},
        },
        {
            "passed": True,
            "remaining": [],
            "sandboxes": [{"id": "one", "deleted": True, "cpu": 4, "memory": 8, "disk": 10}],
        },
        {
            "complete": True,
            "fresh_original_id_absent": True,
            "fresh_owner_list_empty": True,
            "original_cleanup_verified": True,
            "owner": "fixture",
            "original_id": "one",
            "observed_at": "1970-01-01T00:02:00+00:00",
        },
    )


def test_prices_the_entire_profile_and_margins_without_rewriting_receipts():
    args = evidence()
    before = copy.deepcopy(args)
    result = bounded_control(*args)
    assert result["full_approved_lifetime_plus_margins_seconds"] == 1080
    assert result["retained_usd"] == "0.25" and args == before


@pytest.mark.parametrize(
    "defect",
    [
        "resources",
        "creator",
        "unfinished",
        "too_long",
        "extra_box",
        "different_id",
        "not_deleted",
        "present",
        "old_absence",
        "science",
    ],
)
def test_unknown_or_incomplete_controls_keep_their_original_hold(defect):
    args = evidence()
    config, result, claim, cleanup, fresh = args
    if defect == "resources":
        config["resources"]["cpus"] = 8
    elif defect == "creator":
        config["source_sha256"][CREATOR] = "unknown"
    elif defect == "unfinished":
        result["cleanup_verified"] = False
    elif defect == "too_long":
        result["finished"] = 600
    elif defect == "extra_box":
        cleanup["sandboxes"] *= 2
    elif defect == "different_id":
        fresh["original_id"] = "other"
    elif defect == "not_deleted":
        cleanup["sandboxes"][0]["deleted"] = False
    elif defect == "present":
        fresh["fresh_original_id_absent"] = False
    elif defect == "old_absence":
        fresh["observed_at"] = "1970-01-01T00:01:00+00:00"
    elif defect == "science":
        result["scientific_computation"] = True
    with pytest.raises(AssertionError):
        bounded_control(*args)
