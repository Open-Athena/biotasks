"""Bounded streaming recovery of a known-size archive; no credentials or extraction."""

import hashlib
from pathlib import Path


def recover(stream, target: Path, expected_bytes: int, *, maximum_bytes: int):
    if not 0 < expected_bytes <= maximum_bytes:
        raise ValueError("Archive size outside recovery allowance")
    if target.exists():
        raise FileExistsError(target)
    partial = target.with_name(target.name + ".partial")
    digest = hashlib.sha256()
    count = 0
    # Exclusive creation preserves evidence from an interrupted recovery.
    with partial.open("xb") as output:
        while block := stream.read(min(1024 * 1024, expected_bytes - count + 1)):
            count += len(block)
            if count > expected_bytes:
                raise ValueError("Archive exceeds declared size")
            output.write(block)
            digest.update(block)
    if count != expected_bytes:
        raise ValueError("Archive is truncated")
    # Exclusive link avoids replacing evidence if another recovery finishes first.
    target.hardlink_to(partial)
    partial.unlink()
    return {"size_bytes": count, "sha256": digest.hexdigest()}
