"""Consolidate immutable publication evidence against its original archive cache.

Only completed publication records whose evidence manifest exactly matches the
independently downloaded original are eligible. Preserve every path, byte, mode,
manifest and receipt. Never use an active campaign's working files.
"""

import argparse
import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from consolidate_cache import collect, consolidate
from readback_cache import identity


def publication_views(publications, records, groups, manifests):
    included = {}
    for case in sorted(publications.iterdir()):
        if not case.is_dir() or case.is_symlink() or case.name not in manifests:
            continue
        receipt = records / case.name / "publication.json"
        if not receipt.is_file() or receipt.is_symlink():
            continue
        raw_receipt = receipt.read_bytes()
        if json.loads(raw_receipt).get("state") != "completed":
            continue
        for attempt in sorted(case.glob("attempt-*")):
            assert attempt.is_dir() and not attempt.is_symlink()
            files = attempt / "evidence"
            manifest = files / "export-manifest.json"
            if not manifest.is_file():
                continue
            assert not files.is_symlink() and not manifest.is_symlink()
            raw = manifest.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            assert digest == manifests[case.name], "Publication view differs from original seal"
            selected = 0
            for row in json.loads(raw)["files"]:
                if row["bytes"] < 1024 * 1024:
                    continue
                name = PurePosixPath(row["path"])
                assert not name.is_absolute() and ".." not in name.parts
                assert str(name) == row["path"]
                path = files / name
                assert not path.is_symlink() and path.resolve().is_relative_to(files.resolve())
                info = path.stat()
                assert stat.S_ISREG(info.st_mode)
                assert info.st_size == row["bytes"] and stat.S_IMODE(info.st_mode) == row["mode"]
                key = (info.st_dev, *identity(row))
                # Require a materialized original as the first/canonical path.
                assert key in groups and groups[key]
                groups[key].append((path, row))
                selected += 1
            included[str(files.relative_to(publications))] = {
                "original_manifest_sha256": digest,
                "completed_publication_receipt_sha256": hashlib.sha256(raw_receipt).hexdigest(),
                "large_paths": selected,
            }
    return included


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--publications", type=Path, required=True)
    parser.add_argument("--publication-records", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert not args.receipt.exists()
    groups, manifests = collect(args.archives)
    included = publication_views(args.publications, args.publication_records, groups, manifests)
    selected = [
        paths
        for paths in groups.values()
        if len({(path.stat().st_dev, path.stat().st_ino) for path, _ in paths}) > 1
    ]
    before = os.statvfs(args.archives)
    changed = 0
    if args.apply:
        with args.receipt.with_suffix(".journal.jsonl").open("x") as journal:
            for paths in selected:
                changed += consolidate(paths, journal)
    after = os.statvfs(args.archives)
    proof = {
        "observed_at": datetime.now(UTC).isoformat(),
        "applied": args.apply,
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "consolidation_helper_sha256": hashlib.sha256(
            Path(__file__).with_name("consolidate_cache.py").read_bytes()
        ).hexdigest(),
        "original_manifest_hashes": manifests,
        "publication_views": included,
        "candidate_groups": len(selected),
        "paths_consolidated": changed,
        "free_bytes_before": before.f_bavail * before.f_frsize,
        "free_bytes_after": after.f_bavail * after.f_frsize,
        "remote_objects_or_original_receipts_changed": False,
        "payload_bytes_modes_or_names_changed": False,
        "model_or_scientific_execution": False,
        "active_campaign_workspaces_used": False,
    }
    args.receipt.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({k: v for k, v in proof.items() if k != "original_manifest_hashes"}))


if __name__ == "__main__":
    main()
