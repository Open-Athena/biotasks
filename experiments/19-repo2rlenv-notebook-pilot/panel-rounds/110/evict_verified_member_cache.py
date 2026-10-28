"""Evict only byte-identical restored caches; retain original compressed evidence."""

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(base, number):
    archive = base / f"archives/{number:03}"
    transport = archive / "snapshot-transport"
    restored = archive / "snapshot-restored"
    cache = restored / "files"
    assert archive.resolve().is_relative_to(base.resolve())
    assert not archive.is_symlink() and not restored.is_symlink()
    assert cache.is_dir() and not cache.is_symlink()
    assert cache.resolve() == archive.resolve() / "snapshot-restored/files"
    claim = base / f"launch/{number:03}-submission.json"
    observations = [
        read(path) for path in (base / "launch/typed-observations").glob(f"{number:03}-*.json")
    ]
    terminal = max(observations, key=lambda row: row["observed_at"])
    assert terminal["terminal"] is True
    assert terminal["state"] in {"SUCCEEDED", "FAILED", "KILLED", "WORKER_FAILED", "UNSCHEDULABLE"}
    assert terminal["claim_sha256"] == digest(claim)
    clean = read(archive / "fresh-provider-cleanup.json")
    assert clean["complete"] and clean["fresh_original_ids_absent"] and not clean["sandboxes"]
    recovery = read(archive / "failure-archive-readback.json")
    assert recovery["source_claim_sha256"] == digest(claim)
    assert (
        clean["source_snapshot_manifest_sha256"] == recovery["snapshot"]["source_manifest_sha256"]
    )
    assert recovery["snapshot"] == read(restored / "snapshot-readback.json")
    assert recovery["snapshot"]["all_snapshot_files_hash_size_mode_verified"] is True
    manifest_path = transport / "export-manifest.json"
    assert manifest_path.read_bytes() == (restored / "transport-export-manifest.json").read_bytes()
    assert digest(manifest_path) == recovery["snapshot"]["transport_manifest_sha256"]
    seal = read(manifest_path)
    assert seal["download_checked"] is True
    assert {row["path"] for row in seal["files"]} == {"snapshot-files.json", "evidence.tar.gz"}
    assert len(seal["files"]) == 2
    for row in seal["files"]:
        path = transport / row["path"]
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"]
    members_path = restored / "snapshot-files.json"
    assert members_path.read_bytes() == (transport / "snapshot-files.json").read_bytes()
    assert digest(members_path) == recovery["snapshot"]["source_manifest_sha256"]
    manifest = read(members_path)
    assert manifest["source_quiescent"] is True
    members = {row["path"]: row for row in manifest["files"]}
    assert len(members) == len(manifest["files"]) == recovery["snapshot"]["file_count"]
    actual = set()
    for path in cache.rglob("*"):
        assert not path.is_symlink()
        if path.is_dir():
            continue
        assert path.is_file()
        name = path.relative_to(cache).as_posix()
        row = members[name]
        assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"]
        assert path.stat().st_mode & 0o777 == row["mode"]
        actual.add(name)
    assert actual == set(members)
    bootstrap = base / f"launch/{number:03}-payload/bootstrap.py"
    assert digest(bootstrap) == read(claim)["inputs"]["files"]["bootstrap.py"]
    assert recovery["original_bootstrap_sha256"] == digest(bootstrap)
    return {
        "campaign": number,
        "member_files_verified": len(members),
        "member_bytes_verified": sum(row["bytes"] for row in members.values()),
        "member_manifest_sha256": digest(members_path),
        "transport_manifest_sha256": digest(manifest_path),
        "retained_compressed_bytes": (transport / "evidence.tar.gz").stat().st_size,
        "retained_compressed_sha256": digest(transport / "evidence.tar.gz"),
        "cache_relative_path": cache.relative_to(base).as_posix(),
        "original_bootstrap_sha256": digest(bootstrap),
        "terminal_state": terminal["state"],
        "fresh_cleanup_verified": True,
        "member_cache_removed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("numbers", type=int, nargs="+")
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.proof.exists() and not args.proof.is_symlink()
    assert len(set(args.numbers)) == len(args.numbers)
    records = [verify(args.private_root, number) for number in args.numbers]
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "cache_eviction_complete": False,
        "helper_sha256": digest(Path(__file__)),
        "free_bytes_before": shutil.disk_usage(args.private_root).free,
        "records": records,
        "scope": "Restorable local member caches only. Original compressed transports, manifests, readback/cleanup receipts, source bootstrap and remote objects remain. No scientific or budget change, new model/provider call or ordinary archive-seal reconstruction.",
        "rehydration": "Verify the retained original transport and bootstrap hashes, use that submission-bound bootstrap's restore_snapshot into a fresh sibling directory, verify its readback equals the retained original, and move only its files directory back to the canonical cache path. Retain the original metadata receipts unchanged.",
    }
    args.proof.write_text(json.dumps(result, indent=2) + "\n")
    if args.apply:
        for record in records:
            cache = args.private_root / record["cache_relative_path"]
            shutil.rmtree(cache)
            assert not cache.exists()
            assert (
                digest(
                    args.private_root
                    / f"archives/{record['campaign']:03}/snapshot-transport/evidence.tar.gz"
                )
                == record["retained_compressed_sha256"]
            )
            record["member_cache_removed"] = True
            args.proof.write_text(json.dumps(result, indent=2) + "\n")
    result["free_bytes_after"] = shutil.disk_usage(args.private_root).free
    result["cache_eviction_complete"] = args.apply and all(
        row["member_cache_removed"] for row in records
    )
    args.proof.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
