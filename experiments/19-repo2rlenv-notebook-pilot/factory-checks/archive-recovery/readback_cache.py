"""Bound local archive storage; independently verify each new remote object."""

import hashlib
import os
import stat
from pathlib import Path

BLOCK = 1024 * 1024


def identity(row):
    return row["sha256"], row["bytes"], row["mode"]


def verify_local(path, row):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Archive cache must be a regular, non-symlink file")
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if (
        digest != row["sha256"]
        or path.stat().st_size != row["bytes"]
        or stat.S_IMODE(path.stat().st_mode) != row["mode"]
    ):
        raise ValueError("Archive cache identity changed")


def stream_verified(source, row, target=None):
    digest, count = hashlib.sha256(), 0
    while chunk := source.read(BLOCK):
        count += len(chunk)
        if count > row["bytes"]:
            raise ValueError("Remote archive file exceeds its sealed size")
        digest.update(chunk)
        if target is not None:
            target.write(chunk)
    if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
        raise ValueError("Remote archive file differs from its sealed identity")


def store(source_factory, destination, row, cache):
    """A duplicate still reads its own remote object before any local link.

    Only equal SHA256, size and mode can share storage. Original remote objects
    remain untouched. Cache paths are immutable evidence, never working files.
    """
    destination = Path(destination)
    key = identity(row)
    if destination.exists() or destination.is_symlink():
        verify_local(destination, row)
        cache.setdefault(key, destination)
        return {"method": "existing_verified_local_file", "remote_object_read_now": False}
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    partial = destination.with_name(destination.name + ".readback-partial")
    if partial.exists() or partial.is_symlink():
        raise ValueError("Preserve interrupted original readback before retry")
    duplicate = cache.get(key)
    if duplicate is not None:
        with source_factory() as source:
            stream_verified(source, row)
        verify_local(duplicate, row)
        os.link(duplicate, destination)
        verify_local(destination, row)
        return {
            "method": "independent_remote_read_then_verified_local_hardlink",
            "remote_object_read_now": True,
            "cache_source": str(duplicate),
        }
    with source_factory() as source, partial.open("xb") as target:
        stream_verified(source, row, target)
    partial.chmod(row["mode"])
    partial.replace(destination)
    verify_local(destination, row)
    cache[key] = destination
    return {"method": "independent_remote_read_and_materialization", "remote_object_read_now": True}
