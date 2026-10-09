import pytest

from biotasks.factory_budget import SessionBudget


def test_uncertain_submission_holds_capacity_across_restart(tmp_path):
    path = tmp_path / "budget.sqlite"
    budget = SessionBudget(path, 3, 2, 1)
    budget.reserve("one", "seed-a", "authoring", "a" * 64)
    resumed = SessionBudget(path, 3, 2, 1)
    with pytest.raises(ValueError, match="concurrency"):
        resumed.reserve("two", "seed-b", "authoring", "b" * 64)
    with pytest.raises(ValueError, match="already reserved"):
        resumed.reserve("one", "seed-a", "authoring", "a" * 64)
    resumed.submitted("one", "remote-one")
    with pytest.raises(ValueError, match="terminal"):
        resumed.terminal("one", "remote-one", "observation_timeout")
    with pytest.raises(ValueError, match="match"):
        resumed.terminal("one", "wrong-job", "failed")
    resumed.terminal("one", "remote-one", "failed")
    resumed.reserve("two", "seed-a", "repair", "b" * 64)
    resumed.submitted("two", "remote-two")
    resumed.terminal("two", "remote-two", "succeeded")
    with pytest.raises(ValueError, match="Seed session"):
        resumed.reserve("three", "seed-a", "review", "c" * 64)
    resumed.reserve("three", "seed-b", "authoring", "c" * 64)
    with pytest.raises(ValueError, match="Campaign session"):
        resumed.reserve("four", "seed-c", "authoring", "d" * 64)


def test_existing_limits_cannot_be_silently_expanded(tmp_path):
    path = tmp_path / "budget.sqlite"
    SessionBudget(path, 3, 2, 1)
    with pytest.raises(ValueError, match="limits differ"):
        SessionBudget(path, 30, 20, 10)


def test_authoritative_rejection_keeps_slot_and_spec_without_refunding_budget(tmp_path):
    budget = SessionBudget(tmp_path / "campaign.sqlite", 1, 1, 1)
    budget.reserve("first", "seed", "specification", "a" * 64)
    budget.rejected_before_submission("first", "b" * 64, "Server rejected duplicate remote name")
    with pytest.raises(ValueError, match="Campaign session budget"):
        budget.reserve("different", "other", "specification", "a" * 64)
    with pytest.raises(ValueError, match="already reserved"):
        budget.reserve("first", "seed", "specification", "c" * 64)
    budget.reserve("first", "seed", "specification", "a" * 64)
    budget.submitted("first", "actual-job")
    with pytest.raises(ValueError, match="unacknowledged"):
        budget.rejected_before_submission("first", "b" * 64, "Cannot undo a created job")
    with budget.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM submission_rejections").fetchone()[0] == 1
