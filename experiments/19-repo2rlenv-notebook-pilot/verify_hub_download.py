"""Verify a pinned upstream release after downloading its mode-preserving archive."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from repo2rlenv.campaigns.release import verify_release
from repo2rlenv.emitter.bundle import inspect_bundle

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 4096
MAX_METADATA_BYTES = 16384
MAX_PATH_BYTES = 1024


def safe_path(name: str) -> Path:
    if not name or len(name.encode()) > MAX_PATH_BYTES or "\\" in name or "\x00" in name:
        raise ValueError("Unsafe release path")
    value = PurePosixPath(name)
    if value.is_absolute() or ".." in value.parts or value.as_posix() != name:
        raise ValueError("Unsafe release path")
    return Path(name)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def bounded_archive(source, destination, entries):
    """Bound raw headers before tarfile parses extended metadata; validate before extracting."""
    expected_files = {name for name in entries if name.startswith("tasks/")}
    expected_dirs = {
        parent.as_posix()
        for name in expected_files
        for parent in Path(name).parents
        if parent != Path(".")
    }
    with tempfile.TemporaryFile() as raw:
        with gzip.open(source, "rb") as compressed:
            total = 0
            for index in range(MAX_ARCHIVE_MEMBERS + 1):
                header = compressed.read(512)
                if header == b"\0" * 512:
                    raw.write(header)
                    break
                if len(header) != 512 or index == MAX_ARCHIVE_MEMBERS:
                    raise ValueError("Invalid or excessive archive headers")
                member = tarfile.TarInfo.frombuf(header, "utf-8", "surrogateescape")
                if member.size < 0 or member.size > MAX_FILE_BYTES:
                    raise ValueError("Archive member exceeds size bound")
                if (
                    member.type
                    in {
                        tarfile.XHDTYPE,
                        tarfile.XGLTYPE,
                        tarfile.GNUTYPE_LONGNAME,
                        tarfile.GNUTYPE_LONGLINK,
                    }
                    and member.size > MAX_METADATA_BYTES
                ):
                    raise ValueError("Archive metadata exceeds bound")
                size = (member.size + 511) // 512 * 512
                total += 512 + size
                if total > MAX_TOTAL_BYTES + 8 * 1024 * 1024:
                    raise ValueError("Archive expansion exceeds bound")
                raw.write(header)
                while size:
                    block = compressed.read(min(size, 65536))
                    if not block:
                        raise ValueError("Truncated archive")
                    raw.write(block)
                    size -= len(block)
        seen = set()
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode="r|") as archive:
            for member in archive:
                if member.name in seen or len(seen) >= MAX_ARCHIVE_MEMBERS:
                    raise ValueError("Duplicate or excessive archive entries")
                seen.add(member.name)
                safe_path(member.name)
                if member.isdir():
                    if member.name not in expected_dirs:
                        raise ValueError("Unexpected archive directory")
                elif member.isfile() and not member.sparse:
                    entry = entries.get(member.name)
                    if (
                        member.name not in expected_files
                        or member.size != entry["bytes"]
                        or member.mode != entry["mode"]
                    ):
                        raise ValueError("Archive differs from release manifest")
                else:
                    raise ValueError("Archive must contain regular files and directories")
        if not expected_files.issubset(seen):
            raise ValueError("Missing archive files")
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode="r|") as archive:
            for member in archive:
                if member.isfile():
                    target = destination / safe_path(member.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as src, target.open("xb") as dst:
                        shutil.copyfileobj(src, dst, length=65536)
                    target.chmod(member.mode)


def check_download(repo_id: str, revision: str, destination: Path, download) -> dict:
    """Download only public release files, restore modes, then call upstream checks.

    ``download(name)`` must fetch from the explicit immutable publication revision.
    A new destination prevents cached local task files from satisfying the check.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Use the immutable publication commit")
    destination.mkdir(parents=True, exist_ok=False)
    manifest_source = Path(download("release-files.json"))
    if manifest_source.stat().st_size > 1024 * 1024:
        raise ValueError("Release manifest is too large")
    manifest = json.loads(manifest_source.read_text())
    if manifest["repo_id"] != repo_id:
        raise ValueError("Downloaded release belongs to a different repository")
    entries = manifest["files"]
    if sum(v["bytes"] for v in entries.values()) > MAX_TOTAL_BYTES:
        raise ValueError("Release exceeds the bounded local download allowance")
    for name, entry in entries.items():
        safe_path(name)
        if not 0 <= entry["bytes"] <= MAX_FILE_BYTES or not 0 <= entry["mode"] <= 0o777:
            raise ValueError("Invalid release size or mode")
    shutil.copyfile(manifest_source, destination / "release-files.json")
    for name, entry in entries.items():
        if name.startswith("tasks/"):
            continue
        source = Path(download(name))
        if source.stat().st_size != entry["bytes"] or digest(source) != entry["sha256"]:
            raise ValueError(f"Downloaded bytes changed: {name}")
        target = destination / safe_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(entry["mode"])
    bounded_archive(destination / "tasks.tar.gz", destination, entries)
    verify_release(destination)
    release = json.loads((destination / "manifest.json").read_text())
    bundles = []
    for row in release["tasks"]:
        identity = inspect_bundle(destination / safe_path(row["path"]))
        if not identity["integrity_passed"] or identity["bundle_hash"] != row["bundle_hash"]:
            raise ValueError("Downloaded task identity changed")
        bundles.append({"task_id": row["task_id"], "bundle_hash": identity["bundle_hash"]})
    return {"repo_id": repo_id, "revision": revision, "verified": True, "tasks": bundles}


def main():
    from huggingface_hub import hf_hub_download

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_id")
    parser.add_argument("revision")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    result = check_download(
        args.repo_id,
        args.revision,
        args.destination,
        lambda name: hf_hub_download(
            args.repo_id, name, repo_type="dataset", revision=args.revision, force_download=True
        ),
    )
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
