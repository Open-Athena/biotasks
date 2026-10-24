"""Small Python-3.12-compatible worker contracts, with no optional SDK imports."""

import hashlib
import json
import tarfile
from pathlib import Path
from typing import Any

from biotasks.validation.files import content_sha as content_sha
from biotasks.validation.files import require as require
from biotasks.validation.files import safe as safe
from biotasks.validation.files import write_json as write
from biotasks.validation.recipes import native_prefix as native_prefix


def sha(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def unpack(source: Path, expected: list[dict[str, Any]], target: Path | None = None) -> None:
    specs = {row["path"]: row for row in expected}
    seen = set()
    total = 0
    with tarfile.open(source, "r|gz") as archive:
        for member in archive:
            name = safe(member.name)
            if member.isdir():
                continue
            total += member.size
            require(
                member.isfile() and name in specs and name not in seen, "Unexpected input member"
            )
            require(0 <= member.size <= 8 * 1024**2 and total <= 32 * 1024**2, "Input archive size")
            stream = archive.extractfile(member)
            require(stream is not None, "Missing input member")
            assert stream is not None
            raw = stream.read(8 * 1024**2 + 1)
            row = specs[name]
            require(
                len(raw) == row["bytes"]
                and content_sha(raw) == row["sha256"]
                and member.mode == int(row["mode"], 8),
                "Input member identity changed",
            )
            if target is not None:
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                path.chmod(member.mode)
            seen.add(name)
    require(seen == set(specs), "Missing input members")


def checkpoint(path: Path, value: Any) -> None:
    write(path, value)
    print("BIOTASKS_VALIDATION_REPORT=" + json.dumps(value), flush=True)
