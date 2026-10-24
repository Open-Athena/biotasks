"""Acquire the exact official source members and isolated local-export writer.

No package is executed or installed. Remote data cannot select output paths or
executable code beyond the bundled member hash allowlist. Existing caches are
read-only verified; interrupted acquisition is retained for explicit inspection.
"""

import hashlib
import json
import os
import tarfile
import urllib.request
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import Any

from biotasks.validation.files import (
    content_sha,
    inventory,
    json_sha,
    lock,
    read_json,
    require,
    safe,
    sha,
    write_json,
)
from biotasks.validation.planning import UPSTREAM

URL = f"https://github.com/huggingface/Repo2RLEnv/archive/{UPSTREAM}.tar.gz"
ARCHIVES = {
    "9c09729e909766366d8761e71a3585a64f656d1d3c64909b0656a0af28b402e9",
    "7e387fbb04d5374964de37a31b63e6cabc310198703213c6a40bf8d5c6dd4755",
}


def specification() -> tuple[dict[str, Any], dict[str, Any]]:
    root = files("biotasks.generation")
    return (
        json.loads((root / "package-acquisition.json").read_bytes()),
        json.loads((root / "check-dependency.json").read_bytes()),
    )


def writer_inventory() -> list[dict[str, Any]]:
    return json.loads((files("biotasks.generation") / "dependency-inventory.json").read_bytes())


def _download(url: str, target: Path, maximum: int) -> None:
    with urllib.request.urlopen(url, timeout=120) as response, target.open("xb") as output:
        total = 0
        while chunk := response.read(65536):
            total += len(chunk)
            require(total <= maximum, "Acquisition download exceeds bound")
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())


def unpack_source(archive: Path, target: Path) -> None:
    expected, _ = specification()
    require(
        archive.stat().st_size <= 20 * 1024**2 and sha(archive) in ARCHIVES,
        "Unknown official archive bytes",
    )
    members = {row["path"]: row for row in expected["files"]}
    seen: set[str] = set()
    total = 0
    count = 0
    with tarfile.open(archive, mode="r|gz") as stream:
        for member in stream:
            count += 1
            total += member.size
            require(
                count <= 5000 and 0 <= total <= 100 * 1024**2,
                "Source archive expansion exceeds bound",
            )
            name = safe(member.name)
            relative = name.partition("/")[2]
            if relative not in members:
                continue
            row = members[relative]
            require(
                member.isfile() and relative not in seen and member.size == row["bytes"],
                "Invalid/duplicate selected source member",
            )
            source = stream.extractfile(member)
            require(source is not None, "Missing selected source bytes")
            assert source is not None
            raw = source.read(row["bytes"] + 1)
            require(
                len(raw) == row["bytes"] and content_sha(raw) == row["sha256"],
                "Official source member changed",
            )
            blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            require(blob == row["git_blob"], "Official Git blob differs")
            destination = target / safe(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            destination.chmod(0o644)
            seen.add(relative)
    require(seen == set(members), "Incomplete official source acquisition")


def unpack_dependency(archive: Path, target: Path) -> None:
    _, expected = specification()
    require(
        archive.stat().st_size == expected["bytes"] and sha(archive) == expected["sha256"],
        "Pinned writer wheel changed",
    )
    seen: set[str] = set()
    with zipfile.ZipFile(archive) as wheel:
        require(
            len(wheel.infolist()) <= 30
            and sum(row.file_size for row in wheel.infolist()) <= 100000,
            "Writer wheel expansion exceeds bound",
        )
        for row in wheel.infolist():
            name = safe(row.filename)
            require(
                name not in seen and (row.external_attr >> 16) & 0o170000 != 0o120000,
                "Duplicate/symlinked writer member",
            )
            seen.add(name)
            if row.is_dir():
                continue
            target_path = target / name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(wheel.read(row))
            target_path.chmod(0o644)


def verify(root: Path) -> dict[str, Any]:
    receipt = read_json(root / "receipt.json")
    value = dict(receipt)
    require(value.pop("receipt_identity") == json_sha(value), "Source receipt changed")
    expected, dependency = specification()
    require(
        receipt["revision"] == UPSTREAM
        and receipt["reference_manifest_sha256"]
        == content_sha((files("biotasks.generation") / "package-acquisition.json").read_bytes()),
        "Source specification changed",
    )
    require(
        receipt["dependency_wheel_sha256"] == dependency["sha256"], "Writer specification changed"
    )
    actual = inventory(root / "source")
    dependency_inventory = inventory(root / "extra_modules")
    pinned_dependency = writer_inventory()
    require(
        actual == receipt["source_inventory"]
        and dependency_inventory == receipt["dependency_inventory"] == pinned_dependency,
        "Source/writer cache changed",
    )
    require(
        {row["path"]: (row["bytes"], row["sha256"]) for row in actual}
        == {row["path"]: (row["bytes"], row["sha256"]) for row in expected["files"]},
        "Source member set differs",
    )
    require(
        sha(root / "source-manifest.json") == receipt["source_manifest_sha256"],
        "Local source manifest changed",
    )
    return receipt


def acquire(
    root: Path, *, archive: Path | None = None, dependency: Path | None = None
) -> dict[str, Any]:
    root = root.resolve()
    with lock(root.with_name(root.name + ".lock")):
        if root.exists():
            return verify(root)
        stage = root.with_name(root.name + ".staging")
        require(
            not stage.exists(), "Interrupted acquisition retained; inspect its staging directory"
        )
        stage.mkdir(parents=True, mode=0o700)
        expected, writer = specification()
        if archive is None:
            archive = stage / "source.tar.gz"
            _download(URL, archive, 20 * 1024**2)
        if dependency is None:
            dependency = stage / writer["wheel"]
            _download(writer["source"], dependency, 100000)
        unpack_source(archive, stage / "source")
        unpack_dependency(dependency, stage / "extra_modules")
        acquired = {
            **expected,
            "archive_sha256": sha(archive),
            "archive_bytes": archive.stat().st_size,
        }
        write_json(stage / "source-manifest.json", acquired)
        receipt = {
            "revision": UPSTREAM,
            "source_url": URL,
            "archive_sha256": sha(archive),
            "archive_bytes": archive.stat().st_size,
            "reference_manifest_sha256": content_sha(
                (files("biotasks.generation") / "package-acquisition.json").read_bytes()
            ),
            "source_manifest_sha256": sha(stage / "source-manifest.json"),
            "dependency_wheel_sha256": writer["sha256"],
            "source_inventory": inventory(stage / "source"),
            "dependency_inventory": inventory(stage / "extra_modules"),
            "package_executed": False,
            "model_calls": 0,
            "remote_jobs": 0,
        }
        receipt["receipt_identity"] = json_sha(receipt)
        write_json(stage / "receipt.json", receipt)
        for path in (archive, dependency):
            if path.parent == stage:
                path.unlink()
        os.replace(stage, root)
        return verify(root)


def configuration(root: Path) -> dict[str, Any]:
    receipt = verify(root)
    return {
        "directory": {
            "path": str(root / "source"),
            "inventory_sha256": json_sha(receipt["source_inventory"]),
        },
        "acquisition": {
            "path": str(root / "source-manifest.json"),
            "sha256": receipt["source_manifest_sha256"],
        },
        "extra_modules": {
            "path": str(root / "extra_modules"),
            "inventory_sha256": json_sha(receipt["dependency_inventory"]),
        },
    }
