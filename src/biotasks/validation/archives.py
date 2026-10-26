"""Bounded archive identities; extraction never follows links or traverses paths."""

import gzip
import io
import tarfile
from pathlib import Path
from typing import Any

import zstandard

from biotasks.validation.files import (
    MAX_ARCHIVE,
    MAX_FILE,
    content_sha,
    inventory,
    require,
    safe,
    sha,
)


def pack(root: Path, target: Path) -> dict[str, Any]:
    require(not target.exists(), f"Archive already exists: {target}")
    rows = inventory(root)
    with (
        target.open("wb") as output,
        gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w|") as archive,
    ):
        for row in rows:
            member = tarfile.TarInfo(row["path"])
            member.size = row["bytes"]
            member.mode = int(row["mode"], 8)
            with (root / row["path"]).open("rb") as stream:
                archive.addfile(member, stream)
    require(target.stat().st_size <= MAX_ARCHIVE, "Compressed archive exceeds limit")
    return {
        "path": str(target),
        "bytes": target.stat().st_size,
        "sha256": sha(target),
        "files": rows,
    }


def records(source: Path | bytes, kind: str) -> dict[str, dict[str, Any]]:
    if isinstance(source, Path):
        require(source.stat().st_size <= MAX_ARCHIVE, "Archive exceeds limit")
    raw = source if isinstance(source, bytes) else source.read_bytes()
    require(len(raw) <= MAX_ARCHIVE, "Archive exceeds limit")
    if kind == "tar.zst":
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as reader:
            raw = reader.read(MAX_ARCHIVE + 1)
        require(len(raw) <= MAX_ARCHIVE, "Expanded archive exceeds limit")
        mode = "r:"
    else:
        require(kind == "tar.gz", "Unsupported archive format")
        mode = "r:gz"
    rows: dict[str, dict[str, Any]] = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode=mode) as archive:
        for member in archive:
            name = safe(member.name)
            if member.isdir():
                continue
            require(member.isfile() and name not in rows, "Linked/duplicate archive member")
            total += member.size
            require(0 <= member.size <= MAX_FILE and total <= MAX_ARCHIVE, "Archive size bound")
            stream = archive.extractfile(member)
            require(stream is not None, "Missing member contents")
            assert stream is not None
            data = stream.read(MAX_FILE + 1)
            require(len(data) == member.size, "Archive member length mismatch")
            rows[name] = {
                "data": data,
                "bytes": len(data),
                "mode": member.mode,
                "sha256": content_sha(data),
            }
    return rows


def verify_package(
    source: Path | bytes, expected: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    rows = records(source, "tar.gz")
    require(set(rows) == {r["path"] for r in expected}, "Input package members changed")
    for item in expected:
        row = rows[item["path"]]
        require(
            row["sha256"] == item["sha256"]
            and row["bytes"] == item["bytes"]
            and row["mode"] == int(item["mode"], 8),
            "Input package bytes or modes changed",
        )
    return rows
