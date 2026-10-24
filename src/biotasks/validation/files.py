"""Bounded identities and durable local records shared with the worker."""

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

MAX_FILE = 8 * 1024**2
MAX_ARCHIVE = 32 * 1024**2


class ValidationError(ValueError):
    """A source, policy or evidence contract cannot be established."""


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def content_sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_sha(value: Any) -> str:
    return content_sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def read_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"Missing or symlinked record: {path}")
    require(path.stat().st_size <= MAX_ARCHIVE, f"Record exceeds size limit: {path}")
    return json.loads(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    """Replace one record atomically, flushing file and directory before return."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def lock(path: Path) -> Iterator[None]:
    """A nonblocking per-run/ledger lock, independent of the shared heavy lock."""
    try:
        import fcntl
    except ImportError as error:
        raise ValidationError("Validation requires a POSIX controller with flock") from error
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def safe(name: str) -> str:
    path = PurePosixPath(name)
    require(
        bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name,
        f"Unsafe archive path: {name!r}",
    )
    return str(path)


def inventory(root: Path) -> list[dict[str, Any]]:
    require(root.is_dir() and not root.is_symlink(), f"Not a source directory: {root}")
    rows = []
    total = 0
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"Symlinked input: {path}")
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        require(size <= MAX_FILE and total <= MAX_ARCHIVE, "Input inventory exceeds limits")
        rows.append(
            {
                "path": safe(path.relative_to(root).as_posix()),
                "bytes": size,
                "mode": oct(path.stat().st_mode & 0o777)[2:],
                "sha256": sha(path),
            }
        )
        require(len(rows) <= 1000, "Input inventory exceeds 1000 files")
    return rows
