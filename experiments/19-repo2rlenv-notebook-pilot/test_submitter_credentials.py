"""Personal storage credentials belong in the submission environment only."""

import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
from launch_iris import coreweave_credentials, submit_prepared


def sdk_fixture(monkeypatch):
    modules = {
        name: ModuleType(name)
        for name in (
            "iris",
            "iris.cluster",
            "iris.cluster.constraints",
            "iris.cluster.setup_scripts",
            "iris.cluster.types",
            "iris.rpc",
            "rigging",
            "rigging.timing",
        )
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    constraints = modules["iris.cluster.constraints"]
    constraints.Constraint = SimpleNamespace(create=lambda **values: values)
    constraints.ConstraintOp = SimpleNamespace(EQ="eq")
    modules["iris.cluster.setup_scripts"].default_setup_script = lambda **values: values
    types = modules["iris.cluster.types"]
    for name in ("Entrypoint", "EnvironmentSpec", "ResourceSpec"):
        setattr(types, name, SimpleNamespace)
    modules["iris.rpc"].job_pb2 = SimpleNamespace(PRIORITY_BAND_BATCH=1)
    modules["rigging.timing"].Duration = SimpleNamespace(from_seconds=lambda value: value)


def inputs():
    return {
        "campaign-config.json": json.dumps(
            {"entrypoint": "run_autonomous.py", "campaign": "synthetic"}
        ).encode(),
        "inputs.json": json.dumps({"files": {"seed.json": "synthetic-hash"}}).encode(),
    }


@pytest.mark.parametrize(
    "missing", [("CW_KEY_ID",), ("CW_KEY_SECRET",), ("CW_KEY_ID", "CW_KEY_SECRET")]
)
def test_missing_pair_stops_before_claim_or_submission(monkeypatch, tmp_path, missing):
    monkeypatch.setenv("CW_KEY_ID", "synthetic-id")
    monkeypatch.setenv("CW_KEY_SECRET", "synthetic-secret")
    for name in missing:
        monkeypatch.delenv(name)
    receipt = tmp_path / "receipt.json"
    with pytest.raises(ValueError, match="require both CW_KEY_ID and CW_KEY_SECRET"):
        submit_prepared(
            None,
            files=inputs(),
            revision="synthetic",
            receipt=receipt,
            token="synthetic-model",
            daytona_key="synthetic-daytona",
            artifact_prefix="s3://synthetic",
            endpoint_job="synthetic",
            cluster="cw-synthetic",
        )
    assert not receipt.exists()


def test_keys_forwarded_without_entering_payload_or_receipt(monkeypatch, tmp_path):
    sdk_fixture(monkeypatch)
    monkeypatch.setenv("CW_KEY_ID", "personal-fixture-id")
    monkeypatch.setenv("CW_KEY_SECRET", "personal-fixture-secret")
    calls = []

    def submit(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(job_id="/synthetic/job")

    files = inputs()
    before = dict(files)
    receipt = tmp_path / "receipt.json"
    result = submit_prepared(
        SimpleNamespace(submit=submit),
        files=files,
        revision="synthetic",
        receipt=receipt,
        token="synthetic-model",
        daytona_key="synthetic-daytona",
        artifact_prefix="s3://synthetic",
        endpoint_job="synthetic",
        cluster="cw-synthetic",
    )
    assert len(calls) == 1
    env = calls[0]["environment"].env_vars
    assert env["CW_KEY_ID"] == "personal-fixture-id"
    assert env["CW_KEY_SECRET"] == "personal-fixture-secret"
    assert files == before
    assert calls[0]["entrypoint"].workdir_files == before
    assert result["state"] == "submitted"
    assert json.loads(receipt.read_text()) == result
    for value in (b"personal-fixture-id", b"personal-fixture-secret"):
        assert value not in receipt.read_bytes()
        assert all(value not in data for data in files.values())


def test_non_coreweave_submission_does_not_receive_personal_pair(monkeypatch):
    monkeypatch.setenv("CW_KEY_ID", "personal-fixture-id")
    monkeypatch.setenv("CW_KEY_SECRET", "personal-fixture-secret")
    assert coreweave_credentials("synthetic-other-cluster") == {}
