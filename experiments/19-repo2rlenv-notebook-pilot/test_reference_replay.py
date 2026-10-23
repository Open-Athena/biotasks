"""Offline tests for frozen replay; no biological computation or API calls."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from reference_environment import setup_script
from reference_replay import compare_inventory, load_snapshot, replay_reference
from reference_setup import PreparedReference
from run_reference_setup import check_config

HERE = Path(__file__).parent


def test_snapshot_checks_reference_and_export_identity():
    prepared = PreparedReference.load(HERE / "preparation-runs/010")
    snapshot = load_snapshot(HERE / "setup-runs/001", prepared)
    assert len(snapshot["outputs"]) == 3
    broken = PreparedReference(prepared.context, prepared.plan, prepared.baseline, "different")
    with pytest.raises(ValueError, match="exports differ"):
        load_snapshot(HERE / "setup-runs/001", broken)


def test_locked_setup_never_resolves_again():
    script = setup_script([], locked=True)
    assert "uv lock " not in script
    assert "uv sync --project /work/environment --locked" in script
    assert "uv lock " in setup_script([])


def test_comparison_is_observational_and_inventory_must_match():
    expected = [{"path": "a", "sha256": "first"}]
    assert not compare_inventory(expected, [{"path": "a", "exists": True, "sha256": "second"}])[0][
        "byte_identical"
    ]
    with pytest.raises(ValueError, match="inventory"):
        compare_inventory(expected, [])
    with pytest.raises(ValueError, match="inventory"):
        compare_inventory(expected, [{"path": "a"}, {"path": "a"}])


def test_replay_configuration():
    check_config(json.loads((HERE / "reference-replay.json").read_text()))


class Remote:
    def __init__(self, snapshot, *, drift=False, bad_download=False):
        self.snapshot, self.drift, self.bad_download = snapshot, drift, bad_download
        self.files, self.events = {}, []
        self.blocked = False
        self.output = b"measured\n"

    async def upload(self, local, remote):
        self.files[remote] = local.read_bytes()

    async def download(self, remote, local):
        if remote.endswith("environment.txt"):
            data = (self.snapshot["directory"] / "trial/environment.txt").read_bytes()
            if self.drift:
                data += b"extra==1\n"
        elif remote.startswith("/work/outputs/"):
            data = b"corrupt" if self.bad_download else self.output
        else:
            data = self.files[remote]
        local.write_bytes(data)

    async def command(self, argv, seconds, label, *, cwd="/work"):
        self.events.append(label)
        if label.startswith("replay-reference-"):
            assert self.blocked and cwd == "/work/run"
        return {"exit_code": 0}

    async def network(self, blocked):
        self.blocked = blocked

    async def helper(self, args, label):
        assert self.blocked
        self.events.append(label)
        if args[0] == "verify-staging":
            return {"staged_inputs_verified": True}
        return {
            "declared_artifacts_present": True,
            "artifacts": [
                {
                    "path": "result.txt",
                    "exists": True,
                    "sha256": hashlib.sha256(self.output).hexdigest(),
                }
            ],
        }


def fixture():
    prepared = PreparedReference.load(HERE / "preparation-runs/010")
    snapshot = load_snapshot(HERE / "setup-runs/001", prepared)
    snapshot["outputs"] = [
        {"path": "result.txt", "sha256": hashlib.sha256(b"measured\n").hexdigest()}
    ]
    return snapshot


def test_replay_runs_fresh_offline_processes_and_hashes_downloads(tmp_path):
    snapshot = fixture()
    remote = Remote(snapshot)
    config = {"max_tests": 2, "setup_seconds": 1800, "reference_seconds": 600}
    result = asyncio.run(
        replay_reference(remote=remote, snapshot=snapshot, root=tmp_path / "r", config=config)
    )
    assert result["model_calls"] == 0 and result["reference_tests"] == 2
    assert result["all_outputs_byte_identical_to_original"]
    assert not result["comparison_rules_validated"]
    for i in (1, 2):
        assert (
            remote.events.index(f"replay-reset-{i}")
            < remote.events.index(f"replay-inputs-before-{i}")
            < remote.events.index(f"replay-reference-{i}")
            < remote.events.index(f"replay-inputs-after-{i}")
        )


@pytest.mark.parametrize("corrupt_receipt", [False, True])
def test_replay_reuses_frozen_removal_helper_and_checks_receipt(tmp_path, corrupt_receipt):
    import shutil

    snapshot = fixture()
    source = tmp_path / "frozen"
    for name in (
        "candidate/pyproject.toml",
        "candidate/stage-inputs.sh",
        "candidate/inputs.json",
        "trial/uv.lock",
        "trial/environment.txt",
        "trial/reference.py",
        "trial/inputs-before.json",
        "inputs/plan.json",
    ):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(snapshot["directory"] / name, target)
    snapshot["directory"] = source
    snapshot["dependency_exclusions"] = {"files": []}
    for name, content in {
        "candidate/dependency-exclusions.json": '{"files": []}',
        "trial/dependency_assets.py": "# frozen helper\n",
        "trial/dependency-exclusions-applied.json": '{"files": [], "excluded_files_absent": true}',
    }.items():
        (source / name).write_text(content)
        snapshot["hashes"][name] = hashlib.sha256(content.encode()).hexdigest()

    class ExclusionRemote(Remote):
        async def command(self, argv, seconds, label, **kwargs):
            if label == "replay-setup":
                assert self.files["/work/dependency_assets.py"] == b"# frozen helper\n"
                assert "UV_NO_CACHE=1" in self.files["/work/setup.sh"].decode()
                receipt = (source / "trial/dependency-exclusions-applied.json").read_bytes()
                self.files["/work/environment/dependency-exclusions-applied.json"] = receipt + (
                    b" " if corrupt_receipt else b""
                )
            return await super().command(argv, seconds, label, **kwargs)

    remote = ExclusionRemote(snapshot)
    options = dict(
        remote=remote,
        snapshot=snapshot,
        root=tmp_path / "replay",
        config={"max_tests": 1, "setup_seconds": 30, "reference_seconds": 10},
    )
    if corrupt_receipt:
        with pytest.raises(RuntimeError, match="dependency removal differs"):
            asyncio.run(replay_reference(**options))
        assert "replay-reference-1" not in remote.events
    else:
        assert asyncio.run(replay_reference(**options))["reference_tests"] == 1


@pytest.mark.parametrize("failure", ["drift", "bad_download"])
def test_replay_fails_closed_on_drift_or_transport_corruption(tmp_path, failure):
    snapshot = fixture()
    remote = Remote(snapshot, **{failure: True})
    with pytest.raises(RuntimeError):
        asyncio.run(
            replay_reference(
                remote=remote,
                snapshot=snapshot,
                root=tmp_path / "r",
                config={"max_tests": 2, "setup_seconds": 30, "reference_seconds": 10},
            )
        )
    assert "replay-reference-2" not in remote.events


def test_replay_launcher_refuses_model_credentials_before_submission(tmp_path):
    from launch_iris import submit_prepared

    with pytest.raises(ValueError, match="must not receive model"):
        submit_prepared(
            None,
            files={"campaign-config.json": json.dumps({"entrypoint": "run_reference_replay.py"})},
            revision="fixture",
            receipt=tmp_path / "receipt.json",
            token="fixture",
            daytona_key="fixture",
            artifact_prefix="s3://fixture",
            endpoint_job=None,
            cluster="fixture",
        )
    assert not (tmp_path / "receipt.json").exists()
