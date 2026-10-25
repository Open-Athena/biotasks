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


def grading_evidence(profile="grading"):
    p, _, _, _, clean = evidence()
    folders, names, sources = module.profile_config(profile)
    p.update(
        failed_stage="grading",
        stages=[
            {
                "name": name,
                "status": "incomplete" if name == "grading" else "completed",
                "started": 100 + i * 100,
                "finished": 199 + i * 100,
            }
            for i, name in enumerate(names)
        ],
        quality_repair={
            "kind": "specification_review",
            "target": "task_specification",
            "allowance_consumed": True,
            "validation_status": "ready",
        },
    )
    claims = {
        f: {
            "id": f,
            "owner": f,
            "state": "created",
            "resources": {"cpu": 4, "memory": 8, "disk": 10},
        }
        for f in folders
    }
    sessions = {
        f: {
            "started": p["stages"][i]["started"] + 10,
            "finished": p["stages"][i]["finished"] - 10,
            "cleanup_verified": True,
        }
        for f, i in zip(folders, [1, 2, 4, 5], strict=True)
    }
    clean["owners"] = list(folders)
    return p, dict(sources), claims, sessions, clean


@pytest.mark.parametrize("profile", ["grading", "workspace_grading"])
def test_explicit_early_review_profile_prices_four_complete_sessions(profile):
    coarse, upper, records = module.audit(*grading_evidence(profile), profile=profile)
    assert coarse == Decimal("2.769000")
    assert len(records) == 4 and upper < 1


@pytest.mark.parametrize(
    "defect",
    [
        "source",
        "crosswired_profile",
        "native",
        "wrong_repair",
        "unvalidated_repair",
        "unconsumed_repair",
        "later_session",
        "outside_stage",
    ],
)
@pytest.mark.parametrize("profile", ["grading", "workspace_grading"])
def test_grading_profile_does_not_admit_other_repairs_or_topologies(defect, profile):
    p, sources, claims, sessions, clean = copy.deepcopy(grading_evidence(profile))
    if defect == "source":
        sources["run_reference_setup.py"] = module.SOURCES["run_reference_setup.py"]
    if defect == "crosswired_profile":
        with pytest.raises(AssertionError):
            module.audit(p, sources, claims, sessions, clean)
        return
    if defect == "native":
        p["stages"].append({"name": "native"})
    if defect == "wrong_repair":
        p["quality_repair"]["kind"] = "comparison_diagnosis"
    if defect == "unvalidated_repair":
        p["quality_repair"]["validation_status"] = "revise"
    if defect == "unconsumed_repair":
        p["quality_repair"]["allowance_consumed"] = False
    if defect == "later_session":
        claims["native"] = claims["grading"]
    if defect == "outside_stage":
        sessions["grading"]["started"] = 150
    with pytest.raises(AssertionError):
        module.audit(p, sources, claims, sessions, clean, profile=profile)


@pytest.mark.parametrize("profile", ["grading", "workspace_grading"])
def test_different_complete_source_families_cannot_be_crosswired(profile):
    p, sources, claims, sessions, clean = grading_evidence(profile)
    other = "workspace_grading" if profile == "grading" else "grading"
    with pytest.raises(AssertionError):
        module.audit(p, sources, claims, sessions, clean, profile=other)


def current_grading_evidence():
    p, sources, claims, sessions, clean = grading_evidence("current_grading_rejection")
    p.update(status="rejected")
    p.pop("failed_stage")
    p["stages"][-1]["status"] = "rejected"
    return p, sources, claims, sessions, clean


def current_native_evidence():
    p, sources, claims, sessions, clean = grading_evidence("current_native_preparation_failure")
    p["failed_stage"] = "native"
    p["stages"][-2]["status"] = "completed"
    p["stages"][-1]["status"] = "incomplete"
    return p, sources, claims, sessions, clean


def test_native_preparation_clock_profile_prices_four_sessions_only():
    # Financial main additionally requires the independent exact-source
    # no-dispatch proof; a native failure does not establish that by itself.
    coarse, upper, records = module.audit(
        *current_native_evidence(), profile="current_native_preparation_failure"
    )
    assert coarse == Decimal("2.769000") and upper < 1
    assert len(records) == 4


@pytest.mark.parametrize("defect", ["source", "grading", "extra_session", "native_completed"])
def test_native_preparation_clock_profile_refuses_other_sources_or_incomplete_prefix(defect):
    p, sources, claims, sessions, clean = current_native_evidence()
    if defect == "source":
        sources.pop("upload_transfer.py")
    elif defect == "grading":
        p["stages"][-2]["status"] = "incomplete"
    elif defect == "extra_session":
        claims["native"] = claims["grading"]
    else:
        p["stages"][-1]["status"] = "completed"
    with pytest.raises(AssertionError):
        module.audit(
            p, sources, claims, sessions, clean, profile="current_native_preparation_failure"
        )


@pytest.mark.parametrize("repair", [True, False])
def test_current_grading_rejection_prices_all_four_closed_sessions(repair):
    args = current_grading_evidence()
    if not repair:
        args[0].pop("quality_repair")
    coarse, upper, records = module.audit(*args, profile="current_grading_rejection")
    assert coarse == Decimal("2.769000") and upper < 1
    assert len(records) == 4


