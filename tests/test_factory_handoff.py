import hashlib
import json
import zipfile

import pytest

from biotasks.factory_batch import freeze_batch
from biotasks.factory_budget import SessionBudget
from biotasks.factory_dispatch import dispatch, session_identity
from biotasks.factory_handoff import freeze_followup


def test_frozen_followup_dispatches_exact_parent_records_without_expanding_budget(tmp_path):
    source = tmp_path / "source.zip"
    source.write_bytes(b"original inputs")
    initial = tmp_path / "batch.json"
    frozen = freeze_batch("a" * 40, {"unseen": source}, {}, 40, 1200, 1, initial)
    budget = SessionBudget(tmp_path / "ledger.sqlite", 2, 2, 1)
    calls = []

    def remote(session, batch, archive):
        calls.append((session, batch, archive))
        return f"job-{len(calls)}"

    job = dispatch(initial, frozen["sha256"], "unseen", source, budget, remote)
    session = session_identity(frozen["sha256"], "unseen", "authoring")
    budget.terminal(session, job, "succeeded")
    with budget.connect() as db:
        spec_hash = db.execute(
            "SELECT spec_sha256 FROM sessions WHERE id=?", (session,)
        ).fetchone()[0]
    parent = {"session_id": session, "job_id": job, "spec_sha256": spec_hash}
    descriptor = {
        "artifact_prefix": "s3://example/parent",
        "input_zip_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "generated_manifest": [],
        "deleted_inputs": [],
        "task_manifest": [],
    }
    envelope, stage = tmp_path / "handoff.zip", tmp_path / "stage.json"
    receipt = freeze_followup(
        initial,
        frozen["sha256"],
        "unseen",
        "review",
        parent,
        descriptor,
        {"result.json": b'{"outcome":"worker_finished"}'},
        20,
        600,
        envelope,
        stage,
    )
    frozen_stage = json.loads(stage.read_text())
    spec = frozen_stage["entries"]["unseen"]
    with zipfile.ZipFile(envelope) as archive:
        descriptor_bytes = archive.read("parent-restore.json")
        assert (
            hashlib.sha256(descriptor_bytes).hexdigest()
            == spec["predecessor"]["artifact_receipt_sha256"]
        )
        pinned = json.loads(descriptor_bytes)
        record = archive.read("parent-records/result.json")
        assert pinned["record_files"][0]["sha256"] == hashlib.sha256(record).hexdigest()
    dispatch(stage, receipt["sha256"], "unseen", envelope, budget, remote)
    assert len(calls) == 2
    assert calls[-1][0] == session_identity(frozen["sha256"], "unseen", "review")
    assert spec["request_cap"] == 20 and spec["wall_seconds"] == 600
    assert frozen_stage["factory_revision"] == "a" * 40
    with pytest.raises(FileExistsError):
        freeze_followup(
            initial,
            frozen["sha256"],
            "unseen",
            "review",
            parent,
            descriptor,
            {"result.json": b"different"},
            20,
            600,
            envelope,
            stage,
        )
    with pytest.raises(ValueError, match="expands"):
        freeze_followup(
            initial,
            frozen["sha256"],
            "unseen",
            "review",
            parent,
            descriptor,
            {"result.json": b"different"},
            41,
            600,
            tmp_path / "expanded.zip",
            tmp_path / "expanded.json",
        )
