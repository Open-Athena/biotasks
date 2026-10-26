"""Native cleanup can be complete without manufacturing a missing ID."""

import copy

import pytest
from verify_regular_cleanup import check_native_ownership


def native():
    return {
        "state": "completed",
        "returncode": 0,
        "job_id": "native-job",
        "command": ["harbor", "run", "--ek", 'labels={"repo2rlenv.job":"native-job"}'],
        "cleanup": {"passed": True, "sandboxes": [], "remaining": []},
    }


def test_completed_native_owner_can_be_checked_without_inventing_an_id():
    record = native()
    before = copy.deepcopy(record)
    assert check_native_ownership(record) == "native-job"
    assert record == before and not record["cleanup"]["sandboxes"]


@pytest.mark.parametrize(
    "defect", ["failed", "nonzero", "uncertain", "wrong_owner", "missing_label", "duplicate_label"]
)
def test_native_absence_requires_a_completed_creation_and_the_actual_owner_label(defect):
    record = native()
    if defect == "failed":
        record["state"] = "failed"
    elif defect == "nonzero":
        record["returncode"] = 1
    elif defect == "uncertain":
        record["cleanup"]["creation_uncertain"] = True
    elif defect == "wrong_owner":
        record["command"][-1] = 'labels={"repo2rlenv.job":"another-job"}'
    elif defect == "missing_label":
        record["command"] = record["command"][:2]
    elif defect == "duplicate_label":
        record["command"] += record["command"][-2:]
    with pytest.raises(AssertionError):
        check_native_ownership(record)
