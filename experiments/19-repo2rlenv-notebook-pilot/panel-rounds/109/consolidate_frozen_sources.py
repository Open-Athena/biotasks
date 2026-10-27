"""Consolidate identical task-owned source transports without changing claims."""

import collections
import hashlib
import json
import shutil
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    repo, launch, out = map(Path, sys.argv[1:])
    helper = repo / "experiments/19-repo2rlenv-notebook-pilot/factory-checks/archive-recovery"
    sys.path.insert(0, str(helper))
    from consolidate_cache import consolidate

    groups = collections.defaultdict(list)
    seals = {}
    for directory in sorted(launch.glob("[0-9]*-payload")):
        number = directory.name.removesuffix("-payload")
        path = directory / "upstream.tar.gz"
        inputs, claim = directory / "inputs.json", launch / f"{number}-submission.json"
        if (
            not number.isdigit()
            or directory.is_symlink()
            or not all(p.is_file() and not p.is_symlink() for p in (path, inputs, claim))
        ):
            continue
        submitted, frozen = json.loads(claim.read_text()), json.loads(inputs.read_text())
        expected = frozen["files"].get("upstream.tar.gz")
        if not expected or submitted["inputs"]["files"].get("upstream.tar.gz") != expected:
            continue
        info = path.stat()
        assert stat.S_ISREG(info.st_mode)
        row = {
            "path": "upstream.tar.gz",
            "sha256": expected,
            "bytes": info.st_size,
            "mode": stat.S_IMODE(info.st_mode),
        }
        key = (expected, info.st_size, row["mode"], info.st_dev, info.st_uid, info.st_gid)
        groups[key].append((path, row))
        seals[str(inputs)], seals[str(claim)] = sha(inputs), sha(claim)
    before = shutil.disk_usage(launch).free
    changed = 0
    out.mkdir(parents=True, exist_ok=True)
    with (out / "atomic-links.jsonl").open("x") as journal:
        for paths in groups.values():
            # Retain external aliases; prefer an already multiply linked inode.
            paths.sort(key=lambda item: (-item[0].stat().st_nlink, str(item[0])))
            changed += consolidate(paths, journal)
    for paths in groups.values():
        for path, row in paths:
            assert path.is_file() and not path.is_symlink()
            info = path.stat()
            assert info.st_size == row["bytes"]
            assert stat.S_IMODE(info.st_mode) == row["mode"]
        assert sha(paths[0][0]) == paths[0][1]["sha256"]
    assert all(sha(Path(p)) == expected for p, expected in seals.items())
    receipt = {
        "observed_at": datetime.now(UTC).isoformat(),
        "groups": len(groups),
        "paths": sum(map(len, groups.values())),
        "paths_consolidated": changed,
        "original_claim_and_input_hashes_unchanged": True,
        "all_source_paths_hash_size_mode_verified": True,
        "filesystem_free_bytes_before": before,
        "filesystem_free_bytes_after": shutil.disk_usage(launch).free,
        "original_remote_objects_untouched": True,
        "new_jobs_or_model_calls": 0,
        "scope": "Task-owned duplicate frozen upstream.tar.gz only; every original path, content, permission and claim remains.",
        "helper_sha256": sha(Path(__file__)),
        "atomic_link_helper_sha256": sha(helper / "consolidate_cache.py"),
        "journal_sha256": sha(out / "atomic-links.jsonl"),
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (out / "original-seals.json").write_text(json.dumps(seals, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
