"""Verify original snapshot provenance without manufacturing a per-file seal.

Operator-side archive verification only. Scientific/native acceptance and
redistribution decisions remain separate gates.
"""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Snapshot evidence must be a regular original file")
    return path


def inventory(manifest):
    rows = {}
    for row in manifest["files"]:
        name = row["path"]
        path = PurePosixPath(name)
        if (
            not name
            or not path.parts
            or path.is_absolute()
            or path.as_posix() != name
            or ".." in path.parts
            or "\\" in name
            or "\x00" in name
            or name in rows
            or type(row["bytes"]) is not int
            or row["bytes"] < 0
            or type(row["mode"]) is not int
            or not 0 <= row["mode"] <= 0o777
            or not re.fullmatch("[0-9a-f]{64}", row["sha256"])
        ):
            raise ValueError("Invalid or duplicate original snapshot identity")
        rows[name] = row
    if not rows:
        raise ValueError("Original snapshot has no files")
    return rows


def check_file(path, row, *, mode=True):
    regular(path)
    if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
        raise ValueError("Snapshot original identity mismatch")
    if mode and path.stat().st_mode & 0o777 != row["mode"]:
        raise ValueError("Snapshot original permission mismatch")


class SnapshotArchive:
    def __init__(self, root, rows, evidence):
        self.root, self.rows, self.evidence = root, rows, evidence

    def read_json(self, relative):
        if relative not in self.rows:
            raise ValueError("Record absent from original snapshot")
        path = self.root / relative
        if path.resolve().relative_to(self.root.resolve()).as_posix() != relative:
            raise ValueError("Snapshot record escaped its original root")
        check_file(path, self.rows[relative])
        return json.loads(path.read_text())


def verify_snapshot_archive(*, restored, transport, recovery, claim, bootstrap):
    """Recheck both original seals, all restored members and the source claim.

    The authenticated download receipt must already bind this original transport
    to the submission claim. No synthetic `download_checked` member seal is made.
    """
    restored, transport = Path(restored), Path(transport)
    if restored.is_symlink() or transport.is_symlink():
        raise ValueError("Unsafe original archive directory")
    member_manifest = regular(restored / "snapshot-files.json")
    transport_manifest = regular(transport / "export-manifest.json")
    original = json.loads(transport_manifest.read_text())
    if original.get("download_checked") is not True:
        raise ValueError("Snapshot transport lacks its checked original seal")
    objects = inventory(original)
    if set(objects) != {"evidence.tar.gz", "snapshot-files.json"}:
        raise ValueError("Unexpected original snapshot transport objects")
    for name, row in objects.items():
        # Download caches may deliberately be private0600; object-store modes
        # are metadata. Original member modes are restored and checked below.
        check_file(transport / name, row, mode=False)
    if member_manifest.read_bytes() != (transport / "snapshot-files.json").read_bytes():
        raise ValueError("Restored member manifest differs from original transport")
    copied_seal = regular(restored / "transport-export-manifest.json")
    if copied_seal.read_bytes() != transport_manifest.read_bytes():
        raise ValueError("Restored transport seal differs from original")
    manifest = json.loads(member_manifest.read_text())
    if manifest.get("source_quiescent") is not True:
        raise ValueError("Snapshot source was not quiescent")
    rows = inventory(manifest)
    readback_path = regular(restored / "snapshot-readback.json")
    readback = json.loads(readback_path.read_text())
    if (
        readback.get("all_snapshot_files_hash_size_mode_verified") is not True
        or type(readback.get("file_count")) is not int
        or type(readback.get("bytes")) is not int
        or readback.get("source_manifest_sha256") != digest(member_manifest)
        or readback.get("transport_manifest_sha256") != digest(transport_manifest)
        or readback.get("file_count") != len(rows)
        or readback.get("bytes") != sum(r["bytes"] for r in rows.values())
    ):
        raise ValueError("Snapshot readback does not bind the original inventory")
    recovered = json.loads(regular(recovery).read_text())
    submitted = json.loads(regular(claim).read_text())
    if (
        recovered.get("snapshot") != readback
        or recovered.get("source_claim_sha256") != digest(Path(claim))
        or recovered.get("original_bootstrap_sha256") != digest(regular(bootstrap))
        or recovered["original_bootstrap_sha256"] != submitted["inputs"]["files"]["bootstrap.py"]
    ):
        raise ValueError("Snapshot recovery belongs to a different source claim")
    root = restored / "files"
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Original snapshot member directory is absent")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("Unsafe restored snapshot member")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name not in rows:
                raise ValueError("Unexpected restored snapshot file")
            check_file(path, rows[name])
            actual.add(name)
    if actual != set(rows):
        raise ValueError("Missing original snapshot member")
    return SnapshotArchive(
        root,
        rows,
        {
            "archive_format": "original-snapshot-v1",
            "member_manifest_sha256": digest(member_manifest),
            "transport_manifest_sha256": digest(transport_manifest),
            "snapshot_readback_sha256": digest(readback_path),
            "source_claim_sha256": digest(Path(claim)),
            "original_bootstrap_sha256": digest(Path(bootstrap)),
            "file_count": len(rows),
            "bytes": readback["bytes"],
            "original_per_file_seal_reconstructed": False,
            "scope": "Original archive identities and authenticated recovery binding; no scientific acceptance or redistribution grant.",
        },
    )
