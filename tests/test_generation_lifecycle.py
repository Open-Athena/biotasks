"""Synthetic transport artifacts test lifecycle; no generation/control is run."""

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest
import zstandard

from biotasks.generation import generation_bridge
from biotasks.generation import generation_pipeline as generation_module
from biotasks.generation.generation_publication import text_observations
from biotasks.validation import bridge, budget, collection, preservation
from biotasks.validation.files import ValidationError, read_json, sha, write_json

GenerationPipeline, billing = generation_module.GenerationPipeline, generation_module.billing


def compressed(files, zstd=False):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    return (
        zstandard.ZstdCompressor().compress(buffer.getvalue())
        if zstd
        else gzip.compress(buffer.getvalue(), mtime=0)
    )


def usage(unknown=False):
    cost = None if unknown else "0.125"
    events = [
        {"event": "model_request", "call": 1},
        {"event": "model_charge", "call": 1, "actual_cost_usd": cost},
    ]
    return {
        "native-observations/billing.json": json.dumps(
            {
                "model_calls": 1,
                "actual_cost_usd": "0" if unknown else "0.125",
                "cost_complete": not unknown,
            }
        ).encode(),
        "native-observations/events.jsonl": b"\n".join(json.dumps(row).encode() for row in events),
    }


def test_billing_distinguishes_unknown_requests_from_zero_calls():
    phase = {name: {"data": raw} for name, raw in usage().items()}
    assert billing(phase, {"generation_started": True})["known_actual_usd"] == "0.125"
    unknown = {name: {"data": raw} for name, raw in usage(True).items()}
    assert billing(unknown, {"generation_started": True}) == {
        "known_actual_usd": "0",
        "calls": 1,
        "complete": False,
        "reason": "Original upstream observed request/charge events",
    }
    assert billing({}, {"generation_started": True})["calls"] is None
    assert billing({}, {"generation_started": False})["complete"]


def test_json_gzip_is_preserved_only_after_bounded_text_review():
    original = preservation.inspect
    raw = gzip.compress(json.dumps({"usage": "synthetic"}).encode())
    with text_observations():
        preservation.inspect(raw, "request.json.gz")
        bad = gzip.compress(json.dumps({"key": "sk-or-v1-" + "a" * 64}).encode())
        with pytest.raises(ValidationError, match="Credential"):
            preservation.inspect(bad, "request.json.gz")
        with pytest.raises(ValidationError, match="exceeds"):
            preservation.inspect(gzip.compress(b" " * (8 * 1024**2 + 1)), "request.json.gz")
    assert preservation.inspect is original


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    payload = tmp_path / "payload"
    payload.mkdir()
    write_json(payload / "family.json", {"run_id": "fixture-generation", "operation": "generate"})
    hashes = {"family.json": sha(payload / "family.json")}
    write_json(payload / "payload.json", {"sha256": hashes})
    for name in ("native-config.json", "reference-candidates.json"):
        write_json(tmp_path / name, {"repo": "synthetic/fixture", "candidates": []})
    (tmp_path / "notices.tar.gz").write_bytes(compressed({"LICENSE": b"synthetic fixture"}))
    ledger = tmp_path / "budget.json"
    budget.create(ledger, 32)
    value = read_json(ledger)
    value.update(
        recorded_paid_cost_usd=0,
        outstanding_reservations_usd=10,
        new_model_calls=0,
        operating_ceiling_usd=90,
        user_limit_exclusive_usd=100,
    )
    write_json(ledger, value)
    group = {
        "id": "generation",
        "run_id": "fixture-generation",
        "payload_directory": "payload",
        "payload_sha256": {**hashes, "payload.json": sha(payload / "payload.json")},
        "resources": {
            "cpus": 4,
            "memory_gib": 16,
            "disk_gib": 30,
            "timeout_seconds": 5400,
            "maximum_cpu_hours": 6,
            "cleanup_cpu_hours": 1 / 6,
        },
        "notices": {"path": "notices.tar.gz"},
        "publication": {"eligible": False},
    }
    plan = {
        "backend": {"config": "synthetic never connected"},
        "client_profile": {"synthetic": True},
        "budget_ledger": str(ledger),
        "plan_identity": "a" * 64,
        "repo2rlenv_revision": "27d04ee8203cd5b2f20c3997d13836e5f5b64238",
        "model_budget": {"maximum_usd": "13.07", "quote_sha256": "b" * 64},
        "archive": {"kind": "local"},
        "group": group,
    }
    write_json(tmp_path / "plan.json", plan)
    remote: dict[str, Any] = {
        "submitted": [],
        "archives": {},
        "fault": False,
        "missing": False,
        "zero_attempts": False,
        "empty": False,
    }

    def call(backend, request, log):
        if request["action"] == "fingerprint":
            return plan["client_profile"]
        selected = request["group"]
        name = selected["run_id"]
        if request["action"] == "preflight":
            return {"worker_id": "synthetic-worker"}
        if request["action"] == "submit":
            assert name not in remote["submitted"]
            remote["submitted"].append(name)
            write_json(
                Path(request["submission_file"]),
                {
                    "job_id": "/exedev/" + name,
                    "state": "submission_pending",
                    "worker_id": "synthetic-worker",
                    "worker_tpu_name": "synthetic-tpu",
                    "payload_sha256": selected["payload_sha256"],
                },
            )
            if remote["fault"]:
                remote["fault"] = False
                raise RuntimeError("lost acknowledgement")
            return read_json(Path(request["submission_file"]))
        assert request["action"] == "observe"
        if remote["missing"]:
            return {"state": "handle_missing"}
        if remote["zero_attempts"] and name == group["run_id"]:
            return {
                "state": "SYNTHETIC_TERMINAL",
                "terminal": True,
                "job_id": "/exedev/" + name,
                "attempts": 0,
                "allocated_cpu_hours": 0,
                "verified_no_creation": True,
                "output_archive": {"state": "empty"},
            }
        operation = (
            "generate"
            if name == group["run_id"]
            else "cleanup"
            if name.endswith("cleanup")
            else "stop"
        )
        report = {
            "run_id": group["run_id"],
            "operation": operation,
            "worker_id": "synthetic-worker",
            "payload_sha256": {
                k: v for k, v in selected["payload_sha256"].items() if k != "payload.json"
            },
            "configuration_verified": True,
            "finished": 1,
            "stage": "synthetic_transport",
            "generation_started": True,
            "stop": {"verified_stopped": True},
            "protected_base": None,
        }
        members = {} if remote["empty"] else {"control-artifacts.tar.gz": compressed(usage())}
        if operation == "cleanup":
            members = {}
            report["cleanup"] = {
                "verified_empty": True,
                "remaining": {"containers": [], "controllers": [], "images": [], "volumes": []},
            }
        report["output_sha256"] = {k: hashlib.sha256(v).hexdigest() for k, v in members.items()}
        members["result.json"] = json.dumps(report).encode()
        archive = tmp_path / (name + ".tar.zst")
        archive.write_bytes(compressed(members, True))
        remote["archives"][name] = archive
        return {
            "state": "SYNTHETIC_TERMINAL",
            "terminal": True,
            "job_id": "/exedev/" + name,
            "attempts": 1,
            "allocated_cpu_hours": 0.01,
            "output_archive": {"state": "uploaded"},
        }

    monkeypatch.setattr(bridge, "call", call)
    monkeypatch.setattr(generation_bridge, "call", call)
    monkeypatch.setattr(
        collection,
        "download",
        lambda account, directory, gcloud: remote["archives"][
            account["job_id"].removeprefix("/exedev/")
        ],
    )
    return GenerationPipeline(tmp_path, plan, group), remote


