"""Real pinned local exporter; synthetic task, no models/Docker/network/SDK RPC."""

import importlib.util
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from biotasks.validation import bridge, budget, planning
from biotasks.validation.files import (
    ValidationError,
    inventory,
    json_sha,
    read_json,
    sha,
    write_json,
)

ROOT = Path(__file__).resolve().parent
WORKTREES = ROOT.parents[2]
SOURCE_ROOT = WORKTREES / "31/experiments/31-historical-builds"
spec = importlib.util.spec_from_file_location("handoff", ROOT / "handoff.py")
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)
REF = "a" * 40
IMAGE = "local/r2e-bootstrap/synthetic__fixture:" + REF[:12]


@pytest.fixture
def fixture(tmp_path):
    source = SOURCE_ROOT / "inputs-private/upstream-package"
    source_manifest = SOURCE_ROOT / "package-acquisition.json"
    extras = SOURCE_ROOT / "inputs-private/check-deps"
    native = handoff.source_api(source, source_manifest, extras)
    raw, cache = tmp_path / "raw", tmp_path / "cache"
    task = raw / "synthetic__fixture-1"
    for folder in ("environment", "tests", "solution"):
        (task / folder).mkdir(parents=True)
    (task / "task.toml").write_text(
        '[metadata.repo2env]\npipeline="pr_runtime"\nrepo="synthetic/fixture"\n[metadata.repo2env.pr_runtime]\nbase_commit="'
        + REF
        + '"\n[verifier]\ntimeout_sec=300\n[agent]\ntimeout_sec=1800\n[environment]\ncpus=1\nmemory_mb=6144\n'
    )
    (task / "environment/Dockerfile").write_text(
        "FROM " + IMAGE + "\nWORKDIR /workspace\nRUN echo synthetic-overlay-not-executed\n"
    )
    (task / "environment/docker-compose.yaml").write_text(
        'services:\n  main:\n    extra_hosts:\n      - "github.com:0.0.0.0"\n'
    )
    for name in (
        "instruction.md",
        "solution/patch.diff",
        "solution/solve.sh",
        "tests/test.sh",
        "tests/verifier.py",
    ):
        (task / name).write_text("synthetic interface fixture; never executed\n")
    (task / "solution/solve.sh").chmod(0o755)
    for name in ("f2p", "p2p"):
        write_json(task / "tests" / (name + ".json"), ["test_" + name])
    write_json(
        cache / "synthetic__fixture" / REF[:12] / "bootstrap.json",
        {
            "repo": "synthetic/fixture",
            "ref": REF,
            "image_tag": IMAGE,
            "language": "python",
            "rebuild_cmds": ["echo recorded-synthetic-command-never-executed"],
            "test_cmds": ["python -m pytest"],
            "dockerfile_reconstruction": "FROM python:3.12-slim\n",
        },
    )
    iris = tmp_path / "iris.yaml"
    iris.write_text("synthetic config never connected\n")
    ledger = tmp_path / "budget.json"
    budget.create(ledger, 12)
    config = {
        "upstream_source": str(source),
        "upstream_manifest": str(source_manifest),
        "upstream_manifest_sha256": sha(source_manifest),
        "upstream_extra_modules": str(extras),
        "upstream_extra_modules_sha256": json_sha(inventory(extras)),
        "raw_exports": str(raw),
        "bootstrap_cache": str(cache),
        "output_directory": str(tmp_path / "result"),
        "raw_inventory_sha256": json_sha(inventory(raw)),
        "cache_inventory_sha256": json_sha(inventory(cache)),
        "validation_template": {
            "schema_version": 1,
            "id": "handoff-fixture",
            "repo2rlenv_revision": handoff.UPSTREAM,
            "backend": {
                "type": "iris",
                "python": sys.executable,
                "config": str(iris),
                "worker_revision": "c7c14a252d",
            },
            "budget_ledger": str(ledger),
            "max_cpu_hours_per_task": 6,
            "archive": {"kind": "local"},
        },
    }
    return config, native


