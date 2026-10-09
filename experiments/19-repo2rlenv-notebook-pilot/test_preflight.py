"""Resource/isolation checks must fail closed and reconcile uncertain creation."""

import json
import time
from unittest.mock import MagicMock

import preflight
import pytest
from daytona.common.errors import DaytonaNotFoundError


def client_fixture(monkeypatch, reachable=False):
    monkeypatch.setattr(preflight.socket, "create_connection", MagicMock())
    client = MagicMock()
    sandbox = client.create.return_value
    sandbox.id = "owned-id"
    sandbox.cpu, sandbox.memory, sandbox.disk = 1, 2, 10
    sandbox.network_block_all = True
    sandbox.process.exec.return_value.exit_code = 0
    sandbox.process.exec.return_value.result = json.dumps(
        [{"host": host, "port": port, "reachable": reachable} for host, port in preflight.TARGETS]
    )
    client.get.side_effect = DaytonaNotFoundError("not found")
    return client


def test_success_and_no_relaunch(tmp_path, monkeypatch):
    client = client_fixture(monkeypatch)
    result = preflight.run(client, root=tmp_path, campaign="test", deadline=time.time() + 700)
    assert result["passed"] and result["cleanup_verified"]
    params = client.create.call_args.args[0]
    assert params.network_block_all is True and params.ttl_minutes == 10
    assert params.resources.cpu == 1 and params.resources.memory == 2
    client.delete.assert_called_once_with(client.create.return_value, timeout=60, wait=True)
    with pytest.raises(FileExistsError):
        preflight.run(client, root=tmp_path, campaign="test", deadline=time.time() + 700)
    assert client.create.call_count == 1


def test_network_failure_still_cleans_up(tmp_path, monkeypatch):
    client = client_fixture(monkeypatch, reachable=True)
    with pytest.raises(RuntimeError, match="external destination"):
        preflight.run(client, root=tmp_path, campaign="test", deadline=time.time() + 700)
    result = json.loads((tmp_path / "infrastructure-preflight.json").read_text())
    assert not result["passed"] and result["cleanup_verified"]
    client.delete.assert_called_once()


def test_uncertain_creation_not_found_is_not_cleanup_proof(tmp_path, monkeypatch):
    client = client_fixture(monkeypatch)
    client.create.side_effect = TimeoutError("unknown provider state")
    with pytest.raises(TimeoutError):
        preflight.run(client, root=tmp_path, campaign="test", deadline=time.time() + 700)
    result = json.loads((tmp_path / "infrastructure-preflight.json").read_text())
    assert not result["passed"] and not result["cleanup_verified"]
    assert result["error_type"] == "TimeoutError"
