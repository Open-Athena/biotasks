"""Original fallback seals can price closed resources, never grant acceptance."""

import copy
import json
from datetime import UTC, datetime
from decimal import Decimal

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


@pytest.mark.parametrize("defect", [None, "unverified", "wrong_hash", "duplicate", "root"])
def test_regular_original_inventory_keeps_its_own_readback_guards(tmp_path, defect):
    archive = tmp_path / "regular"
    row = {"path": "pipeline.json", "bytes": 2, "sha256": module.digest(b"{}"), "mode": 384}
    write(
        archive / "sealed-manifest.json", {"files": [row, row] if defect == "duplicate" else [row]}
    )
    raw = (archive / "sealed-manifest.json").read_bytes()
    write(
        archive / "independent-readback.json",
        {
            "all_files_download_verified": defect != "unverified",
            "source_manifest_sha256": "wrong" if defect == "wrong_hash" else module.digest(raw),
        },
    )
    write(
        archive / "root-evidence/readback.json",
        {
            "all_manifest_files_hash_size_mode_verified": defect != "root",
        },
    )
    if defect:
        with pytest.raises(AssertionError):
            module.archive_inventory(archive)
    else:
        root, rows, identity, extra = module.archive_inventory(archive)
        assert root == archive / "files" and set(rows) == {"pipeline.json"}
        assert identity == module.digest(raw) and extra is None
        assert not (archive / "snapshot-restored").exists()


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


def absence_evidence():
    pipeline, _, claims, sessions, clean = grading_evidence("common_grading_failure")
    clean.update(
        all_original_claim_ids_checked=True,
        fresh_original_ids_absent=True,
        original_sandbox_claims=list(claims.values()),
        observed_at=datetime.fromtimestamp(2000, UTC).isoformat(),
    )
    return pipeline, claims, sessions, clean


@pytest.mark.parametrize("regular", [False, True])
def test_uncertain_tail_prices_every_second_until_later_direct_absence_without_rewriting_clocks(
    regular,
):
    args = absence_evidence()
    if regular:
        args[3]["all_original_sdk_claim_ids_checked"] = args[3].pop(
            "all_original_claim_ids_checked"
        )
        args[3]["original_sdk_claims"] = args[3].pop("original_sandbox_claims")
    before = copy.deepcopy(args)
    added, rows = module.price_through_fresh_absence(*args, ["grading"])
    seconds = Decimal(2000) - Decimal(str(args[2]["grading"]["finished"]))
    assert added == seconds * module.RATE / 3600
    assert Decimal(rows["grading"]["additional_priced_seconds"]) == seconds
    assert args == before


@pytest.mark.parametrize("regular", [False, True])
@pytest.mark.parametrize(
    "defect",
    [
        "missing_id_check",
        "present_id",
        "missing_claim",
        "changed_claim",
        "duplicate_claim",
        "old_observation",
        "naive_clock",
        "unknown_folder",
        "duplicate_folder",
    ],
)
def test_late_absence_pricing_requires_all_bound_claims_and_an_actual_later_observation(
    defect, regular
):
    pipeline, claims, sessions, clean = absence_evidence()
    folders = ["grading"]
    if defect == "missing_id_check":
        clean["all_original_claim_ids_checked"] = False
    elif defect == "present_id":
        clean["fresh_original_ids_absent"] = False
    elif defect == "missing_claim":
        clean["original_sandbox_claims"] = clean["original_sandbox_claims"][:-1]
    elif defect == "changed_claim":
        clean["original_sandbox_claims"] = copy.deepcopy(clean["original_sandbox_claims"])
        clean["original_sandbox_claims"][0]["id"] = "other"
    elif defect == "duplicate_claim":
        clean["original_sandbox_claims"] = [clean["original_sandbox_claims"][0]] * 4
    elif defect == "old_observation":
        clean["observed_at"] = datetime.fromtimestamp(1, UTC).isoformat()
    elif defect == "naive_clock":
        clean["observed_at"] = "1970-01-01T00:33:20"
    elif defect == "unknown_folder":
        folders = ["other"]
    elif defect == "duplicate_folder":
        folders = ["grading", "grading"]
    if regular:
        clean["all_original_sdk_claim_ids_checked"] = clean.pop("all_original_claim_ids_checked")
        clean["original_sdk_claims"] = clean.pop("original_sandbox_claims")
    with pytest.raises(AssertionError):
        module.price_through_fresh_absence(pipeline, claims, sessions, clean, folders)


@pytest.mark.parametrize("defect", ["mixed", "partial", "unknown"])
def test_late_absence_evidence_does_not_mix_or_guess_claim_schemas(defect):
    pipeline, claims, sessions, clean = absence_evidence()
    if defect == "mixed":
        clean["all_original_sdk_claim_ids_checked"] = True
        clean["original_sdk_claims"] = clean["original_sandbox_claims"]
    elif defect == "partial":
        clean.pop("original_sandbox_claims")
    else:
        clean.pop("all_original_claim_ids_checked")
        clean.pop("original_sandbox_claims")
    with pytest.raises(AssertionError):
        module.price_through_fresh_absence(pipeline, claims, sessions, clean, ["grading"])


def test_tail_bound_retains_margin_and_rounding_and_never_exceeds_the_original_reservation():
    assert module.retain_extended_bound(Decimal(5), Decimal(1), Decimal("0.95")) == Decimal("1.25")
    assert module.retain_extended_bound(Decimal(5), Decimal(1), Decimal("0.4")) == Decimal(1)
    with pytest.raises(AssertionError):
        module.retain_extended_bound(Decimal(5), Decimal(1), Decimal("4.99"))
