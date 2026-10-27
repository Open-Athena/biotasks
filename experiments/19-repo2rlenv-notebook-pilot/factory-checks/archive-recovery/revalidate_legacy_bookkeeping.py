"""Revalidate existing legacy snapshot caches and add derived readback metadata.

Original seals, scientific files and earlier operator receipts are preserved.
This is not scientific execution or reconstruction of a missing ordinary seal.
"""

import argparse
import hashlib
import importlib.util
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from rigging.filesystem.buckets import filesystem_for


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def owned_path(root, name):
    relative = PurePosixPath(name)
    assert not relative.is_absolute() and ".." not in relative.parts
    assert str(relative) == name and name != "."
    path = root / name
    assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    base = args.private_root
    archive = base / f"archives/{args.number:03}"
    recovery_path = archive / "failure-archive-readback.json"
    assert not recovery_path.exists()
    original_root_receipt = (archive / "root-evidence/readback.json").read_bytes()
    old_root = json.loads(original_root_receipt)
    prefix = old_root["source_root_prefix"]
    assert prefix.startswith("s3://marin-us-east-02a/marin/evals/biotasks19/")
    assert prefix.endswith(f"/biotasks19-autonomous-panel-{args.number:03}/")
    for relative, local in [
        ("export-manifest.json", archive / "root-evidence/sealed-root-manifest.json"),
        (
            "autonomous-snapshot/export-manifest.json",
            archive / "snapshot-transport/export-manifest.json",
        ),
    ]:
        fs, key = filesystem_for(prefix + relative)
        with fs.open(key, "rb", cache_type="none", block_size=1024 * 1024) as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        assert raw == local.read_bytes() and json.loads(raw)["download_checked"]
    root_raw = (archive / "root-evidence/sealed-root-manifest.json").read_bytes()
    root_manifest = json.loads(root_raw)
    assert hashlib.sha256(root_raw).hexdigest() == old_root["root_manifest_sha256"]
    for row in root_manifest["files"]:
        path = owned_path(archive / "root-evidence/files", row["path"])
        assert not path.is_symlink() and path.stat().st_size == row["bytes"]
        assert path.stat().st_mode & 0o777 == row["mode"] and digest(path) == row["sha256"]
    claim_raw = (base / f"launch/{args.number:03}-submission.json").read_bytes()
    claim = json.loads(claim_raw)
    bootstrap = base / f"launch/{args.number:03}-payload/bootstrap.py"
    assert digest(bootstrap) == claim["inputs"]["files"]["bootstrap.py"]
    transport = archive / "snapshot-transport"
    snapshot_manifest = json.loads((transport / "snapshot-files.json").read_text())
    required = sum(row["bytes"] for row in snapshot_manifest["files"])
    assert shutil.disk_usage(archive).free - required >= 2 * 1024**3
    fresh = archive / "operator-revalidated-snapshot"
    assert not fresh.exists()
    spec = importlib.util.spec_from_file_location("original_legacy_snapshot_bootstrap", bootstrap)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    snapshot = module.restore_snapshot(transport, fresh)
    assert snapshot == json.loads(
        (archive / "snapshot-restored/snapshot-readback.json").read_text()
    )
    original = archive / "snapshot-restored/files"
    restored_paths = []
    for row in snapshot_manifest["files"]:
        path = owned_path(original, row["path"])
        source = owned_path(fresh / "files", row["path"])
        assert not path.is_symlink()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.hardlink_to(source)
            restored_paths.append(row["path"])
        assert path.stat().st_size == row["bytes"]
        assert path.stat().st_mode & 0o777 == row["mode"] and digest(path) == row["sha256"]
    pipeline = json.loads((original / "pipeline.json").read_text())
    assert pipeline["factory_revision"] == claim["factory_revision"]
    history = archive / "operator-readback-history"
    history.mkdir(exist_ok=True)
    old_hash = hashlib.sha256(original_root_receipt).hexdigest()
    preserved = history / (old_hash + ".json")
    if preserved.exists():
        assert preserved.read_bytes() == original_root_receipt
    else:
        preserved.write_bytes(original_root_receipt)
    assert preserved.read_bytes() == original_root_receipt
    root_receipt = {
        **old_root,
        "observed_at": datetime.now(UTC).isoformat(),
        "file_count": len(root_manifest["files"]),
        "files": root_manifest["files"],
        "source_full_snapshot_manifest_sha256": snapshot["source_manifest_sha256"],
        "previous_operator_readback_sha256": old_hash,
        "scope": "Derived operator revalidation of unchanged original root seal/files and snapshot; prior operator receipt preserved. No scientific artifact or original seal changed.",
    }
    (archive / "root-evidence/readback.json").write_text(json.dumps(root_receipt, indent=2) + "\n")
    record = {
        "observed_at": datetime.now(UTC).isoformat(),
        "campaign": args.number,
        "source_claim_sha256": hashlib.sha256(claim_raw).hexdigest(),
        "original_bootstrap_sha256": digest(bootstrap),
        "snapshot": snapshot,
        "root_files": root_receipt["file_count"],
        "root_bytes": root_receipt["bytes"],
        "remote_original_seals_freshly_matched": True,
        "ordinary_autonomous_export_seal_reconstructed": False,
        "originals_changed": False,
        "derived_operator_bookkeeping_added": True,
        "previous_operator_root_readback_sha256": old_hash,
        "evicted_cache_paths_rehydrated": restored_paths,
        "new_hosts_models_sandboxes": 0,
        "scope": "Revalidated legacy readback using original submitted bootstrap and unchanged remote seals. Original scientific files, seals and prior operator receipt preserved.",
    }
    recovery_path.write_text(json.dumps(record, indent=2) + "\n")
    assert json.loads(recovery_path.read_text()) == record
    shutil.rmtree(fresh)
    assert not fresh.exists()
    print(json.dumps({k: v for k, v in record.items() if k != "evicted_cache_paths_rehydrated"}))


if __name__ == "__main__":
    main()
