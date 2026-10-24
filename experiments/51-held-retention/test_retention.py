"""Offline faults over real archived bytes, with isolated ledger/local policy.

The source fixture reuses the verified47 failure and never changes its files.
Local publication/isolated accounting are explicit test doubles, not claims of
new native execution or public archival. All transport is forbidden.
"""

import copy
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from biotasks.validation import controller, preservation
from biotasks.validation.archives import records
from biotasks.validation.files import ValidationError, inventory, read_json, sha, write_json

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import evidence  # noqa: E402
import log_policy  # noqa: E402
import retain  # noqa: E402

ORIGINAL = (
    ROOT.parents[2]
    / "47/experiments/47-bootstrap-recipe-state/inputs-private/comparison-001/validation"
)


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
        root = "jobs/" + control["name"] + "/" + trial + "/verifier/"
        packed[root + "test-stdout.txt"] = {"data": b"test_a PASSED\n\0\0test_b FAILED\n"}
    return task, controls, packed


@pytest.mark.parametrize("name", ["org__repo-12", "second__biology-302", "team__sub.domain-7"])
def test_inspection_paths_are_derived_for_different_tasks_without_hash_inputs(name):
    task, controls, packed = logs(name)
    rows = log_policy.derive(task, controls, packed)
    assert len(rows) == 2 and all(row["nul_bytes"] == 2 for row in rows)
    before = copy.deepcopy(packed)
    with log_policy.inspection(rows):
        for path, item in packed.items():
            preservation.inspect(item["data"], path)
    assert packed == before


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
def test_unknown_or_unsafe_views_are_rejected(kind):
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


