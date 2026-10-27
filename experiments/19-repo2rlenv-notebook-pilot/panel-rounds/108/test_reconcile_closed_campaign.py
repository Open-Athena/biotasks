import importlib.util
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "closed_campaign_fixture", Path(__file__).with_name("reconcile_closed_campaign.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("version", [72, 102, 105, 108])
def test_exact_recorded_creator_family_is_required(version):
    runtime = json.loads(
        (module.EXPERIMENT / f"panel-rounds/{version:03}/runtime-identity.json").read_text()
    )["runtime_files"]
    module.admit_resource_family(runtime, version, 0)
    wrong = {**runtime, module.PREFIX + "run_reference_setup.py": "unknown"}
    with pytest.raises(AssertionError):
        module.admit_resource_family(wrong, version, 0)


def test_legacy_native_or_unknown_families_keep_their_full_holds():
    runtime = json.loads(
        (module.EXPERIMENT / "panel-rounds/072/runtime-identity.json").read_text()
    )["runtime_files"]
    with pytest.raises(AssertionError):
        module.admit_resource_family(runtime, 72, 1)
    with pytest.raises(AssertionError):
        module.admit_resource_family(runtime, 999, 0)


def evidence(native=False):
    names = ["preparation", "setup", "replay", "specification", "construction", "grading"]
    bounds = [(0, 10), (10, 210), (210, 410), (410, 610), (610, 810), (810, 1410)]
    if native:
        names.append("native")
        bounds.append((1410, 1610))
    stages = [
        {"name": name, "status": "completed", "started": left, "finished": right}
        for name, (left, right) in zip(names, bounds, strict=True)
    ]
    stages[-1]["status"] = "incomplete"
    pipeline = {
        "autonomous": True,
        "operator_interventions": 0,
        "status": "infrastructure_failed",
        "failed_stage": names[-1],
        "daytona_reserved_usd": 5 if native else 4,
        "started": 0,
        "finished": bounds[-1][1],
        "stages": stages,
        "quality_repair": {
            "kind": "specification_review" if native else "comparison_diagnosis",
            "allowance_consumed": True,
            "target": "public_question",
        },
    }
    sessions = {
        name: {"started": start, "finished": start + 100, "cleanup_verified": True}
        for name, start in [
            ("setup-raw", 20),
            ("replay", 220),
            ("materialization-raw", 620),
            ("grading", 820),
        ]
    }
    if not native:
        sessions["grading-comparison-repair"] = {
            "started": 1020,
            "finished": 1120,
            "cleanup_verified": True,
        }
    return pipeline, sessions


@pytest.mark.parametrize("native,retained", [(False, "0.50"), (True, "1.50")])
def test_every_sdk_gets_both_margins_and_native_hold_is_not_refunded(native, retained):
    pipeline, sessions = evidence(native)
    before = deepcopy((pipeline, sessions))
    clocks, upper, native_hold, keep = module.price(pipeline, sessions)
    assert all(row["priced_seconds"] == "700" for row in clocks.values())
    assert native_hold == (1 if native else 0)
    assert keep == Decimal(retained) and upper + native_hold + Decimal("0.10") <= keep
    assert (pipeline, sessions) == before


def test_overlapping_sdk_lifetimes_receive_no_serialization_or_idle_discount():
    pipeline, sessions = evidence()
    sessions["grading-comparison-repair"].update(started=820, finished=1120)
    clocks, upper, _, _ = module.price(pipeline, sessions)
    assert clocks["grading"]["priced_seconds"] == "700"
    assert clocks["grading-comparison-repair"]["priced_seconds"] == "900"
    assert upper == sum(Decimal(row["resource_upper_bound_usd"]) for row in clocks.values())


def test_public_question_diagnosis_keeps_the_same_five_complete_sdk_lifetimes():
    pipeline, sessions = evidence()
    expected = module.price(pipeline, sessions)
    pipeline["quality_repair"]["kind"] = "public_question_diagnosis"
    before = deepcopy((pipeline, sessions))
    assert module.price(pipeline, sessions) == expected
    assert set(expected[0]) == set(sessions) and len(sessions) == 5
    assert (pipeline, sessions) == before


@pytest.mark.parametrize("native", [False, True])
def test_public_question_diagnosis_cannot_admit_an_incompatible_target_or_native_prefix(native):
    pipeline, sessions = evidence(native)
    pipeline["quality_repair"]["kind"] = "public_question_diagnosis"
    if not native:
        pipeline["quality_repair"]["target"] = "independent_solution"
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)


@pytest.mark.parametrize(
    "defect",
    [
        "running",
        "unknown_stage",
        "wrong_failure",
        "wrong_reservation",
        "manual_edit",
        "unapproved_duration",
        "stage_overlap",
        "unknown_repair",
        "extra_repair",
        "failed_stage_completed",
    ],
)
def test_unknown_or_nonterminal_profiles_cannot_release_holds(defect):
    pipeline, sessions = evidence()
    if defect == "running":
        pipeline["status"] = "running"
    elif defect == "unknown_stage":
        pipeline["stages"].append(dict(pipeline["stages"][-1]))
    elif defect == "wrong_failure":
        pipeline["failed_stage"] = "setup"
    elif defect == "wrong_reservation":
        pipeline["daytona_reserved_usd"] = 3
    elif defect == "manual_edit":
        pipeline["operator_interventions"] = 1
    elif defect == "unapproved_duration":
        pipeline["finished"] = 7201
    elif defect == "stage_overlap":
        pipeline["stages"][1]["started"] = 0
    elif defect == "unknown_repair":
        pipeline["quality_repair"]["kind"] = "unknown"
    elif defect == "extra_repair":
        pipeline["quality_repair"]["allowance_consumed"] = False
    else:
        pipeline["stages"][-1]["status"] = "completed"
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)


