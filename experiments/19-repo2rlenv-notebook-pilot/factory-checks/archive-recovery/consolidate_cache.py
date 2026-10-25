"""Consolidate equal immutable archive-cache files without changing payloads.

The downloader already uses hardlinks within one archive. This maintenance step
extends that representation across independently verified completed archives.
Original remote objects, manifests, readback receipts and all file paths remain.
"""

import argparse
import hashlib
import json
import os
import stat
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from readback_cache import identity, verify_local


def collect(archives):
    groups = defaultdict(list)
    manifests = {}
    for root in sorted(archives.iterdir()):
        if root.is_symlink() or not root.is_dir() or not root.name.isdigit():
            continue
        receipt, manifest = root / "independent-readback.json", root / "sealed-manifest.json"
        if not receipt.is_file() or not manifest.is_file():
            continue
        proof = json.loads(receipt.read_text())
        if not proof.get("all_files_download_verified"):
            continue
        raw = manifest.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == proof["source_manifest_sha256"]
        files = root / "files"
        assert files.is_dir() and not files.is_symlink()
        manifests[root.name] = digest
        for row in json.loads(raw)["files"]:
            name = PurePosixPath(row["path"])
            assert not name.is_absolute() and ".." not in name.parts and str(name) == row["path"]
            if row["bytes"] < 1024 * 1024:
                continue
            path = files / name
            assert path.resolve().is_relative_to(files.resolve())
            assert not path.is_symlink()
            # An older explicitly evicted cache is not a materialized candidate.
            if not path.exists():
                continue
            current = path.stat()
            assert stat.S_ISREG(current.st_mode)
            assert current.st_size == row["bytes"] and stat.S_IMODE(current.st_mode) == row["mode"]
            groups[(current.st_dev, *identity(row))].append((path, row))
    return groups, manifests


def consolidate(paths, journal):
    """Verify each distinct inode, then atomically replace only equal copies."""
    canonical, row = paths[0]
    distinct = {}
    for path, entry in paths:
        if path.is_symlink():
            raise ValueError("Archive cache cannot contain symlinks")
        assert identity(entry) == identity(row)
        info = path.stat()
        distinct.setdefault((info.st_dev, info.st_ino), (path, info))
    if len(distinct) < 2:
        return 0
    # Every distinct original is checked against the sealed identity BEFORE
    # replacing any name. Matching a canonical alone is insufficient.
    for path, _ in distinct.values():
        verify_local(path, row)
    changed = 0
    source_info = canonical.stat()
    for destination, _ in paths[1:]:
        current = destination.stat()
        if (current.st_dev, current.st_ino) == (source_info.st_dev, source_info.st_ino):
            continue
        _, verified = distinct[(current.st_dev, current.st_ino)]
        assert (current.st_mtime_ns, current.st_size, current.st_mode) == (
            verified.st_mtime_ns,
            verified.st_size,
            verified.st_mode,
        )
        temporary = destination.with_name(".cache-link-" + uuid.uuid4().hex)
        record = {
            "destination": str(destination),
            "canonical": str(canonical),
            "temporary": str(temporary),
            **row,
        }
        journal.write(json.dumps({"action": "before_atomic_link", **record}) + "\n")
        journal.flush()
        os.fsync(journal.fileno())
        try:
            os.link(canonical, temporary)
            linked = temporary.stat()
            assert (linked.st_dev, linked.st_ino) == (source_info.st_dev, source_info.st_ino)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        journal.write(json.dumps({"action": "linked", **record}) + "\n")
        journal.flush()
        changed += 1
    verify_local(canonical, row)
    for path, _ in paths:
        current = path.stat()
        assert (current.st_dev, current.st_ino) == (source_info.st_dev, source_info.st_ino)
        assert current.st_size == row["bytes"] and stat.S_IMODE(current.st_mode) == row["mode"]
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.receipt.exists()
    groups, manifests = collect(args.archives)
    selected = [
        paths
        for paths in groups.values()
        if len({(p.stat().st_dev, p.stat().st_ino) for p, _ in paths}) > 1
    ]
    before = os.statvfs(args.archives)
    changed = 0
    if args.apply:
        journal_path = args.receipt.with_suffix(".journal.jsonl")
        with journal_path.open("x") as journal:
            for paths in selected:
                changed += consolidate(paths, journal)
    after = os.statvfs(args.archives)
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "manifest_hashes": manifests,
        "candidate_content_groups": len(selected),
        "candidate_paths": sum(len(p) for p in selected),
        "paths_consolidated": changed,
        "observed_filesystem_free_bytes_before": before.f_bavail * before.f_frsize,
        "observed_filesystem_free_bytes_after": after.f_bavail * after.f_frsize,
        "scope": "Task-owned immutable cache only; no manifest, original receipt, payload bytes or permissions changed. Remote objects untouched.",
        "scientific_or_model_execution": False,
    }
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "manifest_hashes"}), flush=True)


if __name__ == "__main__":
    main()
