"""Portable policy and lifecycle regression; no native/model/network execution."""

import copy
import socket
import subprocess
from types import SimpleNamespace

import pytest

from biotasks.generation import native, outcomes
from biotasks.retention import actor, log_policy
from biotasks.validation import controller, preservation
from biotasks.validation.files import ValidationError, inventory, sha, write_json


@pytest.fixture(autouse=True)
def no_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Retention policy tests must not use external transport")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def logs(task_name):
    task = {"task": task_name}
    controls, packed = [], {}
    for agent in ("nop", "oracle"):
        trial = task_name + "__trial_" + agent
        control = {
            "task": task_name,
            "agent": agent,
            "name": task_name + "-" + agent,
            "trial_results": [
                {
                    "path": task_name + "-" + agent + "/" + trial + "/result.json",
                    "result": {"trial_name": trial},
                }
            ],
        }
        controls.append(control)
        packed["jobs/" + control["name"] + "/" + trial + "/verifier/test-stdout.txt"] = {
            "data": b"test_a PASSED\n\0\0test_b FAILED\n"
        }
    return task, controls, packed


@pytest.mark.parametrize("task_name", ["org__repo-12", "team__sub.domain-302"])
def test_log_views_are_source_derived_without_changing_archived_bytes(task_name):
    task, controls, packed = logs(task_name)
    before = copy.deepcopy(packed)
    rows = log_policy.derive(task, controls, packed)
    assert len(rows) == 2 and all(row["nul_bytes"] == 2 for row in rows)
    original = preservation.inspect
    with pytest.raises(InterruptedError), log_policy.inspection(rows):
        for path, item in packed.items():
            preservation.inspect(item["data"], path)
        raise InterruptedError("Inspection interrupted")
    assert preservation.inspect is original and packed == before
    with pytest.raises(ValidationError):
        preservation.inspect(next(iter(packed.values()))["data"], rows[0]["path"])


@pytest.mark.parametrize(
    "kind",
    [
        "foreign-trial",
        "foreign-agent",
        "task-binary",
        "credential",
        "invalid-utf8",
        "binary-control",
        "split-utf8",
        "oversize",
    ],
)
def test_unsafe_or_unbound_log_data_are_never_publication_views(kind):
    task, controls, packed = logs("org__repo-12")
    path = next(iter(packed))
    if kind == "foreign-trial":
        packed[path.replace("__trial_nop/", "__other/")] = packed.pop(path)
    elif kind == "foreign-agent":
        packed[path.replace("-nop/", "-solver/")] = packed.pop(path)
    elif kind == "task-binary":
        packed["outputs/task/tests/verifier.py"] = {"data": b"data\0data"}
    elif kind == "credential":
        fake = b"gh" + b"p_" + b"a" * 32
        packed[path]["data"] = fake[:9] + b"\0" + fake[9:]
    elif kind == "invalid-utf8":
        packed[path]["data"] = b"\xff\0text"
    elif kind == "split-utf8":
        packed[path]["data"] = b"\xc3\0\xa9"
    elif kind == "binary-control":
        packed[path]["data"] = b"text\x03\0text"
    else:
        packed[path]["data"] = b"\0" + b"x" * (2 * 1024**2)
    with pytest.raises(ValidationError):
        log_policy.derive(task, controls, packed)


def test_changed_bound_log_bytes_cannot_reuse_an_inspection_view():
    task, controls, packed = logs("org__repo-12")
    rows = log_policy.derive(task, controls, packed)
    with log_policy.inspection(rows), pytest.raises(ValidationError):
        preservation.inspect(next(iter(packed.values()))["data"] + b"changed", rows[0]["path"])


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    validation = tmp_path / "validation"
    validation.mkdir()
    groups = [{"id": name} for name in ("first", "second")]
    plan = {"tasks": groups, "unsupported": []}
    monkeypatch.setattr(native.controller, "verify_plan", lambda path: plan)
    calls = []

    class Pipeline:
        def __init__(self, root, source, group):
            self.group = group

        def step(self):
            calls.append(self.group["id"])
            return "complete"

    monkeypatch.setattr(native.controller, "Pipeline", Pipeline)
    held = validation / "runs/first/held.json"
    write_json(held, {"reason": "Native reward disagreement", "stop_verified": True})
    return validation, held, plan, calls