@pytest.mark.parametrize("defect", ["missing", "extra", "unclosed", "before_stage", "after_stage"])
def test_incomplete_or_misbound_session_clocks_cannot_release_holds(defect):
    pipeline, sessions = evidence()
    if defect == "missing":
        del sessions["grading"]
    elif defect == "extra":
        sessions["unknown"] = dict(sessions["grading"])
    elif defect == "unclosed":
        sessions["grading"]["cleanup_verified"] = False
    elif defect == "before_stage":
        sessions["grading"]["started"] = 800
    else:
        sessions["grading"]["finished"] = 1500
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)


def rejected_evidence(stage, repair):
    pipeline, sessions = evidence()
    pipeline.update(status="rejected", rejection={"stage": stage})
    del pipeline["failed_stage"]
    del sessions["grading-comparison-repair"]
    if stage == "specification":
        pipeline["stages"] = pipeline["stages"][:4]
        sessions = {name: row for name, row in sessions.items() if name in {"setup-raw", "replay"}}
    pipeline["stages"][-1]["status"] = "rejected"
    pipeline["finished"] = pipeline["stages"][-1]["finished"]
    pipeline["daytona_reserved_usd"] = len(sessions)
    pipeline["quality_repair"] = (
        {"kind": "specification_review", "target": "task_specification", "allowance_consumed": True}
        if repair
        else None
    )
    return pipeline, sessions


@pytest.mark.parametrize("stage,retained", [("specification", "0.25"), ("grading", "0.50")])
@pytest.mark.parametrize("repair", [False, True])
def test_rejected_sdk_prefixes_keep_every_lifetime_and_both_margins(stage, retained, repair):
    pipeline, sessions = rejected_evidence(stage, repair)
    before = deepcopy((pipeline, sessions))
    clocks, upper, native, keep = module.price(pipeline, sessions)
    assert native == 0 and keep == Decimal(retained)
    assert all(row["priced_seconds"] == "700" for row in clocks.values())
    assert keep >= upper + Decimal("0.10")
    assert (pipeline, sessions) == before


@pytest.mark.parametrize(
    "defect",
    [
        "last_completed",
        "prior_rejected",
        "failure_field",
        "wrong_stage",
        "reservation",
        "repair_target",
        "extra_sdk",
        "native",
    ],
)
def test_rejection_profiles_refuse_unproved_dispatch_or_repair_shapes(defect):
    pipeline, sessions = rejected_evidence("specification", True)
    if defect == "last_completed":
        pipeline["stages"][-1]["status"] = "completed"
    elif defect == "prior_rejected":
        pipeline["stages"][0]["status"] = "rejected"
    elif defect == "failure_field":
        pipeline["failed_stage"] = "specification"
    elif defect == "wrong_stage":
        pipeline["rejection"]["stage"] = "setup"
    elif defect == "reservation":
        pipeline["daytona_reserved_usd"] = 1
    elif defect == "repair_target":
        pipeline["quality_repair"]["target"] = "independent_solution"
    elif defect == "extra_sdk":
        sessions["unknown"] = dict(sessions["replay"])
    else:
        pipeline["stages"].append(
            {"name": "native", "status": "rejected", "started": 610, "finished": 620}
        )
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)


def setup_rejection():
    pipeline, sessions = rejected_evidence("specification", False)
    pipeline["stages"] = pipeline["stages"][:2]
    pipeline["stages"][-1]["status"] = "rejected"
    pipeline["finished"] = pipeline["stages"][-1]["finished"]
    pipeline["rejection"]["stage"] = "setup"
    pipeline["daytona_reserved_usd"] = 1
    return pipeline, {"setup-raw": sessions["setup-raw"]}


def test_closed_setup_rejection_keeps_its_entire_lifetime_and_both_margins():
    pipeline, sessions = setup_rejection()
    before = deepcopy((pipeline, sessions))
    clocks, upper, native, retained = module.price(pipeline, sessions)
    assert set(clocks) == {"setup-raw"}
    assert clocks["setup-raw"]["priced_seconds"] == "700"
    assert native == 0 and retained == Decimal("0.25")
    assert retained >= upper + Decimal("0.10")
    assert (pipeline, sessions) == before


@pytest.mark.parametrize(
    "defect", ["repair", "extra_dispatch", "unclosed", "outside_stage", "incomplete"]
)
def test_setup_rejection_cannot_release_unknown_or_unclosed_exposure(defect):
    pipeline, sessions = setup_rejection()
    if defect == "repair":
        pipeline["quality_repair"] = {
            "kind": "specification_review",
            "target": "task_specification",
            "allowance_consumed": True,
        }
    elif defect == "extra_dispatch":
        sessions["replay"] = dict(sessions["setup-raw"])
    elif defect == "unclosed":
        sessions["setup-raw"]["cleanup_verified"] = False
    elif defect == "outside_stage":
        sessions["setup-raw"]["finished"] = pipeline["finished"] + 1
    else:
        pipeline["stages"][-1]["status"] = "incomplete"
    with pytest.raises(AssertionError):
        module.price(pipeline, sessions)


@pytest.mark.parametrize("defect", ["native", "unbound_module"])
def test_older102_prefix_requires_whole_recorded_runtime_and_no_native_hold(defect):
    runtime = json.loads(
        (module.EXPERIMENT / "panel-rounds/102/runtime-identity.json").read_text()
    )["runtime_files"]
    if defect == "unbound_module":
        runtime = {**runtime, module.PREFIX + "daytona_session.py": "unknown"}
    with pytest.raises(AssertionError):
        module.admit_resource_family(runtime, 102, 1 if defect == "native" else 0)
