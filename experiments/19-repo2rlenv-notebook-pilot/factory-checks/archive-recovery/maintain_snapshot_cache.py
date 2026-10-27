"""Reuse verified hardlink consolidation for a terminal original snapshot cache.

Operator storage maintenance only. The original snapshot reader and atomic link
helper remain unchanged; no regular export seal, task or scientific result is
created. Every original member is checked before and after the operation.
"""

import argparse
import hashlib
import importlib.util
import json
import shutil
import stat
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from consolidate_cache import consolidate
from readback_cache import identity, verify_local


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_inventory(archive):
    experiment = Path(__file__).resolve().parents[2]
    reader_path = experiment / "panel-rounds/079/reconcile_setup_replay_prefix.py"
    spec = importlib.util.spec_from_file_location("original_snapshot_inventory", reader_path)
    assert spec is not None and spec.loader is not None
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    files, rows, manifest_hash, proof = reader.archive_inventory(archive, snapshot=True)
    assert proof is not None and archive.name.isdigit()
    base = archive.parent.parent
    claim_path = base / f"launch/{int(archive.name):03}-submission.json"
    claim = json.loads(claim_path.read_text())
    assert digest(claim_path) == proof["source_claim_sha256"]
    assert proof["original_bootstrap_sha256"] == claim["inputs"]["files"]["bootstrap.py"]
    observations = [
        json.loads(path.read_text())
        for path in (base / "launch/typed-observations").glob(f"{int(archive.name):03}-*.json")
    ]
    terminal = max(observations, key=lambda row: row["observed_at"])
    assert terminal["terminal"] and terminal["state"] in {
        "SUCCEEDED",
        "FAILED",
        "KILLED",
        "WORKER_FAILED",
        "UNSCHEDULABLE",
    }
    assert terminal["claim_sha256"] == digest(claim_path)
    cleanup_path = archive / "fresh-provider-cleanup.json"
    cleanup = json.loads(cleanup_path.read_text())
    assert cleanup["complete"] and cleanup["original_all_cleanup_passed"]
    assert cleanup["fresh_original_ids_absent"] and not cleanup["sandboxes"]
    assert cleanup["source_snapshot_manifest_sha256"] == manifest_hash
    assert not (archive / "sealed-manifest.json").exists()
    seals = [
        archive / "failure-archive-readback.json",
        archive / "snapshot-restored/snapshot-files.json",
        archive / "snapshot-restored/snapshot-readback.json",
        archive / "snapshot-restored/transport-export-manifest.json",
        archive / "snapshot-transport/export-manifest.json",
        archive / "snapshot-transport/snapshot-files.json",
        archive / "root-evidence/sealed-root-manifest.json",
        archive / "root-evidence/readback.json",
        cleanup_path,
        claim_path,
    ]
    return files, rows, manifest_hash, {str(path): digest(path) for path in seals}, reader_path


def verify_members(files, rows):
    groups = defaultdict(list)
    for name, row in rows.items():
        relative = PurePosixPath(name)
        assert str(relative) == name and not relative.is_absolute() and ".." not in relative.parts
        path = files / relative
        assert path.resolve().is_relative_to(files.resolve())
        assert not any(parent.is_symlink() for parent in [path, *path.parents])
        verify_local(path, row)
        if row["bytes"] >= 1024 * 1024:
            current = path.stat()
            assert stat.S_ISREG(current.st_mode)
            groups[(current.st_dev, *identity(row))].append((path, row))
    return [
        paths
        for paths in groups.values()
        if len({(path.stat().st_dev, path.stat().st_ino) for path, _ in paths}) > 1
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    assert not args.receipt.exists() and (not args.apply or args.journal is not None)
    files, rows, manifest_hash, seals, reader_path = original_inventory(args.archive)
    groups = verify_members(files, rows)
    before = shutil.disk_usage(args.archive).free
    changed = 0
    if args.apply:
        with args.journal.open("x") as journal:
            for paths in groups:
                changed += consolidate(paths, journal)
    verify_members(files, rows)
    assert all(digest(Path(path)) == expected for path, expected in seals.items())
    assert not (args.archive / "sealed-manifest.json").exists()
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "source_archive_manifest_sha256": manifest_hash,
        "file_count": len(rows),
        "member_bytes": sum(row["bytes"] for row in rows.values()),
        "all_original_members_hash_size_mode_verified_before_and_after": True,
        "original_metadata_hashes_unchanged": seals,
        "candidate_content_groups": len(groups),
        "candidate_paths": sum(len(paths) for paths in groups),
        "paths_consolidated": changed,
        "filesystem_free_bytes_before": before,
        "filesystem_free_bytes_after": shutil.disk_usage(args.archive).free,
        "journal_path": str(args.journal) if args.apply else None,
        "journal_sha256": digest(args.journal) if args.apply else None,
        "helper_sha256": digest(Path(__file__)),
        "existing_inventory_reader_sha256": digest(reader_path),
        "existing_link_helper_sha256": digest(Path(__file__).with_name("consolidate_cache.py")),
        "scope": "Verified terminal immutable snapshot cache only; every path, byte, permission, original receipt and remote object is retained. No regular seal reconstructed.",
        "scientific_or_model_execution": False,
        "new_jobs_or_sandboxes": 0,
    }
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key != "original_metadata_hashes_unchanged"
            }
        )
    )


if __name__ == "__main__":
    main()