@pytest.mark.parametrize(
    "defect",
    [
        "source",
        "missing_transfer",
        "infrastructure_failure",
        "failed_stage",
        "native",
        "extra_session",
        "unfinished_grading",
        "wrong_repair",
        "unvalidated_repair",
        "outside_stage",
        "missing_cleanup",
        "profile",
    ],
)
def test_current_grading_rejection_refuses_other_sources_topologies_and_outcomes(defect):
    p, sources, claims, sessions, clean = copy.deepcopy(current_grading_evidence())
    if defect == "source":
        sources["run_reference_setup.py"] = module.WORKSPACE_GRADING_SOURCES[
            "run_reference_setup.py"
        ]
    elif defect == "missing_transfer":
        sources.pop("upload_transfer.py")
    elif defect == "infrastructure_failure":
        p["status"] = "infrastructure_failed"
    elif defect == "failed_stage":
        p["failed_stage"] = "grading"
    elif defect == "native":
        p["stages"].append({"name": "native"})
    elif defect == "extra_session":
        claims["native"] = claims["grading"]
    elif defect == "unfinished_grading":
        p["stages"][-1]["status"] = "incomplete"
    elif defect == "wrong_repair":
        p["quality_repair"]["kind"] = "comparison_diagnosis"
    elif defect == "unvalidated_repair":
        p["quality_repair"]["validation_status"] = "revise"
    elif defect == "outside_stage":
        sessions["grading"]["started"] = 150
    elif defect == "missing_cleanup":
        clean["original_all_cleanup_passed"] = False
    else:
        with pytest.raises(AssertionError):
            module.audit(p, sources, claims, sessions, clean, profile="workspace_grading")
        return
    with pytest.raises(AssertionError):
        module.audit(p, sources, claims, sessions, clean, profile="current_grading_rejection")


@pytest.mark.parametrize("profile", ["legacy_setup_replay", "legacy_specification_rejection"])
def test_known_legacy_resource_families_keep_distinct_outcome_shapes(profile):
    p, _, claims, sessions, clean = evidence()
    _, _, sources = module.profile_config(profile)
    if profile == "legacy_specification_rejection":
        p.update(status="rejected", finished=1200)
        p.pop("failed_stage")
        p["stages"][-1]["status"] = "completed"
        p["stages"].append(
            {"name": "specification", "status": "rejected", "started": 1000, "finished": 1100}
        )
    assert module.audit(p, sources, claims, sessions, clean, profile=profile)[0] == Decimal(
        "1.384500"
    )
    with pytest.raises(AssertionError):
        module.audit(p, module.SOURCES, claims, sessions, clean, profile=profile)
    p["status"] = "infrastructure_failed" if p["status"] == "rejected" else "rejected"
    with pytest.raises(AssertionError):
        module.audit(p, sources, claims, sessions, clean, profile=profile)


def current_specification_evidence():
    p, _, claims, sessions, clean = evidence()
    p.update(status="rejected", finished=1200)
    p.pop("failed_stage")
    p["stages"][-1]["status"] = "completed"
    p["stages"].append(
        {"name": "specification", "status": "rejected", "started": 1000, "finished": 1100}
    )
    p["quality_repair"] = {
        "kind": "specification_review",
        "target": "task_specification",
        "allowance_consumed": True,
        "validation_status": "revise",
        "original_specification": "work/specification",
        "original_review": "work/specification-review",
        "effective_specification": "work/specification-revision",
        "effective_review": "work/specification-review-revised",
    }
    return p, dict(module.CURRENT_SPECIFICATION_SOURCES), claims, sessions, clean


@pytest.mark.parametrize("repair", [True, False])
def test_current_specification_rejection_prices_only_two_original_sessions(repair):
    args = current_specification_evidence()
    if not repair:
        args[0].pop("quality_repair")
    coarse, upper, records = module.audit(*args, profile="current_specification_rejection")
    assert coarse == Decimal("1.384500") and upper < 1
    assert len(records) == 2


@pytest.mark.parametrize(
    "defect",
    ["source", "missing_transfer", "ready", "wrong_review", "extra_session", "native", "profile"],
)
def test_current_specification_profile_rejects_changed_sources_and_other_outcomes(defect):
    p, sources, claims, sessions, clean = copy.deepcopy(current_specification_evidence())
    if defect == "source":
        sources["run_reference_setup.py"] = module.SOURCES["run_reference_setup.py"]
    elif defect == "missing_transfer":
        sources.pop("upload_transfer.py")
    elif defect == "ready":
        p["quality_repair"]["validation_status"] = "ready"
    elif defect == "wrong_review":
        p["quality_repair"]["effective_review"] = "unrelated/specification-review-revised"
    elif defect == "extra_session":
        claims["grading"] = claims["setup-raw"]
    elif defect == "native":
        p["stages"].append({"name": "native"})
    else:
        with pytest.raises(AssertionError):
            module.audit(
                p, sources, claims, sessions, clean, profile="legacy_specification_rejection"
            )
        return
    with pytest.raises(AssertionError):
        module.audit(p, sources, claims, sessions, clean, profile="current_specification_rejection")


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
