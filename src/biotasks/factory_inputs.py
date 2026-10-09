"""Assemble fresh author inputs from explicit source assets, without prior tasks."""

import hashlib
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


def assemble(source: Path, selected: list[str], shared: dict[str, bytes], output: Path) -> dict:
    """Stream explicitly selected source members into a reproducible archive.

    Asset selection is experiment metadata. This helper contains no seed-specific
    paths. Shared files replace old prompts/protocols uniformly across a batch.
    """
    names = selected + list(shared)
    if len(names) != len(set(names)):
        raise ValueError("Duplicate input names")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or not path.parts:
            raise ValueError("Unsafe input path")
    with zipfile.ZipFile(source) as original:
        if len(original.namelist()) != len(set(original.namelist())):
            raise ValueError("Duplicate source members")
        members = {name: original.getinfo(name) for name in selected}
        for info in members.values():
            if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Only regular source files are supported")
        total = sum(i.file_size for i in members.values()) + sum(map(len, shared.values()))
        if total > 128 * 1024 * 1024:
            raise ValueError("Input preparation exceeds bounded local size")
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_STORED) as target:
            for name in sorted(names):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                with target.open(info, "w") as destination:
                    if name in shared:
                        destination.write(shared[name])
                    else:
                        with original.open(name) as incoming:
                            shutil.copyfileobj(incoming, destination, 1024 * 1024)
    digest = hashlib.sha256()
    with output.open("rb") as archive:
        while chunk := archive.read(1024 * 1024):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size_bytes": output.stat().st_size, "members": names}
