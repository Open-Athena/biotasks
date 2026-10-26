"""Original fallback seals can price closed resources, never grant acceptance."""

import copy
import json

import pytest
from test_setup_replay_prefix import grading_evidence, module


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def snapshot_metadata(tmp_path, defect=None):
    archive = tmp_path / "archive"
    restored = archive / "snapshot-restored"
    transport = archive / "snapshot-transport"
    transport.mkdir(parents=True)
    manifest = {
        "source_quiescent": defect != "active_source",
        "files": [
            {"path": "pipeline.json", "bytes": 2, "sha256": module.digest(b"{}"), "mode": 384}
        ],
    }
    if defect == "duplicate_member":
        manifest["files"].append(copy.deepcopy(manifest["files"][0]))
    write(restored / "snapshot-files.json", manifest)
    raw = (restored / "snapshot-files.json").read_bytes()
    (transport / "snapshot-files.json").write_bytes(raw)
    (transport / "evidence.tar.gz").write_bytes(b"original transport bytes")
    seal = {
        "download_checked": defect != "unverified_transport",
        "files": [
            {
                "path": name,
                "bytes": (transport / name).stat().st_size,
                "sha256": module.digest((transport / name).read_bytes()),
                "mode": 384,
            }
            for name in ["snapshot-files.json", "evidence.tar.gz"]
        ],
    }
    write(transport / "export-manifest.json", seal)
    transport_raw = (transport / "export-manifest.json").read_bytes()
    (restored / "transport-export-manifest.json").write_bytes(transport_raw)
    readback = {
        "format": "quiescent-tar-v1",
        "all_snapshot_files_hash_size_mode_verified": defect != "incomplete_readback",
        "source_manifest_sha256": module.digest(raw),
        "transport_manifest_sha256": module.digest(transport_raw),
        "file_count": len(manifest["files"]) + int(defect == "wrong_count"),
        "bytes": sum(row["bytes"] for row in manifest["files"]),
    }
    write(restored / "snapshot-readback.json", readback)
    write(
        archive / "failure-archive-readback.json",
        {
            "snapshot": readback,
            "ordinary_autonomous_export_seal_reconstructed": defect == "manufactured_seal",
            "originals_changed": defect == "modified_originals",
            "source_claim_sha256": "a" * 64,
            "original_bootstrap_sha256": "b" * 64,
        },
    )
    root = archive / "root-evidence"
    write(root / "sealed-root-manifest.json", {"files": []})
    write(
        root / "readback.json",
        {
            "all_manifest_files_hash_size_mode_verified": defect != "incomplete_root",
            "source_full_snapshot_manifest_sha256": module.digest(raw)
            if defect != "crosswired_root"
            else "c" * 64,
            "root_manifest_sha256": module.digest(
                (root / "sealed-root-manifest.json").read_bytes()
            ),
        },
    )
    if defect == "transport_changed":
        (transport / "evidence.tar.gz").write_bytes(b"different transport data")
    elif defect == "missing_transport":
        (transport / "evidence.tar.gz").unlink()
    elif defect == "linked_transport":
        path = transport / "evidence.tar.gz"
        data = path.read_bytes()
        path.unlink()
        (tmp_path / "outside").write_bytes(data)
        path.symlink_to(tmp_path / "outside")
    elif defect == "changed_manifest_copy":
        (transport / "snapshot-files.json").write_bytes(raw + b" ")
    return archive


def test_snapshot_reader_names_the_original_format_and_never_manufactures_a_regular_seal(tmp_path):
    archive = snapshot_metadata(tmp_path)
    root, rows, identity, proof = module.archive_inventory(archive, snapshot=True)
    assert root == archive / "snapshot-restored/files"
    assert set(rows) == {"pipeline.json"}
    assert identity == module.digest(
        (archive / "snapshot-restored/snapshot-files.json").read_bytes()
    )
    assert proof["source_claim_sha256"] == "a" * 64
    assert not (archive / "sealed-manifest.json").exists()
    with pytest.raises(FileNotFoundError):
        module.archive_inventory(archive)


@pytest.mark.parametrize(
    "defect",
    [
        "active_source",
        "duplicate_member",
        "unverified_transport",
        "incomplete_readback",
        "wrong_count",
        "manufactured_seal",
        "modified_originals",
        "incomplete_root",
        "crosswired_root",
        "transport_changed",
        "missing_transport",
        "linked_transport",
        "changed_manifest_copy",
    ],
)
def test_snapshot_requires_the_original_complete_bound_transport_and_root(tmp_path, defect):
    archive = snapshot_metadata(tmp_path, defect)
    with pytest.raises((AssertionError, FileNotFoundError)):
        module.archive_inventory(archive, snapshot=True)


def test_common_timeout_prices_only_the_same_four_nonoverlapping_closed_sdk_sessions():
    coarse, upper, records = module.audit(
        *grading_evidence("common_grading_failure"), profile="common_grading_failure"
    )
    assert len(records) == 4 and upper < 1 and coarse < 4


@pytest.mark.parametrize(
    "defect",
    ["rejected", "wrong_stage", "old_source", "extra_owner", "other_repair", "unclean", "overlap"],
)
def test_common_timeout_does_not_relax_source_status_resource_or_cleanup_guards(defect):
    pipeline, sources, claims, sessions, clean = grading_evidence("common_grading_failure")
    if defect == "rejected":
        pipeline["status"] = "rejected"
    elif defect == "wrong_stage":
        pipeline["failed_stage"] = "native"
    elif defect == "old_source":
        sources = dict(module.CURRENT_SPECIFICATION_SOURCES)
    elif defect == "extra_owner":
        claims["grading-comparison-repair"] = dict(claims["grading"])
    elif defect == "other_repair":
        pipeline["quality_repair"]["kind"] = "generated_construction"
    elif defect == "unclean":
        clean["original_all_cleanup_passed"] = False
    elif defect == "overlap":
        sessions["grading"]["started"] = sessions["materialization-raw"]["finished"] - 1
    with pytest.raises(AssertionError):
        module.audit(pipeline, sources, claims, sessions, clean, profile="common_grading_failure")
