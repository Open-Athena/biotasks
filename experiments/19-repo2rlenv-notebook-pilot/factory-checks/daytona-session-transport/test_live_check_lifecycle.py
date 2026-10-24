"""The future live check must clean owned resources without hiding its first error."""

import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).with_name("run_live_check.py")
SPEC = importlib.util.spec_from_file_location("session_live_check_fixture", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("lost_creation_response", [False, True])
@pytest.mark.parametrize("cleanup_error", [False, True])
def test_work_failure_preserves_primary_error_and_always_attempts_owned_cleanup(
    tmp_path, monkeypatch, lost_creation_response, cleanup_error
):
    events = []

    def create(params, **kwargs):
        events.append("create")
        assert (params.resources.cpu, params.resources.memory, params.resources.disk) == (4, 8, 10)
        assert params.network_block_all and params.labels == {
            "repo2rlenv.job": "biotasks19-session-compat-fixture"
        }
        if lost_creation_response:
            raise ConnectionError("creation acknowledgement lost")
        return SimpleNamespace(
            id="owned-fixture",
            cpu=2,  # Deliberately wrong observed profile; no command may follow.
            memory=8,
            disk=10,
            refresh_data=lambda **kwargs: events.append("refresh"),
        )

    class Client:
        async def close(self):
            events.append("close")
            if cleanup_error:
                raise RuntimeError("fixture close failed")

    def cleanup(owner, provider):
        events.append("cleanup")
        assert owner == "biotasks19-session-compat-fixture"
        if cleanup_error:
            raise RuntimeError("fixture cleanup failed")
        return {"passed": True, "sandboxes": [], "remaining": []}

    def no_worker(*args, **kwargs):
        raise AssertionError("No command is allowed after an invalid or unknown creation")

    monkeypatch.setattr(MODULE, "Daytona", lambda: SimpleNamespace(create=create))
    monkeypatch.setattr(MODULE, "AsyncDaytona", Client)
    monkeypatch.setattr(MODULE, "cleanup", cleanup)
    monkeypatch.setattr(MODULE, "DaytonaWorker", no_worker)
    monkeypatch.setattr(MODULE.importlib.metadata, "version", lambda name: "0.211.2")
    config = {
        "owner": "biotasks19-session-compat-fixture",
        "resources": {"cpus": 4, "memory_gib": 8, "disk_gib": 10, "gpu": False},
        "seconds": 300,
        "cleanup_seconds": 180,
        "reservation_usd": "1.00",
        "model_calls": 0,
    }
    expected = ConnectionError if lost_creation_response else ValueError
    with pytest.raises(expected):
        asyncio.run(MODULE.run(config, tmp_path / "run"))
    assert events.count("create") == 1 and events[-2:] == ["close", "cleanup"]
    result = json.loads((tmp_path / "run/result.json").read_text())
    assert result["status"] == "incomplete"
    assert result["error_type"] == expected.__name__ and not result["cases"]
    assert result["new_model_calls"] == 0 and not result["scientific_computation"]
    assert result["cleanup_verified"] is (not lost_creation_response and not cleanup_error)
    if cleanup_error:
        assert result["client_close_error_type"] == result["cleanup_error_type"] == "RuntimeError"
