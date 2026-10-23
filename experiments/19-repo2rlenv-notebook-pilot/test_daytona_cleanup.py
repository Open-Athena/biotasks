"""Owned cloud cleanup must never select another job's resources."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from daytona.common.errors import DaytonaNotFoundError
from repo2rlenv.execution.daytona_cleanup import cleanup


@pytest.fixture
def cleanup_clock(monkeypatch):
    from repo2rlenv.execution import daytona_cleanup

    clock = SimpleNamespace(seconds=0.0)

    def advance(seconds):
        clock.seconds += seconds

    monkeypatch.setattr(
        daytona_cleanup, "time", SimpleNamespace(monotonic=lambda: clock.seconds, sleep=advance)
    )
    clock.advance = advance
    return clock


def test_deletes_only_label_bound_resources():
    client = MagicMock()
    sandbox = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=1, memory=2, disk=10)
    client.list.side_effect = [[sandbox], []]
    client.get.side_effect = DaytonaNotFoundError("gone")
    result = cleanup("job-1", client)
    assert result["passed"]
    assert result["sandboxes"][0]["deleted"]
    assert client.list.call_args_list[0].args[0].labels == {"repo2rlenv.job": "job-1"}
    client.delete.assert_called_once_with(sandbox, timeout=60, wait=True)


def test_rejects_wrong_ownership_even_if_provider_filter_failed():
    client = MagicMock()
    client.list.return_value = [MagicMock(labels={"repo2rlenv.job": "someone-else"})]
    with pytest.raises(ValueError, match="ownership"):
        cleanup("job-1", client)
    client.delete.assert_not_called()


def test_remaining_resource_is_unresolved():
    client = MagicMock()
    client.list.side_effect = [
        [],
        [MagicMock(id="late-create", labels={"repo2rlenv.job": "job-1"})],
    ]
    assert not cleanup("job-1", client)["passed"]


@pytest.mark.parametrize("returncode", [0, 1])
def test_supervisor_selects_daytona_and_preserves_failed_creation_uncertainty(
    tmp_path, monkeypatch, returncode
):
    from repo2rlenv.execution import daytona_cleanup, job

    monkeypatch.setenv("REPO2RLENV_REMOTE_WORKER", "1")
    monkeypatch.setenv("REPO2RLENV_EXECUTION_BACKEND", "daytona")
    process = MagicMock(pid=12345)
    process.wait.return_value = returncode
    start = MagicMock(return_value=process)
    monkeypatch.setattr(job.subprocess, "Popen", start)
    monkeypatch.setattr(job.os, "killpg", MagicMock())
    docker = MagicMock(side_effect=AssertionError("Docker cleanup must not run"))
    monkeypatch.setattr(job, "_cleanup_containers", docker)
    cleaned = MagicMock(return_value={"passed": True})
    monkeypatch.setattr(daytona_cleanup, "cleanup", cleaned)
    assert job.execute(tmp_path, ["harbor", "run"], timeout_sec=2) == returncode
    record = json.loads((tmp_path / "job.json").read_text())
    cleaned.assert_called_once_with(record["job_id"])
    assert "labels=" + json.dumps({"repo2rlenv.job": record["job_id"]}) in start.call_args.args[0]
    assert record["cleanup"]["passed"] is (returncode == 0)
    docker.assert_not_called()


@pytest.mark.parametrize("still_present", [False, True])
def test_delete_not_found_still_requires_independent_absence(still_present):
    client = MagicMock()
    sandbox = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=1, memory=2, disk=10)
    client.list.side_effect = [[sandbox], [sandbox] if still_present else []]
    client.delete.side_effect = DaytonaNotFoundError("already deleted")
    if still_present:
        client.get.return_value = MagicMock(state="started")
    else:
        client.get.side_effect = DaytonaNotFoundError("gone")
    result = cleanup("job-1", client)
    assert result["passed"] is (not still_present)
    assert result["sandboxes"][0]["delete_reported_absent"]
    assert client.get.call_count == (2 if still_present else 1)
    client.get.assert_called_with("owned", request_timeout=15)


def test_stale_final_listing_requires_id_readback():
    client = MagicMock()
    stale = MagicMock(id="gone", labels={"repo2rlenv.job": "job-1"})
    client.list.side_effect = [[], [stale]]
    client.get.side_effect = DaytonaNotFoundError("gone")
    result = cleanup("job-1", client)
    assert result["passed"]
    assert result["stale_listing_absent_ids"] == ["gone"]
    client.get.assert_called_once_with("gone", request_timeout=15)
    client.delete.assert_not_called()


@pytest.mark.parametrize("still_present", [False, True])
def test_delete_conflict_requires_independent_absence(still_present, cleanup_clock):
    from daytona.common.errors import DaytonaConflictError

    client = MagicMock()
    sandbox = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=1, memory=2, disk=10)
    client.list.side_effect = [[sandbox], [sandbox] if still_present else []]
    client.delete.side_effect = DaytonaConflictError("transition in progress")
    if still_present:
        client.get.return_value = MagicMock(state="started")
    else:
        client.get.side_effect = DaytonaNotFoundError("gone")
    result = cleanup("job-1", client)
    assert result["passed"] is (not still_present)
    assert result["sandboxes"][0]["delete_reported_conflict"]
    assert client.get.call_count >= (2 if still_present else 1)
    assert cleanup_clock.seconds == (60 if still_present else 0)
    client.delete.assert_called_once_with(sandbox, timeout=60, wait=True)


@pytest.mark.parametrize("terminal", ["absent", "destroyed"])
def test_delete_conflict_observes_delayed_absence_without_repeating_delete(terminal, cleanup_clock):
    from daytona.common.errors import DaytonaConflictError

    client = MagicMock()
    box = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=4, memory=8, disk=10)
    client.list.side_effect = [[box], []]
    client.delete.side_effect = DaytonaConflictError("Already transitioning")
    last = DaytonaNotFoundError("gone") if terminal == "absent" else MagicMock(state="destroyed")
    client.get.side_effect = [MagicMock(state="started"), MagicMock(state="stopping"), last]
    result = cleanup("job-1", client)
    assert result["passed"] and result["sandboxes"][0]["deleted"]
    assert result["sandboxes"][0]["conflict_readback_count"] == 3
    assert cleanup_clock.seconds == 2
    client.delete.assert_called_once_with(box, timeout=60, wait=True)
    assert all(0 < call.kwargs["request_timeout"] <= 15 for call in client.get.call_args_list)


def test_conflict_readback_shares_original_delete_time_allowance(cleanup_clock):
    from daytona.common.errors import DaytonaConflictError

    client = MagicMock()
    box = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=4, memory=8, disk=10)
    client.list.side_effect = [[box], []]

    def delete(*_args, **_kwargs):
        cleanup_clock.advance(59.5)
        raise DaytonaConflictError("Late conflict")

    client.delete.side_effect = delete
    client.get.return_value = MagicMock(state="started")
    result = cleanup("job-1", client)
    assert not result["passed"]  # An empty final listing alone is insufficient.
    assert cleanup_clock.seconds == 60
    client.get.assert_called_once_with("owned", request_timeout=0.5)
    client.delete.assert_called_once_with(box, timeout=60, wait=True)


def test_final_exact_absence_reconciles_prior_live_observation():
    client = MagicMock()
    box = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=4, memory=8, disk=10)
    client.list.side_effect = [[box], [box]]
    client.delete.side_effect = DaytonaNotFoundError("Earlier listing raced deletion")
    client.get.side_effect = [MagicMock(state="stopping"), DaytonaNotFoundError("now gone")]
    result = cleanup("job-1", client)
    assert result["passed"] and result["sandboxes"][0]["deleted"]
    assert result["stale_listing_absent_ids"] == ["owned"]
    client.delete.assert_called_once()


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_conflict_readback_errors_do_not_become_cleanup_success(failure, cleanup_clock):
    from daytona.common.errors import DaytonaConflictError

    client = MagicMock()
    box = MagicMock(id="owned", labels={"repo2rlenv.job": "job-1"}, cpu=4, memory=8, disk=10)
    client.list.return_value = [box]
    client.delete.side_effect = DaytonaConflictError("Transition")
    client.get.side_effect = failure()
    with pytest.raises(failure):
        cleanup("job-1", client)
    assert cleanup_clock.seconds == 0
    client.delete.assert_called_once()
