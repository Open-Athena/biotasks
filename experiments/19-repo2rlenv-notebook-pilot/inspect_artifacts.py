"""Bounded structural observations, not scientific validation or reward.

CSV is scanned in streaming fashion. HDF5 is inspected without loading matrices
or following soft/external links. The same rules apply to any source notebook.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path, PurePosixPath


def relative_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
        raise ValueError("Expected a normalized relative artifact path")
    return path


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def csv_profile(path, *, delimiter=",", distinct_limit=100_000, row_limit=None):
    csv.field_size_limit(1_048_576)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.reader(stream, delimiter=delimiter, strict=True)
        header = next(rows)
        if not 0 < len(header) <= 256:
            raise ValueError("Column count outside inspection limit")
        distinct_limit = min(distinct_limit, max(1, 1_000_000 // len(header)))
        stats = [
            dict(
                name=name,
                position=i,
                empty=0,
                finite_numeric=0,
                nonfinite_numeric=0,
                other=0,
                minimum=None,
                maximum=None,
                examples=[],
            )
            for i, name in enumerate(header)
        ]
        distinct = [set() for _ in header]
        overflow = [False] * len(header)
        fingerprints = [hashlib.sha256() for _ in header]
        count = ragged = 0
        for row in rows:
            count += 1
            if row_limit is not None and count > row_limit:
                raise ValueError("CSV row inspection limit exceeded")
            if len(row) != len(header):
                ragged += 1
                continue
            for index, value in enumerate(row):
                field = stats[index]
                encoded = value.encode()
                fingerprints[index].update(len(encoded).to_bytes(8, "big") + encoded)
                if not value:
                    field["empty"] += 1
                    continue
                fingerprint = hashlib.sha256(encoded).digest()
                if fingerprint not in distinct[index]:
                    if len(distinct[index]) < distinct_limit:
                        distinct[index].add(fingerprint)
                    else:
                        overflow[index] = True
                if len(field["examples"]) < 3 and value[:256] not in field["examples"]:
                    field["examples"].append(value[:256])
                try:
                    number = float(value)
                except ValueError:
                    field["other"] += 1
                    continue
                if not math.isfinite(number):
                    field["nonfinite_numeric"] += 1
                    continue
                field["finite_numeric"] += 1
                field["minimum"] = (
                    number if field["minimum"] is None else min(field["minimum"], number)
                )
                field["maximum"] = (
                    number if field["maximum"] is None else max(field["maximum"], number)
                )
        for i, field in enumerate(stats):
            field.update(
                distinct_nonempty=len(distinct[i]),
                distinct_capped=overflow[i],
                ordered_values_sha256=fingerprints[i].hexdigest(),
            )
    return dict(
        format="delimited",
        row_count=count,
        ragged_rows=ragged,
        distinct_limit_per_column=distinct_limit,
        duplicate_header_names=len(header) != len(set(header)),
        columns=stats,
        limitations=[
            "Numeric ranges use float conversion, not semantic type inference.",
            "Distinct values use SHA-256 identities and the declared cap.",
            "Column fingerprints exclude ragged rows; empty fields are included.",
            "Examples are limited to three values and 256 characters each.",
        ],
    )


def hdf5_profile(path, *, node_limit=2000):
    import h5py

    def scalar(value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")[:256]
        if isinstance(value, str):
            return value[:256]
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple)):
            return [scalar(item) for item in value[:16]]
        if isinstance(value, float) and not math.isfinite(value):
            return str(value)
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:256]

    nodes, skipped_links = [], []
    with h5py.File(path, "r") as source:

        def visit(name, obj):
            if len(nodes) >= node_limit:
                raise ValueError("HDF5 node inspection limit exceeded")
            record = dict(
                path="/" + name, kind="dataset" if isinstance(obj, h5py.Dataset) else "group"
            )
            # These encoding attributes describe format/axes, never full matrix data.
            record["encoding"] = {
                key: scalar(obj.attrs[key])
                for key in ("encoding-type", "encoding-version", "shape", "_index")
                if key in obj.attrs
            }
            if isinstance(obj, h5py.Dataset):
                record.update(
                    shape=obj.shape, dtype=str(obj.dtype), fields=list(obj.dtype.names or ())
                )
                if obj.is_virtual or obj.external:
                    record["preview_skipped"] = "virtual or external storage"
                elif obj.shape is not None and len(obj.shape) <= 1 and not obj.dtype.names:
                    if obj.shape == ():
                        record["preview"] = scalar(obj[()])
                    elif obj.dtype.kind in {
                        "b",
                        "i",
                        "u",
                        "f",
                        "S",
                        "U",
                    } or h5py.check_string_dtype(obj.dtype):
                        record["preview"] = scalar(obj[:5])
                nodes.append(record)
            else:
                nodes.append(record)

        def link(name, item):
            if not isinstance(item, h5py.HardLink):
                if len(skipped_links) >= node_limit:
                    raise ValueError("HDF5 link inspection limit exceeded")
                skipped_links.append(dict(path="/" + name, type=type(item).__name__))

        visit("", source)
        source.visititems(visit)
        source.visititems_links(link)
    return dict(
        format="hdf5",
        nodes=nodes,
        skipped_links=skipped_links,
        limitations=[
            "Shapes, encodings and bounded previews only; no full matrix content scan.",
            "Soft/external links are not followed; virtual/external datasets are not read.",
            "Previews contain at most five entries; text is truncated to 256 characters.",
            "Structural observations do not establish biological correctness.",
        ],
    )


def inspect(path):
    if path.suffix.lower() in {".csv", ".tsv"}:
        return csv_profile(path, delimiter="\t" if path.suffix.lower() == ".tsv" else ",")
    if path.suffix.lower() in {".h5", ".hdf5", ".h5ad"}:
        return hdf5_profile(path)
    return dict(format="unsupported", limitations=["No structural reader for this file type."])


def main(manifest_path, input_root, output_root):
    manifest = json.loads(Path(manifest_path).read_text())
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    observations = []
    for item in manifest["artifacts"]:
        relative = relative_path(item["path"])
        path = Path(input_root) / relative
        if (
            path.is_symlink()
            or path.stat().st_size != item["bytes"]
            or digest(path) != item["sha256"]
        ):
            raise ValueError("Reference artifact identity mismatch")
        profile = dict(
            path=item["path"], bytes=item["bytes"], sha256=item["sha256"], **inspect(path)
        )
        if digest(path) != item["sha256"]:
            raise ValueError("Inspection modified a reference artifact")
        target = output / relative.parent / (relative.name + ".profile.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(profile, indent=2, allow_nan=False) + "\n")
        observations.append(profile)
    (output / "all.json").write_text(json.dumps(observations, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
