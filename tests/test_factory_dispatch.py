import pytest

from biotasks.factory_batch import freeze_batch
from biotasks.factory_budget import SessionBudget
from biotasks.factory_dispatch import dispatch, session_identity
from biotasks.factory_stage import stage_spec


def followup(tmp_path, root_hash, archive, slot, predecessor):
    """Create a frozen stage input without calling a remote worker."""
    import hashlib
    import json

    role = "review" if slot == "review_after_repair" else slot
    spec = stage_spec(role, archive, 40, 1200)
    spec.update(stage_slot=slot, predecessor=predecessor)
    path = tmp_path / f"{slot}.json"
    path.write_text(
        json.dumps(
            {
                "root_batch_sha256": root_hash,
                "factory_revision": "a" * 40,
                "entries": {"novel-seed": spec},
            }
        )
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def predecessor_receipt(budget, session):
    with budget.connect() as db:
        spec_hash, job_id = db.execute(
            "SELECT spec_sha256, job_id FROM sessions WHERE id=?", (session,)
        ).fetchone()
    return {
        "session_id": session,
        "spec_sha256": spec_hash,
        "job_id": job_id,
        "artifact_receipt_sha256": "b" * 64,
    }


def prepared(tmp_path):
    archive = tmp_path / "inputs.zip"
    archive.write_bytes(b"immutable input")
    batch = tmp_path / "batch.json"
    receipt = freeze_batch("a" * 40, {"novel-seed": archive}, {}, 40, 1200, 1, batch)
    budget = SessionBudget(tmp_path / "budget.sqlite", 2, 2, 1)
    return batch, receipt["sha256"], archive, budget


def test_lost_submission_response_never_causes_automatic_resubmit(tmp_path):
    batch, digest, archive, budget = prepared(tmp_path)
    calls = []

    def remote(session, frozen, inputs):
        calls.append(session)
        raise TimeoutError("Response lost after remote submission")

    with pytest.raises(TimeoutError):
        dispatch(batch, digest, "novel-seed", archive, budget, remote)
    with pytest.raises(ValueError, match="already reserved"):
        dispatch(batch, digest, "novel-seed", archive, budget, remote)
    assert len(calls) == 1


def test_changed_inputs_never_reach_backend_or_consume_session(tmp_path):
    batch, digest, archive, budget = prepared(tmp_path)
    archive.write_bytes(b"changed input")
    calls = []

    def remote(*args):
        calls.append(args)
        return "unexpected-job"

    with pytest.raises(ValueError, match="archive changed"):
        dispatch(batch, digest, "novel-seed", archive, budget, remote)
    assert not calls
    with budget.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_followup_waits_for_exact_terminal_parent(tmp_path):
    batch, digest, archive, budget = prepared(tmp_path)
    calls = []

    def remote(session, frozen, inputs):
        calls.append(session)
        return f"job-{len(calls)}"

    job = dispatch(batch, digest, "novel-seed", archive, budget, remote)
    parent = session_identity(digest, "novel-seed", "authoring")
    receipt = predecessor_receipt(budget, parent)
    review, review_hash = followup(tmp_path, digest, archive, "review", receipt)
    with pytest.raises(ValueError, match="not authoritatively terminal"):
        dispatch(review, review_hash, "novel-seed", archive, budget, remote)
    assert len(calls) == 1
    # A failed author may still leave artifacts worth reviewing. Terminal status
    # permits scheduling only; this is not scientific acceptance.
    budget.terminal(parent, job, "failed")
    dispatch(review, review_hash, "novel-seed", archive, budget, remote)
    assert calls[-1] == session_identity(digest, "novel-seed", "review")


def test_repair_sequence_has_distinct_review_slots_and_cannot_restart(tmp_path):
    batch, digest, archive, _ = prepared(tmp_path)
    budget = SessionBudget(tmp_path / "workflow.sqlite", 4, 4, 1)
    calls = []

    def remote(session, frozen, inputs):
        calls.append(session)
        return f"job-{len(calls)}"

    job = dispatch(batch, digest, "novel-seed", archive, budget, remote)
    parent = session_identity(digest, "novel-seed", "authoring")
    budget.terminal(parent, job, "succeeded")
    for slot in ("review", "repair", "review_after_repair"):
        record, record_hash = followup(
            tmp_path, digest, archive, slot, predecessor_receipt(budget, parent)
        )
        job = dispatch(record, record_hash, "novel-seed", archive, budget, remote)
        parent = session_identity(digest, "novel-seed", slot)
        budget.terminal(parent, job, "succeeded")
    assert len(set(calls)) == 4
    # A new file hash is not a new authorization for the same workflow slot.
    with pytest.raises(ValueError, match="already reserved"):
        dispatch(record, record_hash, "novel-seed", archive, budget, remote)
    assert len(calls) == 4


def test_stage_cannot_skip_parent_or_substitute_another_remote_job(tmp_path):
    batch, digest, archive, budget = prepared(tmp_path)

    def remote(*args):
        return "author-job"

    job = dispatch(batch, digest, "novel-seed", archive, budget, remote)
    parent = session_identity(digest, "novel-seed", "authoring")
    budget.terminal(parent, job, "succeeded")
    receipt = predecessor_receipt(budget, parent)
    record, record_hash = followup(tmp_path, digest, archive, "repair", receipt)
    with pytest.raises(ValueError, match="Wrong workflow predecessor"):
        dispatch(record, record_hash, "novel-seed", archive, budget, remote)
    receipt["job_id"] = "different-job"
    record, record_hash = followup(tmp_path, digest, archive, "review", receipt)
    with pytest.raises(ValueError, match="differs from the reserved"):
        dispatch(record, record_hash, "novel-seed", archive, budget, remote)
    with budget.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


def test_followup_cannot_change_factory_revision(tmp_path):
    import hashlib
    import json

    batch, digest, archive, budget = prepared(tmp_path)
    calls = []

    def remote(session, frozen, inputs):
        calls.append(session)
        return "author-job"

    job = dispatch(batch, digest, "novel-seed", archive, budget, remote)
    parent = session_identity(digest, "novel-seed", "authoring")
    budget.terminal(parent, job, "succeeded")
    record, _ = followup(tmp_path, digest, archive, "review", predecessor_receipt(budget, parent))
    changed = json.loads(record.read_text())
    changed["factory_revision"] = "c" * 40
    record.write_text(json.dumps(changed))
    changed_hash = hashlib.sha256(record.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Factory revision changed"):
        dispatch(record, changed_hash, "novel-seed", archive, budget, remote)
    assert len(calls) == 1