def test_official_export_feeds_real_validator_plan(fixture, monkeypatch):
    config, native = fixture
    result = handoff.prepare(config, native)
    assert result["state"] == "prepared" and result["task_count"] == 1
    output = Path(config["output_directory"]) / "handoff"
    manifest = read_json(output / "validation-manifest.json")
    assert manifest["exports"][0]["initializer"] == "native-inline"
    calls = []
    monkeypatch.setattr(
        bridge,
        "call",
        lambda backend, request, log: calls.append(request) or {"synthetic_fingerprint_only": True},
    )
    plan = planning.prepare(output / "validation-manifest.json", output.parent / "validation-plan")
    assert len(plan["tasks"]) == 1 and not plan["unsupported"]
    task = plan["tasks"][0]
    assert task["task"]["verifier_seconds"] == 300 and task["task"]["agent_seconds"] == 1800
    assert all(row.get("action") == "fingerprint" for row in calls)
    assert (
        read_json(Path(config["validation_template"]["budget_ledger"]))[
            "outstanding_cpu_hour_reservations"
        ]
        == 0
    )


@pytest.mark.parametrize(
    "boundary", ["before_native_export", "after_native_export", "before_commit", "after_commit"]
)
def test_interrupted_local_export_recovers_from_immutable_raw(fixture, boundary):
    config, native = fixture

    def interrupt(stage):
        if stage == boundary:
            raise InterruptedError(boundary)

    with pytest.raises(InterruptedError):
        handoff.prepare(config, native, interrupt)
    result = handoff.prepare(config, native)
    assert result["state"] == "prepared"
    output = Path(config["output_directory"])
    frozen = inventory(output)
    assert handoff.prepare(config, native) == result
    assert inventory(output) == frozen
    assert not (output / "staging").exists()


def test_raw_mode_change_blocks_completed_resume(fixture):
    config, native = fixture
    handoff.prepare(config, native)
    next(Path(config["raw_exports"]).glob("*/solution/solve.sh")).chmod(0o644)
    with pytest.raises(ValidationError, match="Original generation inputs changed"):
        handoff.prepare(config, native)


def test_ambiguous_cache_blocks_before_export(fixture):
    config, native = fixture
    cache = Path(config["bootstrap_cache"])
    slot = cache / "synthetic__fixture" / REF[:12]
    shutil.copytree(slot, slot.with_name(slot.name + "__other"))
    config["cache_inventory_sha256"] = json_sha(inventory(cache))
    with pytest.raises(ValidationError, match="ambiguous"):
        handoff.prepare(config, native)
    assert not Path(config["output_directory"]).exists()


def test_zero_exports_skip_validator_work(fixture):
    config, native = fixture
    for path in Path(config["raw_exports"]).iterdir():
        shutil.rmtree(path)
    config["raw_inventory_sha256"] = json_sha(inventory(Path(config["raw_exports"])))
    result = handoff.prepare(config, native)
    assert result["state"] == "zero_exports" and result["task_count"] == 0
    manifest = read_json(Path(config["output_directory"]) / "handoff/validation-manifest.json")
    assert manifest["exports"] == []


def test_policy_change_cannot_reuse_completed_export(fixture):
    config, native = fixture
    handoff.prepare(config, native)
    config = deepcopy(config)
    config["validation_template"]["max_cpu_hours_per_task"] = 7
    with pytest.raises(ValidationError, match="different inputs"):
        handoff.prepare(config, native)


@pytest.mark.parametrize("target", ["tests/test.sh", "task.toml"])
def test_rejects_grading_drift_before_publication(fixture, target):
    config, native = fixture
    original = inventory(Path(config["raw_exports"]))

    def drift(stage):
        if stage == "after_native_export":
            path = (
                Path(config["output_directory"]) / "staging/prepared/synthetic__fixture-1" / target
            )
            text = path.read_text()
            changed = (
                text.replace("timeout_sec = 300", "timeout_sec = 301")
                if target == "task.toml"
                else "changed grading assets"
            )
            assert changed != text
            path.write_text(changed)

    with pytest.raises(ValidationError, match="grading"):
        handoff.prepare(config, native, drift)
    assert not (Path(config["output_directory"]) / "handoff").exists()
    assert inventory(Path(config["raw_exports"])) == original
    assert handoff.prepare(config, native)["state"] == "prepared"
