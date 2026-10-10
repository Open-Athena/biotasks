"""Verify a pinned upstream release after downloading its mode-preserving archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tarfile
from pathlib import Path, PurePosixPath

from repo2rlenv.campaigns.release import verify_release
from repo2rlenv.emitter.bundle import inspect_bundle

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024


def safe_path(name: str) -> Path:
    if not name or "\\" in name or "\x00" in name:
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
    with tarfile.open(destination / "tasks.tar.gz", "r:gz") as archive:
        seen = set()
        for member in archive.getmembers():
            if member.name in seen:
                raise ValueError("Duplicate archive entry")
            seen.add(member.name)
            path = safe_path(member.name)
            if not path.parts or path.parts[0] != "tasks":
                raise ValueError("Unexpected archive path")
            if not member.isdir() and not member.isfile():
                raise ValueError("Archive must contain only regular files and directories")
            if member.isfile():
                entry = entries.get(member.name)
                if entry is None or member.size != entry["bytes"] or member.mode != entry["mode"]:
                    raise ValueError("Archive differs from release manifest")
        archive.extractall(destination, filter="data")
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
