"""An autonomous release label requires source-bound archived execution evidence."""

import hashlib
import json

import pytest
from release_metadata import release_execution_provenance


def fixture(tmp_path):
    seed = {"id": "fixture", "source_sha256": "a" * 64}
    pipeline = {
        "source": seed,
        "status": "validated",
        "autonomous": True,
        "operator_interventions": 0,
        "factory_revision": "b" * 40,
        "reasoning_effort_requested": "high",
        "served_endpoint_effective_effort_verified": False,
        "stages": [
            {"name": name, "status": "completed"}
            for name in [
                "preparation",
                "setup",
                "replay",
                "specification",
                "construction",
                "grading",
                "native",
            ]
        ],
    }
    native = tmp_path / "native"
    native.mkdir()
    (tmp_path / "pipeline.json").write_text(json.dumps(pipeline))
    (tmp_path / "seed.json").write_text(json.dumps([seed]))
    (native / "result.json").write_text(
        json.dumps(
            {"status": "native_validated_solver_attempt_recorded", "publication_ready": True}
        )
    )
    refresh_manifest(tmp_path)
    config = {
        "autonomous_pipeline": str(tmp_path / "pipeline.json"),
        "autonomous_archive_manifest": str(tmp_path / "export-manifest.json"),
        "native": str(native),
        "release_metadata": {"seed_file": str(tmp_path / "seed.json")},
    }
    return config, {"accepted": True, "bundle_hash": "sha256:" + "c" * 64}


def refresh_manifest(root):
    rows = []
    for name in ("pipeline.json", "native/result.json"):
        raw = (root / name).read_bytes()
        rows.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    (root / "export-manifest.json").write_text(
        json.dumps({"files": rows, "download_checked": True})
    )


def test_legacy_release_remains_assisted():
    assert release_execution_provenance({}, {"accepted": True}) == ("assisted", {})


def test_archived_unattended_source_is_labeled_and_explained(tmp_path):
    config, validation = fixture(tmp_path)
    provenance, documents = release_execution_provenance(config, validation)
    assert provenance == "unattended"
    evidence = documents["autonomous-execution.json"]
    assert evidence["bundle_hash"] == validation["bundle_hash"]
    assert evidence["source_sha256"] == "a" * 64
    assert evidence["operator_interventions"] == 0
    assert evidence["served_endpoint_effective_effort_verified"] is False


@pytest.mark.parametrize("name", ["pipeline.json", "native/result.json"])
def test_changed_archived_record_blocks_unattended_label(tmp_path, name):
    config, validation = fixture(tmp_path)
    with (tmp_path / name).open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="differs from its archive"):
        release_execution_provenance(config, validation)


def test_different_release_seed_cannot_borrow_pipeline_provenance(tmp_path):
    config, validation = fixture(tmp_path)
    (tmp_path / "seed.json").write_text(json.dumps([{"source_sha256": "d" * 64}]))
    with pytest.raises(ValueError, match="different release source"):
        release_execution_provenance(config, validation)


@pytest.mark.parametrize("interventions", [1, False, None])
def test_operator_edits_or_missing_intervention_record_block_label(tmp_path, interventions):
    config, validation = fixture(tmp_path)
    path = tmp_path / "pipeline.json"
    pipeline = json.loads(path.read_text())
    pipeline["operator_interventions"] = interventions
    path.write_text(json.dumps(pipeline))
    refresh_manifest(tmp_path)
    with pytest.raises(ValueError, match="completed unattended pipeline"):
        release_execution_provenance(config, validation)


def test_missing_stage_is_not_a_completed_autonomous_pipeline(tmp_path):
    config, validation = fixture(tmp_path)
    path = tmp_path / "pipeline.json"
    pipeline = json.loads(path.read_text())
    pipeline["stages"].pop(1)
    path.write_text(json.dumps(pipeline))
    refresh_manifest(tmp_path)
    with pytest.raises(ValueError, match="completed unattended pipeline"):
        release_execution_provenance(config, validation)


@pytest.mark.parametrize("defect", ["no-manifest", "no-pipeline", "unaccepted", "unchecked"])
def test_partial_or_unverified_evidence_is_not_unattended(tmp_path, defect):
    config, validation = fixture(tmp_path)
    if defect == "no-manifest":
        config.pop("autonomous_archive_manifest")
    elif defect == "no-pipeline":
        config.pop("autonomous_pipeline")
    elif defect == "unaccepted":
        validation["accepted"] = False
    else:
        p = tmp_path / "export-manifest.json"
        manifest = json.loads(p.read_text())
        manifest["download_checked"] = False
        p.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        release_execution_provenance(config, validation)
