"""Real local snapshot roundtrips and refusals, with no science or cloud calls."""

import importlib.util
import json
from pathlib import Path

import pytest
from iris_bootstrap import restore_snapshot, snapshot

spec = importlib.util.spec_from_file_location(
    "snapshot109_archive", Path(__file__).with_name("snapshot_archive.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    source, transport, restored = [tmp_path / name for name in ("source", "transport", "restored")]
    source.mkdir()
    transport.mkdir()
    (source / "native").mkdir()
    (source / "pipeline.json").write_text(json.dumps({"status": "rejected"}))
    (source / "native/result.json").write_text(json.dumps({"status": "not_run"}))
    (source / "pipeline.json").chmod(0o640)
    snapshot(source, transport.as_uri())
    readback = restore_snapshot(transport, restored)
    # The authenticated cache protects downloads independently of archive modes.
    for path in transport.iterdir():
        path.chmod(0o600)
    bootstrap, claim, recovery = [
        tmp_path / name for name in ("bootstrap.py", "claim.json", "recovery.json")
    ]
    bootstrap.write_text("# fixture controller source\n")
    claim.write_text(json.dumps({"inputs": {"files": {"bootstrap.py": module.digest(bootstrap)}}}))
    recovery.write_text(
        json.dumps(
            {
                "snapshot": readback,
                "source_claim_sha256": module.digest(claim),
                "original_bootstrap_sha256": module.digest(bootstrap),
            }
        )
    )
    return dict(
        restored=restored, transport=transport, recovery=recovery, claim=claim, bootstrap=bootstrap
    )


def test_original_two_level_archive_provenance_without_a_synthetic_seal(tmp_path):
    args = fixture(tmp_path)
    result = module.verify_snapshot_archive(**args)
    assert result.read_json("pipeline.json") == {"status": "rejected"}
    assert result.evidence["archive_format"] == "original-snapshot-v1"
    assert result.evidence["original_per_file_seal_reconstructed"] is False
    assert result.evidence["file_count"] == 2
    assert not (args["restored"] / "export-manifest.json").exists()
    assert "no scientific acceptance" in result.evidence["scope"]


@pytest.mark.parametrize(
    "change",
    [
        "tar",
        "transport_manifest",
        "member_manifest",
        "copied_seal",
        "member",
        "missing_member",
        "extra_member",
        "symlink_member",
        "member_mode",
        "readback",
        "recovery",
        "claim",
        "bootstrap",
    ],
)
def test_incomplete_changed_or_substituted_snapshot_is_refused(tmp_path, change):
    args = fixture(tmp_path)
    root = args["restored"]
    member = root / "files/pipeline.json"
    if change == "tar":
        with (args["transport"] / "evidence.tar.gz").open("ab") as stream:
            stream.write(b"changed")
    elif change == "transport_manifest":
        path = args["transport"] / "export-manifest.json"
        value = json.loads(path.read_text())
        value["download_checked"] = False
        path.write_text(json.dumps(value))
    elif change == "member_manifest":
        with (root / "snapshot-files.json").open("a") as stream:
            stream.write(" ")
    elif change == "copied_seal":
        (root / "transport-export-manifest.json").write_text("{}")
    elif change == "member":
        member.write_text("{}")
    elif change == "missing_member":
        member.unlink()
    elif change == "extra_member":
        (root / "files/unexpected.txt").write_text("extra")
    elif change == "symlink_member":
        outside = tmp_path / "outside.json"
        member.rename(outside)
        member.symlink_to(outside)
    elif change == "member_mode":
        member.chmod(0o600)
    elif change == "readback":
        path = root / "snapshot-readback.json"
        value = json.loads(path.read_text())
        value["file_count"] += 1
        path.write_text(json.dumps(value))
    elif change == "recovery":
        value = json.loads(args["recovery"].read_text())
        value["source_claim_sha256"] = "a" * 64
        args["recovery"].write_text(json.dumps(value))
    elif change == "claim":
        with args["claim"].open("a") as stream:
            stream.write(" ")
    else:
        args["bootstrap"].write_text("# another controller\n")
    with pytest.raises(ValueError):
        module.verify_snapshot_archive(**args)


def test_later_record_changes_and_unrecorded_paths_are_refused(tmp_path):
    args = fixture(tmp_path)
    archive = module.verify_snapshot_archive(**args)
    with pytest.raises(ValueError, match="absent"):
        archive.read_json("../claim.json")
    (archive.root / "pipeline.json").write_text("{}")
    with pytest.raises(ValueError, match="identity mismatch"):
        archive.read_json("pipeline.json")


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../b", "a\\b", "", "."])
def test_unsafe_inventory_identity_is_refused(name):
    with pytest.raises(ValueError):
        module.inventory({"files": [{"path": name, "bytes": 1, "mode": 0o600, "sha256": "a" * 64}]})
