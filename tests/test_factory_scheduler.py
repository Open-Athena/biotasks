import pytest

from biotasks.factory_batch import freeze_batch
from biotasks.factory_budget import SessionBudget
from biotasks.factory_scheduler import resume_batch


def panel(tmp_path):
    inputs = {}
    for index in range(10):
        name = f"seed-{index}"
        path = tmp_path / (name + ".zip")
        path.write_bytes(b"immutable inputs")
        inputs[name] = path
    batch = tmp_path / "batch.json"
    receipt = freeze_batch("a" * 40, inputs, {}, 40, 1200, 2, batch)
    budget = SessionBudget(tmp_path / "ledger.sqlite", 10, 1, 2)
    return batch, receipt["sha256"], budget


def test_ten_seeds_finish_with_two_slots_and_resumption(tmp_path):
    batch, digest, budget = panel(tmp_path)
    states = {}
    calls = []

    def submit(session, *_):
        calls.append(session)
        job = f"job-{len(calls)}"
        states[job] = "running"
        return job

    for wave in range(5):
        records = resume_batch(batch, digest, tmp_path, budget, submit, states.__getitem__)
        assert sum(row["state"] == "submitted" for row in records) == 2
        assert len(calls) == 2 * (wave + 1)
        # A repeat observation of running jobs must not submit duplicates.
        resume_batch(batch, digest, tmp_path, budget, submit, states.__getitem__)
        assert len(calls) == 2 * (wave + 1)
        states.update(dict.fromkeys(states, "succeeded"))
    records = resume_batch(batch, digest, tmp_path, budget, submit, states.__getitem__)
    assert {row["state"] for row in records} == {"succeeded"}
    assert len(calls) == len(set(calls)) == 10


def test_lost_submit_response_and_unknown_observation_keep_capacity(tmp_path):
    batch, digest, budget = panel(tmp_path)
    calls = []

    def submit(session, *_):
        calls.append(session)
        if len(calls) == 1:
            raise TimeoutError("Job may have been created")
        return "known-job"

    with pytest.raises(TimeoutError):
        resume_batch(batch, digest, tmp_path, budget, submit, lambda _: "unknown")
    records = resume_batch(batch, digest, tmp_path, budget, submit, lambda _: "unknown")
    assert [row["state"] for row in records].count("reserved") == 1
    assert [row["state"] for row in records].count("pending_capacity") == 8
    resume_batch(batch, digest, tmp_path, budget, submit, lambda _: "unknown")
    assert len(calls) == 2
    # A later authoritative failure frees only the known slot, not the uncertain one.
    resume_batch(batch, digest, tmp_path, budget, submit, lambda _: "failed")
    assert len(calls) == 3