def test_retained_scientific_failure_does_not_skip_unstarted_native_groups(lifecycle, monkeypatch):
    validation, held, _, calls = lifecycle
    before = held.read_bytes()
    monkeypatch.setattr(
        native,
        "retained",
        lambda *args: {
            "state": "retention_complete",
            "admission_closed": False,
            "scientific_acceptance": False,
        },
    )
    result = native.advance(validation)
    assert result["state"] == "complete"
    assert result["tasks"]["first"]["scientific_acceptance"] is False
    assert calls == ["second"] and held.read_bytes() == before


@pytest.mark.parametrize("state", ["retaining", "held_unsupported"])
def test_incomplete_or_unknown_retention_blocks_later_native_admission(
    lifecycle, monkeypatch, state
):
    validation, _, _, calls = lifecycle
    monkeypatch.setattr(native, "retained", lambda *args: {"state": state})
    assert native.advance(validation)["state"] == state
    assert not calls


def test_completed_retention_does_not_clear_closed_admission(lifecycle, monkeypatch):
    validation, _, _, calls = lifecycle
    monkeypatch.setattr(
        native, "retained", lambda *args: {"state": "retention_complete", "admission_closed": True}
    )
    assert native.advance(validation)["state"] == "held"
    assert not calls


def test_native_budget_hold_is_preserved_after_regular_cleanup(lifecycle):
    validation, held, _, calls = lifecycle
    held.unlink()
    write_json(held.parent / "cleanup/budget-hold.json", {"reason": "CPU limit"})
    assert native.advance(validation)["state"] == "held"
    assert calls == ["first"]


def test_unsupported_hold_is_not_retention_completion_or_a_new_case(tmp_path, monkeypatch):
    original = tmp_path / "validation"
    original.mkdir()
    plan = {"tasks": [{"id": "unknown"}]}
    write_json(original / "runs/unknown/held.json", {"reason": "Unknown native error"})
    output = tmp_path / "retention"
    output.mkdir()
    monkeypatch.setattr(actor, "verify", lambda path: ({"original_root": str(original)}, plan))
    before = inventory(original)
    result = actor.run(output)
    assert result["state"] == "held_unsupported" and not result["scientific_acceptance"]
    assert inventory(original) == before and not (output / "cases").exists()


@pytest.mark.parametrize(
    "change", ["truthy-present", "foreign-image", "false-preserved", "remaining"]
)
def test_cleanup_must_preserve_source_bound_public_base_and_verify_empty(change):
    expected = {"ref": "python:3.12-slim", "image_id": "sha256:base"}
    proof = {
        "run_id": "fixed",
        "verified_empty": True,
        "remaining": dict.fromkeys(("containers", "controllers", "images", "volumes"), []),
        "protected_public_base": {
            "ref": expected["ref"],
            "present_before": True,
            "preserved": True,
            "image_id_after": expected["image_id"],
        },
    }
    instance = actor.Retention.__new__(actor.Retention)
    instance.pipe = SimpleNamespace(group={"run_id": "fixed"})
    instance.source = {"protected_base": expected}
    if change == "truthy-present":
        proof["protected_public_base"]["present_before"] = "true"
    elif change == "foreign-image":
        proof["protected_public_base"]["image_id_after"] = "sha256:foreign"
    elif change == "false-preserved":
        proof["protected_public_base"]["preserved"] = False
    else:
        proof["remaining"]["containers"] = ["still-running"]
    with pytest.raises(ValidationError):
        instance.verify_cleanup(proof)


