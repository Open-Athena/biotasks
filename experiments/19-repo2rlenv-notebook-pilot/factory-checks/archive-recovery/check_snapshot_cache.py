"""Independently rehash an original snapshot after cache maintenance.

Uses only the retained original manifests and the Python standard library; it
does not import the maintenance, linking or archive-inventory implementations.
"""

import hashlib
import json
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

archive, applied_path, output = map(Path, sys.argv[1:])
assert not output.exists()
applied = json.loads(applied_path.read_text())
manifest_raw = (archive / "snapshot-restored/snapshot-files.json").read_bytes()
assert hashlib.sha256(manifest_raw).hexdigest() == applied["source_archive_manifest_sha256"]
manifest = json.loads(manifest_raw)
assert manifest["source_quiescent"] is True
files = archive / "snapshot-restored/files"
observed = {}
seen = set()
for row in manifest["files"]:
    name = PurePosixPath(row["path"])
    assert not name.is_absolute() and ".." not in name.parts and str(name) not in seen
    seen.add(str(name))
    path = files / name
    assert path.resolve().is_relative_to(files.resolve())
    assert not any(parent.is_symlink() for parent in [path, *path.parents])
    info = path.stat()
    assert stat.S_ISREG(info.st_mode)
    assert info.st_size == row["bytes"] and stat.S_IMODE(info.st_mode) == row["mode"]
    key = info.st_dev, info.st_ino
    if key not in observed:
        with path.open("rb") as stream:
            observed[key] = hashlib.file_digest(stream, "sha256").hexdigest()
    assert observed[key] == row["sha256"]
for name, expected in applied["original_metadata_hashes_unchanged"].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
transport = archive / "snapshot-transport"
for row in json.loads((transport / "export-manifest.json").read_text())["files"]:
    path = transport / row["path"]
    assert path.stat().st_size == row["bytes"]
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"]
assert not (archive / "sealed-manifest.json").exists()
result = {
    "observed_at": datetime.now(UTC).isoformat(),
    "source_archive_manifest_sha256": applied["source_archive_manifest_sha256"],
    "all_member_paths_hash_size_mode_verified": True,
    "member_paths_checked": len(seen),
    "physical_member_hashes_checked": len(observed),
    "original_metadata_hashes_unchanged": True,
    "original_compressed_transport_verified": True,
    "regular_export_seal_reconstructed": False,
    "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "scientific_or_model_execution": False,
}
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
