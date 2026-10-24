"""Synthetic connector boundaries with the real local exporter/planner, no jobs."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from biotasks.validation import bridge, controller
from biotasks.validation.archives import pack
from biotasks.validation.files import ValidationError, inventory, read_json, sha

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
finish = __import__("finish_generation")


@pytest.fixture
def completed(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fixture_handoff", ROOT / "test_handoff.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config, native = module.fixture.__wrapped__(tmp_path)
    generation = tmp_path / "generation"
    generation.mkdir()
    source = generation / "runs/generation"
    shutil.copytree(Path(config["raw_exports"]), source / "generation-source/outputs/raw")
    shutil.copytree(
        Path(config["bootstrap_cache"]), source / "generation-source/upstream/workspace/bootstrap"
    )
    notices = tmp_path / "source-notices"
    notices.mkdir()
    (notices / "LICENSE").write_text("Synthetic interface fixture, not licensed external data\n")
    package = pack(notices, generation / "notices.tar.gz")
    package["path"] = "notices.tar.gz"
    plan = {
        "repo2rlenv_revision": finish.handoff.UPSTREAM,
        "backend": config["validation_template"]["backend"],
        "budget_ledger": config["validation_template"]["budget_ledger"],
        "archive": {"kind": "local"},
        "group": {
            "notices": package,
            "publication": {
                "eligible": True,
                "review": "Synthetic fixture source notices; no upload or execution",
            },
        },
    }
    readback = {
        "exported_tasks": ["synthetic__fixture-1"],
        "model_billing": {"known_actual_usd": "0.125", "calls": 1, "complete": True},
    }
    ready = {
        "state": "ready",
        "plan": plan,
        "readback": readback,
        "directory": source,
        "binding": {"synthetic_generation": "immutable"},
    }
    monkeypatch.setattr(finish, "generation_ready", lambda root: ready)
    monkeypatch.setattr(
        bridge,
        "call",
        lambda backend, request, log: (
            {"synthetic_fingerprint": True}
            if request["action"] == "fingerprint"
            else pytest.fail("No remote transport permitted")
        ),
    )
    monkeypatch.setattr(
        controller, "run", lambda root, once=False: {"state": "in_progress", "tasks": {}}
    )
    return generation, tmp_path / "connector", ready, native


def test_connector_freezes_distinct_execution_policy_without_mutating_handoff(
    completed, monkeypatch
):
    generation, output, ready, native = completed
    result = finish.execute(generation, output, once=True)
    assert result["state"] == "in_progress" and result["no_regeneration_or_repair"]
    base = output / "prepared-local/handoff/validation-manifest.json"
    before = sha(base)
    original = read_json(base)
    actual = read_json(output / "validation-execution-manifest.json")
    assert not original["exports"][0]["publication"]["eligible"]
    assert actual["exports"][0]["publication"]["eligible"] and actual["exports"][0]["notices"]
    assert Path(actual["exports"][0]["path"]).is_absolute()
    planned = controller.verify_plan(output / "validation")
    assert len(planned["tasks"]) == 1 and not planned["unsupported"]
    monkeypatch.setattr(
        native,
        "prepare_dataset_for_push",
        lambda *a, **k: pytest.fail("Completed local export must not rerun"),
    )
    assert finish.execute(generation, output, once=True)["state"] == "in_progress"
    assert sha(base) == before


def test_zero_exports_never_plan_or_submit_controls(completed, monkeypatch):
    generation, output, ready, native = completed
    ready["readback"]["exported_tasks"] = []
    monkeypatch.setattr(
        finish.handoff, "source_api", lambda *a, **k: pytest.fail("No preparation for zero exports")
    )
    monkeypatch.setattr(
        controller, "run", lambda *a, **k: pytest.fail("No controls for zero exports")
    )
    result = finish.execute(generation, output)
    assert result["state"] == "zero_exports" and result["native_control_jobs"] == 0
    assert not (output / "validation").exists()


def test_changed_generation_binding_cannot_resume_validation(completed):
    generation, output, ready, native = completed
    finish.execute(generation, output, once=True)
    ready["binding"] = {"synthetic_generation": "changed"}
    with pytest.raises(ValidationError, match="identity changed"):
        finish.execute(generation, output, once=True)


def test_existing_generation_wait_is_read_only_and_never_drives_another_job(tmp_path, monkeypatch):
    generation, output = tmp_path / "pending", tmp_path / "connector"
    generation.mkdir()
    monkeypatch.setattr(
        finish.run_generation,
        "verify",
        lambda root: {"group": {"id": "generation", "run_id": "fixed-existing"}},
    )
    monkeypatch.setattr(
        finish,
        "GenerationPipeline",
        lambda *a, **k: pytest.fail("Do not advance an incomplete generator from connector"),
    )
    result = finish.execute(generation, output)
    assert result["state"] == "waiting_for_existing_generation"
    assert not output.exists()


def test_modified_extracted_raw_source_is_not_accepted_as_a_new_input(tmp_path):
    directory = tmp_path / "generation-source"
    directory.mkdir()
    source = directory / "original.txt"
    source.write_text("original recorded output")
    readback = {
        "source_members": [{**row, "mode": int(row["mode"], 8)} for row in inventory(directory)]
    }
    finish.verify_generation_source(tmp_path, readback)
    source.write_text("changed output")
    with pytest.raises(ValidationError, match="lineage differs"):
        finish.verify_generation_source(tmp_path, readback)
