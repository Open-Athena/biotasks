import copy
import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "setup_replay_prefix", Path(__file__).with_name("reconcile_setup_replay_prefix.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence():
    pipeline = {
        "status": "infrastructure_failed",
        "failed_stage": "replay",
        "started": 100,
        "finished": 1000,
        "stages": [
            {"name": "preparation", "status": "completed", "started": 100, "finished": 200},
            {"name": "setup", "status": "completed", "started": 200, "finished": 600},
            {"name": "replay", "status": "incomplete", "started": 600, "finished": 1000},
        ],
    }
    claims = {
        folder: {
            "id": folder,
            "owner": folder,
            "state": "created",
            "resources": {"cpu": 4, "memory": 8, "disk": 10},
        }
        for folder in module.FOLDERS
    }
    sessions = {
        "setup-raw": {"cleanup_verified": True, "started": 210, "finished": 590},
        "replay": {"cleanup_verified": True, "started": 610, "finished": 990},
    }
    clean = {
        "owners": list(module.FOLDERS),
        "complete": True,
        "original_all_cleanup_passed": True,
        "fresh_original_ids_absent": True,
        "sandboxes": [],
    }
    return [pipeline, dict(module.SOURCES), claims, sessions, clean]


def test_prices_all_closed_time_plus_both_cleanup_margins():
    coarse, upper, records = module.audit(*evidence())
    assert coarse == Decimal("1.384500")
    assert upper == 2 * Decimal(980) * module.RATE / 3600
    assert all(Decimal(r["priced_seconds"]) == 980 for r in records.values())


@pytest.mark.parametrize(
    "defect",
    [
        "source",
        "later_stage",
        "wrong_failure",
        "false_rejection",
        "unfinished_setup",
        "quality_repair",
        "duration",
        "order",
        "resource",
        "duplicate_id",
        "duplicate_owner",
        "extra_claim",
        "owner",
        "uncertain_creation",
        "cleanup",
        "remaining",
        "fresh_absence",
        "session_cleanup",
        "session_clock",
        "large_lifetime",
    ],
)
def test_refuses_incomplete_or_different_resource_evidence(defect):
    p, sources, claims, sessions, clean = copy.deepcopy(evidence())
    if defect == "source":
        sources["run_autonomous.py"] = "f" * 64
    if defect == "later_stage":
        p["stages"].append({"name": "specification"})
    if defect == "wrong_failure":
        p["failed_stage"] = "grading"
    if defect == "false_rejection":
        p["status"] = "rejected"
    if defect == "unfinished_setup":
        p["stages"][1]["status"] = "incomplete"
    if defect == "quality_repair":
        p["quality_repair"] = {"used": True}
    if defect == "duration":
        p["finished"] = 10000
    if defect == "order":
        p["stages"][1]["started"] = 0
    if defect == "resource":
        claims["replay"]["resources"]["memory"] = 16
    if defect == "duplicate_id":
        claims["replay"]["id"] = "setup-raw"
    if defect == "duplicate_owner":
        claims["replay"]["owner"] = "setup-raw"
    if defect == "extra_claim":
        claims["native"] = claims["replay"]
    if defect == "owner":
        clean["owners"] = ["different", "replay"]
    if defect == "uncertain_creation":
        claims["replay"]["state"] = "creation_uncertain"
    if defect == "cleanup":
        clean["original_all_cleanup_passed"] = False
    if defect == "remaining":
        clean["sandboxes"] = ["remaining"]
    if defect == "fresh_absence":
        clean["fresh_original_ids_absent"] = False
    if defect == "session_cleanup":
        sessions["replay"]["cleanup_verified"] = False
    if defect == "session_clock":
        sessions["replay"]["started"] = 0
    if defect == "large_lifetime":
        p["finished"] = p["stages"][-1]["finished"] = 7200
        for s in sessions.values():
            s.update(started=101, finished=7199)
    with pytest.raises(AssertionError):
        module.audit(p, sources, claims, sessions, clean)
