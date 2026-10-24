"""The stage owns its async process client and retains its first failure."""

import asyncio
import json
import time
from types import SimpleNamespace

import daytona_session
import pytest


@pytest.mark.parametrize("failure", [None, "lookup", "work"])
@pytest.mark.parametrize("close_failure", [False, True])
def test_client_is_closed_once_without_masking_original_error(
    tmp_path, monkeypatch, failure, close_failure
):
    events = []
    process = object()

    class Client:
        async def get(self, identity, **kwargs):
            events.append("get")
            assert identity == "existing-owned-sandbox" and kwargs["request_timeout"] == 15
            if failure == "lookup":
                raise ConnectionError("original lookup failure")
            return SimpleNamespace(id=identity, process=process)

        async def close(self):
            events.append("close")
            if close_failure:
                raise ValueError("secondary close failure")

    monkeypatch.setattr(daytona_session, "AsyncDaytona", Client)

    async def exercise():
        async with daytona_session.owned_session_process(
            "existing-owned-sandbox", tmp_path, time.time() + 60, enabled=True
        ) as supplied:
            assert supplied is process
            events.append("work")
            if failure == "work":
                raise RuntimeError("original worker failure")

    expected = {"lookup": ConnectionError, "work": RuntimeError}.get(failure)
    if expected or close_failure:
        with pytest.raises(expected or ValueError):
            asyncio.run(exercise())
    else:
        asyncio.run(exercise())
    assert events == (["get", "close"] if failure == "lookup" else ["get", "work", "close"])
    receipt = json.loads((tmp_path / "session-client.json").read_text())
    assert receipt["state"] == ("close_failed" if close_failure else "closed")
    if expected:
        assert receipt["primary_error_type"] == expected.__name__
    if close_failure:
        assert receipt["close_error_type"] == "ValueError"


def test_legacy_client_scope_allocates_nothing(tmp_path, monkeypatch):
    def forbidden():
        raise AssertionError("Legacy transport must not allocate an async client")

    monkeypatch.setattr(daytona_session, "AsyncDaytona", forbidden)

    async def exercise():
        async with daytona_session.owned_session_process(
            "existing", tmp_path, time.time() + 60, enabled=False
        ) as process:
            assert process is None

    asyncio.run(exercise())
    assert not list(tmp_path.iterdir())


def test_future_autonomous_stages_select_live_checked_transport():
    from run_autonomous import Pipeline

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.config = {"campaign": "fixture"}
    pipeline.reasoning_effort = "high"
    for entrypoint in [
        "run_reference_setup.py",
        "run_reference_replay.py",
        "run_notebook_grader.py",
    ]:
        config = pipeline.config_for("fixture", entrypoint)
        assert config["command_transport"] == "async_session"
        assert config["reference_seconds"] == 600 and config["verifier_seconds"] == 120
        assert config["max_tests"] == 2 and config["max_requests"] is None


@pytest.mark.parametrize("value", [None, "sync_session", True, 3])
def test_unknown_transport_rejected_before_resource_creation(value):
    from run_reference_setup import check_config

    with pytest.raises(ValueError, match="Unknown command transport"):
        check_config({"reasoning_effort": "high", "command_transport": value})


def test_different_sandbox_identity_is_rejected_and_client_closed(tmp_path, monkeypatch):
    events = []

    class Client:
        async def get(self, identity, **kwargs):
            return SimpleNamespace(id="another-sandbox", process=object())

        async def close(self):
            events.append("close")

    monkeypatch.setattr(daytona_session, "AsyncDaytona", Client)

    async def exercise():
        async with daytona_session.owned_session_process(
            "expected", tmp_path, time.time() + 60, enabled=True
        ):
            raise AssertionError("Must not dispatch to another sandbox")

    with pytest.raises(ValueError, match="different sandbox identity"):
        asyncio.run(exercise())
    assert events == ["close"]