def test_retained_late_files_never_become_native_accepted_outcomes(tmp_path, monkeypatch):
    validation = tmp_path / "validation"
    validation.mkdir()
    task = {"task": "org__repo-12", "repo": "org/repo", "source_identity": "source"}
    group = {"id": "first", "run_id": "fixed", "task": task}
    write_json(validation / "runs/first/held.json", {"reason": "Native reward disagreement"})
    monkeypatch.setattr(
        outcomes,
        "verify_plan",
        lambda path: {"plan_identity": "plan", "tasks": [group], "unsupported": []},
    )
    monkeypatch.setattr(
        actor,
        "run",
        lambda path: {
            "state": "retention_complete",
            "results": [
                {"task_id": "first", "state": "retention_complete", "native_reward_accepted": False}
            ],
        },
    )
    value = outcomes.summarize(validation)
    assert value["eligible_bundle_instances"] == 0 and not value["dataset_release_authorized"]
    row = value["tasks"][0]
    assert row["scientific_state"] == "held_unaccepted"
    assert all(row[key] is False for key in outcomes.FLAGS)
    assert outcomes.summarize(validation) == value


@pytest.mark.parametrize("lost_observation", [False, True])
def test_uncertain_cleanup_uses_existing_handle_without_resubmission_or_releasing_reservation(
    tmp_path, monkeypatch, lost_observation
):
    # Isolate the transport boundary after verified-publication admission. The
    # original fixed-handle controller's ensure_submission method is real; only
    # already-tested provenance/publication setup is replaced for this fault.
    ledger = tmp_path / "budget.json"
    write_json(ledger, {"cleanup_reservation": "still reserved"})
    group = {"id": "first", "run_id": "fixed", "payload_sha256": {"worker.py": "a" * 64}}
    pipe = controller.Pipeline(
        tmp_path / "original", {"backend": {}, "budget_ledger": str(ledger)}, group
    )
    cleanup = pipe.directory / "cleanup"
    auxiliary = {**group, "run_id": "fixed-cleanup"}
    write_json(
        cleanup / "submission.json",
        {
            "state": "submission_pending",
            "job_id": "/exedev/fixed-cleanup",
            "payload_sha256": group["payload_sha256"],
        },
    )
    write_json(pipe.directory / "journal.json", {"state": "held"})
    instance = actor.Retention.__new__(actor.Retention)
    instance.pipe = pipe
    instance.directory = tmp_path / "retention"
    write_json(
        instance.directory / "preserved/manifest.json",
        {"test": "publication verified before boundary"},
    )
    write_json(instance.directory / "publication.json", {"test": "verified receipt boundary"})
    instance.source = {
        "source_identity": "source",
        "original_files_sha256": {"journal.json": sha(pipe.directory / "journal.json")},
        "control_archive_sha256": "b" * 64,
        "protected_base": {"ref": "python:3.12-slim"},
    }
    instance.cleanup_allowed = True
    monkeypatch.setattr(preservation, "verify_receipt", lambda directory: None)
    monkeypatch.setattr(pipe, "auxiliary", lambda role, **settings: (auxiliary, cleanup, {}))
    monkeypatch.setattr(actor.evidence, "auxiliary_contract", lambda *a, **k: (auxiliary, cleanup))
    calls = []

    def transport(action, *args, **kwargs):
        calls.append(action)
        assert action == "observe", "Existing cleanup intent must never cause another submit"
        if lost_observation and len(calls) == 1:
            raise TimeoutError("Observation acknowledgement lost")
        return {"state": "handle_missing"}

    monkeypatch.setattr(pipe, "client", transport)
    before, reserved = inventory(pipe.root), sha(ledger)
    if lost_observation:
        with pytest.raises(TimeoutError):
            instance.cleanup_terminal()
    else:
        instance.cleanup_terminal()
    instance.cleanup_terminal()
    assert calls == ["observe", "observe"]
    assert inventory(pipe.root) == before and sha(ledger) == reserved
    assert not (instance.directory / "cleanup_terminal.json").exists()
