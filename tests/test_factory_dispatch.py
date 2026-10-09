import pytest

from biotasks.factory_batch import freeze_batch
from biotasks.factory_budget import SessionBudget
from biotasks.factory_dispatch import dispatch


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