def test_inspection_never_changes_raw_bytes_and_restores_context_on_error():
    task, controls, packed = logs("org__repo-12")
    rows = log_policy.derive(task, controls, packed)
    original = preservation.inspect
    with pytest.raises(RuntimeError), log_policy.inspection(rows):
        for path, item in packed.items():
            preservation.inspect(item["data"], path)
        raise RuntimeError("interrupted publication")
    assert preservation.inspect is original
    with log_policy.inspection(rows), pytest.raises(ValidationError):
        preservation.inspect(next(iter(packed.values()))["data"] + b"changed", rows[0]["path"])
    with pytest.raises(ValidationError):
        preservation.inspect(next(iter(packed.values()))["data"], rows[0]["path"])


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    real = controller.verify_plan
    original = real(ORIGINAL)
    plan = copy.deepcopy(original)
    ledger = tmp_path / "isolated-budget.json"
    write_json(ledger, read_json(Path(plan["budget_ledger"])))
    plan["budget_ledger"] = str(ledger)
    plan["archive"] = {"kind": "local"}
    monkeypatch.setattr(controller, "verify_plan", lambda root: copy.deepcopy(plan))

    def forbidden(*args, **kwargs):
        pytest.fail("Offline retention must not use network/subprocess/SDK transport")

    monkeypatch.setattr(controller.Pipeline, "client", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    before = inventory(ORIGINAL)
    output = tmp_path / "retention"
    retain.prepare(ORIGINAL, output)
    yield output, plan, ledger
    assert inventory(ORIGINAL) == before


def finish(output, **kwargs):
    for _ in range(25):
        state = retain.run(output, **kwargs)
        if state["state"] == "retention_complete" or state["state"].startswith("pending:"):
            return state
    pytest.fail("Retention did not terminate")


def test_full_sidecar_keeps_native_failure_and_original_files_unchanged(isolated):
    output, plan, ledger = isolated
    old = sha(ledger)
    state = finish(output)
    assert state["state"] == "retention_complete" and not state["scientific_acceptance"]
    result = state["results"][0]
    assert result["scientific_state"] == "held_unaccepted" and result["original_journal_unchanged"]
    assert result["owned_cleanup_verified_empty"] and not result["native_reward_accepted"]
    assert result["public_base"]["preserved"] and sha(ledger) == old


@pytest.mark.parametrize("boundary", retain.STAGES)
def test_all_sidecar_effect_boundaries_resume_without_repeating_original_jobs(
    isolated, monkeypatch, boundary
):
    output, _, _ = isolated
    real = retain.Retention.record
    failed = []

    def interrupted(actor, stage, paths):
        real(actor, stage, paths)
        if stage == boundary and not failed:
            failed.append(stage)
            raise InterruptedError(stage)

    monkeypatch.setattr(retain.Retention, "record", interrupted)
    with pytest.raises(InterruptedError):
        finish(output)
    assert finish(output)["state"] == "retention_complete"
    assert failed == [boundary]


def test_completed_replay_is_byte_inert_and_needs_no_publication_or_reconcile(
    isolated, monkeypatch
):
    output, _, ledger = isolated
    expected = finish(output)
    before, budget_sha = inventory(output), sha(ledger)
    monkeypatch.setattr(
        preservation, "publish", lambda *a, **k: pytest.fail("No repeated publication")
    )
    monkeypatch.setattr(
        retain.budget, "reconcile", lambda *a, **k: pytest.fail("No repeated accounting")
    )
    assert finish(output) == expected
    assert inventory(output) == before and sha(ledger) == budget_sha


def test_publication_acknowledgement_loss_reuses_verified_receipt(isolated, monkeypatch):
    output, _, _ = isolated
    original = preservation.publish
    calls = []

    def published(*args, **kwargs):
        value = original(*args, **kwargs)
        calls.append(args[0])
        if len(calls) == 1:
            raise InterruptedError("publication acknowledgement lost")
        return value

    monkeypatch.setattr(preservation, "publish", published)
    with pytest.raises(InterruptedError):
        finish(output)
    assert finish(output)["state"] == "retention_complete"
    assert len(calls) == 2


def test_changed_source_is_rejected_before_any_further_effect(isolated, monkeypatch):
    output, _, _ = isolated
    retain.run(output)
    original = evidence.verify

    def changed(*args):
        pipe, source = original(*args)
        source["source_identity"] = "changed"
        return pipe, source

    monkeypatch.setattr(evidence, "verify", changed)
    with pytest.raises(ValidationError, match="held source changed"):
        retain.run(output)


def test_wrong_cleanup_worker_does_not_complete_retention(isolated, monkeypatch):
    output, _, _ = isolated
    original = evidence.read_json
    path = ORIGINAL / "runs/task-4c1544d9d07c/cleanup/submission.json"

    def changed(file):
        value = original(file)
        return {**value, "worker_id": "foreign-worker"} if file == path else value

    monkeypatch.setattr(evidence, "read_json", changed)
    with pytest.raises(ValidationError, match="worker/submission changed"):
        finish(output)
    assert not (output / "cases/task-4c1544d9d07c/cleanup_terminal.json").exists()


def test_foreign_remaining_resources_are_not_cleanup_success(isolated, monkeypatch):
    output, _, _ = isolated
    original = evidence.auxiliary

    def changed(pipe, role, **settings):
        group, directory, account, report = original(pipe, role, **settings)
        if role == "cleanup":
            report["cleanup"]["remaining"]["containers"] = ["foreign-or-still-running"]
        return group, directory, account, report

    monkeypatch.setattr(evidence, "auxiliary", changed)
    with pytest.raises(ValidationError, match="not verified empty"):
        finish(output)


def test_budget_admission_closure_is_not_relaxed_by_retention(isolated):
    output, _, ledger = isolated
    value = read_json(ledger)
    value.update(admission_closed=True, model_admission_closed=True)
    write_json(ledger, value)
    before = sha(ledger)
    result = finish(output)["results"][0]
    assert result["admission_closed"] is True and sha(ledger) == before


def test_unsupported_hold_does_not_create_a_case_or_claim_completion(isolated, monkeypatch):
    output, _, _ = isolated
    original = retain.read_json

    def changed(file):
        value = original(file)
        return {**value, "reason": "Unknown failure"} if file.name == "held.json" else value

    monkeypatch.setattr(retain, "read_json", changed)
    result = retain.run(output)
    assert result["state"] == "held_unsupported" and not result["scientific_acceptance"]
    assert not (output / "cases").exists()


def test_public_transfer_not_admitted_keeps_verified_local_evidence(isolated, monkeypatch):
    output, _, _ = isolated
    monkeypatch.setattr(retain.Retention, "remote_publication", lambda self: True)
    result = finish(output)
    assert result["state"] == "pending:publication_resolved:public transfer not admitted"
    case = output / "cases/task-4c1544d9d07c"
    assert (case / "preserved/manifest.json").is_file()
    assert not (case / "publication.json").exists()
    assert not (case / "cleanup-intent.json").exists()


def test_uncached_cleanup_not_admitted_has_no_new_intent_or_transport(isolated, monkeypatch):
    output, _, _ = isolated
    original = Path.is_file
    account = ORIGINAL / "runs/task-4c1544d9d07c/cleanup/accounting.json"
    with monkeypatch.context() as context:
        context.setattr(Path, "is_file", lambda path: False if path == account else original(path))
        result = finish(output)
    assert result["state"] == "pending:cleanup_terminal:original cleanup operation not admitted"
    assert not (output / "cases/task-4c1544d9d07c/cleanup-intent.json").exists()


@pytest.mark.parametrize("change", ["truthy-present", "foreign-image", "false-preserved"])
def test_cleanup_public_base_protection_cannot_be_inferred_from_truthiness(isolated, change):
    output, plan, _ = isolated
    actor = retain.Retention(output, read_json(output / "plan.json"), plan["tasks"][0]["id"])
    # The original cleanup proof is held inside the source-bound runtime archive.
    _, _, _, report = evidence.auxiliary(actor.pipe, "cleanup", **actor.cleanup_settings())
    proof = report["cleanup"]
    base = proof["protected_public_base"]
    if change == "truthy-present":
        base["present_before"] = "true"
    elif change == "foreign-image":
        base["image_id_after"] = "sha256:foreign"
    else:
        base["preserved"] = False
    with pytest.raises(ValidationError):
        actor.verify_cleanup(proof)


@pytest.mark.parametrize("field", ["task-path", "cpu", "verifier-timeout", "agent", "reward-path"])
def test_both_control_provenance_checks_reject_drift_after_collector_early_error(field):
    plan = controller.verify_plan(ORIGINAL)
    group = plan["tasks"][0]
    directory = ORIGINAL / "runs" / group["id"]
    _, outer = retain.collection.envelope(
        directory / "runtime.tar.zst",
        read_json(directory / "submission.json"),
        group["payload_sha256"],
        "execute",
        group["run_id"],
    )
    items = json.loads(outer["controls/controls.json"]["data"])
    packed = records(outer["control-artifacts.tar.gz"]["data"], "tar.gz")
    item = items[1]
    trial = item["trial_results"][0]
    if field == "task-path":
        trial["result"]["config"]["task"]["path"] = "/other/task"
    elif field == "cpu":
        trial["result"]["config"]["environment"]["override_cpus"] = 2
    elif field == "agent":
        trial["result"]["config"]["agent"]["model_name"] = "unexpected-model"
    elif field == "verifier-timeout":
        item["verifier_timeout_seconds"] += 1
    else:
        name, data = next(iter(item["reward_files"].items()))
        item["reward_files"] = {name.replace(trial["result"]["trial_name"], "foreign_trial"): data}
    packed["jobs/" + trial["path"]]["data"] = json.dumps(trial["result"]).encode()
    with pytest.raises((ValidationError, KeyError)):
        evidence.controls(
            group["task"],
            group["run_id"],
            read_json(ORIGINAL / group["payload_directory"] / "family.json"),
            items,
            packed,
        )
