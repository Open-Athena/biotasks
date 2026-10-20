"""Measure bounded structural facts about staged files, without choosing a task.

Run in the authoring workspace. Files are hashed by streaming; no notebook code,
analysis, sort, model fitting or full matrix materialization runs here. HDF5
inspection uses h5py when installed in that workspace; missing readers and
unsupported formats remain explicit unknowns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import io
import json
import math
import platform
import re
from pathlib import Path, PurePosixPath


def _table(path: Path) -> dict:
    with path.open("rb") as stream:
        prefix = stream.read(65537)
    complete = len(prefix) <= 65536
    if not complete:
        # Drop a partial physical line; csv's strict parser also rejects any
        # unfinished quoted record, without counting it as an observed row.
        prefix = prefix[:65536].rsplit(b"\n", 1)[0]
    reader = csv.reader(
        io.StringIO(prefix.decode("utf-8-sig")),
        delimiter="\t" if path.suffix.lower() == ".tsv" else ",",
        strict=True,
    )
    columns = next(reader)
    if len(columns) > 256 or any(len(value) > 1024 for value in columns):
        raise ValueError("Table header exceeds the inspection bound")
    widths = []
    exhausted = False
    try:
        for _ in range(101):
            widths.append(len(next(reader)))
    except StopIteration:
        exhausted = True
    except csv.Error:
        if complete:
            raise
    return {
        "kind": "delimited_text",
        "first_record": columns,
        "first_record_is_header": "not inferred",
        "rows_inspected": min(len(widths), 100),
        "observed_field_counts": sorted(set(widths[:100])),
        "records_after_first": len(widths) if complete and exhausted else None,
        "scope": "first record and at most 100 further records; no inferred column types",
    }


def _hdf5(path: Path) -> dict:
    h5py = importlib.import_module("h5py")
    datasets = []
    truncated = False
    visited = 0

    def visit(name, item):
        nonlocal truncated, visited
        visited += 1
        if visited > 512 or len(name) > 4096:
            truncated = True
            return "stop"
        if not isinstance(item, h5py.Dataset):
            return None
        if len(datasets) >= 256:
            truncated = True
            return "stop"
        shape = item.shape
        record = {
            "path": "/" + name,
            "shape": list(shape) if shape is not None else None,
            "dtype": str(item.dtype),
            "chunks": list(item.chunks) if item.chunks else None,
            "compression": item.compression,
        }
        # Tiny numeric metadata vectors can encode matrix dimensions. Preserve
        # their values without assuming axis roles or a particular HDF5 schema.
        if (
            shape is not None
            and len(shape) <= 1
            and math.prod(shape) <= 16
            and item.dtype.kind in "biu"
            and item.dtype.itemsize <= 8
            and not item.is_virtual
            and not item.external
            and (not item.chunks or math.prod(item.chunks) * item.dtype.itemsize <= 65536)
        ):
            record["values"] = item[()].tolist()
        datasets.append(record)
        return None

    with h5py.File(path, "r") as data:
        data.visititems(visit)
    return {
        "kind": "hdf5",
        "reader": {"package": "h5py", "version": h5py.__version__},
        "datasets": datasets,
        "truncated": truncated,
        "scope": "dataset structure and tiny integer metadata; soft/external links not followed",
        "axis_semantics": "not inferred",
    }


def profile_file(root: Path, relative: str, checksums: dict[str, str] | None = None) -> dict:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(p in {".", ".."} for p in path.parts):
        raise ValueError("Input path must be relative and contained in the input directory")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Staged inputs must not be symbolic links")
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise ValueError("Staged input must be a contained regular file")
    expected = dict(checksums or {})
    for algorithm, value in expected.items():
        length = {"sha256": 64, "md5": 32}.get(algorithm)
        if (
            length is None
            or not isinstance(value, str)
            or not re.fullmatch(rf"[0-9a-fA-F]{{{length}}}", value)
        ):
            raise ValueError("Expected checksums must be valid SHA256 or MD5 hex digests")
    hashes = {algorithm: hashlib.new(algorithm) for algorithm in {"sha256", *expected}}
    before = current.stat()
    with current.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            for value in hashes.values():
                value.update(chunk)
    digests = {algorithm: value.hexdigest() for algorithm, value in hashes.items()}
    if any(digests[name] != value.lower() for name, value in expected.items()):
        raise ValueError("Staged input does not match its declared checksum")
    record = {
        "path": path.as_posix(),
        "bytes": before.st_size,
        "digests": digests,
        "verified_source_checksums": expected,
        "source_identity_status": "verified" if expected else "no source checksum supplied",
    }
    try:
        suffix = current.suffix.lower()
        if suffix in {".csv", ".tsv"}:
            record["structure"] = _table(current)
        elif suffix in {".h5", ".hdf5", ".h5ad"}:
            record["structure"] = _hdf5(current)
        else:
            record["structure"] = {"kind": "unknown", "reason": "No structural reader selected"}
    except (ImportError, ValueError, OSError, csv.Error, StopIteration) as exc:
        record["structure"] = {
            "kind": "unknown",
            "reason": "Structural inspection did not complete",
            "error_type": type(exc).__name__,
        }
    after = current.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("Input changed during inspection; discard this profile")
    return record


def profile_inputs(root: Path, manifest: list[dict]) -> dict:
    if not isinstance(manifest, list) or not 1 <= len(manifest) <= 64:
        raise ValueError("An explicit manifest of 1–64 staged files is required")
    if len({item["path"] for item in manifest}) != len(manifest):
        raise ValueError("Duplicate staged input paths")
    return {
        "schema_version": 1,
        "producer": "biotasks.data_profile",
        "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "files": [profile_file(root, item["path"], item.get("checksums")) for item in manifest],
        "scientific_analysis_executed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = profile_inputs(args.root, json.loads(args.manifest.read_text()))
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
