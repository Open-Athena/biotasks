"""Owned cloud cleanup must never select another job's resources."""

import json
from unittest.mock import MagicMock

import pytest
from daytona.common.errors import DaytonaNotFoundError
from repo2rlenv.execution.daytona_cleanup import cleanup


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
    client.list.side_effect = [[], [MagicMock(id="late-create")]]
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