def finish(pipeline):
    for _ in range(40):
        state = pipeline.step()
        if state == "complete" or state.startswith("held:"):
            return state
    pytest.fail("Synthetic lifecycle did not terminate")


def test_generation_lifecycle_finishes_preservation_cleanup_without_extra_calls(
    pipeline, monkeypatch
):
    p, remote = pipeline
    assert finish(p) == "complete"
    value = read_json(p.ledger)
    assert value["recorded_paid_cost_usd"] == 0.125 and value["new_model_calls"] == 1
    assert (
        value["outstanding_reservations_usd"] == 10
        and value["outstanding_cpu_hour_reservations"] == 0
    )
    assert remote["submitted"] == ["fixture-generation", "fixture-generation-cleanup"]
    monkeypatch.setattr(p, "client", lambda *a, **k: pytest.fail("Completed journal must be inert"))
    assert p.step() == "complete"


def test_uncertain_generation_submit_only_observes_original_handle(pipeline):
    p, remote = pipeline
    p.candidate()
    remote["fault"] = True
    with pytest.raises(RuntimeError, match="acknowledgement"):
        p.ensure_submission(p.group, p.directory)
    remote["missing"] = True
    assert p.ensure_submission(p.group, p.directory) is None
    assert p.ensure_submission(p.group, p.directory) is None
    assert remote["submitted"] == ["fixture-generation"]


def test_scheduler_zero_attempts_releases_model_and_cpu_bounds(pipeline):
    p, remote = pipeline
    remote["zero_attempts"] = True
    assert finish(p) == "complete"
    value = read_json(p.ledger)
    assert value["recorded_paid_cost_usd"] == value["new_model_calls"] == 0
    assert (
        value["outstanding_reservations_usd"] == 10
        and value["outstanding_cpu_hour_reservations"] == 0
    )
    assert remote["submitted"] == ["fixture-generation"]


def test_empty_attempted_archive_stops_and_retains_uncertain_cost(pipeline, monkeypatch):
    p, remote = pipeline
    remote["empty"] = True
    held = []
    monkeypatch.setattr(p, "stop_and_hold", lambda reason: held.append(reason))
    p.candidate()
    p.ensure_submission(p.group, p.directory)
    p.observe(p.group, p.directory)
    p.archive()
    value = read_json(p.ledger)
    assert (
        held and value["outstanding_reservations_usd"] == 23.07 and value["model_admission_closed"]
    )
    assert not (p.directory / "archive_readback_verified.json").exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "candidate_verified",
        "submission_recorded",
        "remote_terminal",
        "archive_readback_verified",
        "publication_resolved",
        "cleanup_terminal",
        "cleanup_verified",
    ],
)
def test_generation_recovers_each_effect_boundary_without_duplicate_work(
    pipeline, monkeypatch, boundary
):
    p, remote = pipeline
    original = p.record
    interrupted = []

    def record(stage, *args, **kwargs):
        if stage == boundary and not interrupted:
            interrupted.append(stage)
            raise InterruptedError(stage)
        return original(stage, *args, **kwargs)

    monkeypatch.setattr(p, "record", record)
    with pytest.raises(InterruptedError):
        finish(p)
    assert finish(p) == "complete"
    assert remote["submitted"] == ["fixture-generation", "fixture-generation-cleanup"]
    value = read_json(p.ledger)
    assert value["recorded_paid_cost_usd"] == 0.125 and value["new_model_calls"] == 1
    assert (
        value["outstanding_reservations_usd"] == 10
        and value["outstanding_cpu_hour_reservations"] == 0
    )
