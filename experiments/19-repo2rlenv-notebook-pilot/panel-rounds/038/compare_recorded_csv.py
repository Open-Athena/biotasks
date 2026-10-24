"""Describe differences between archived CSVs; no tolerances, reward or science rerun."""

import argparse
import csv
import hashlib
import json
import math
from itertools import zip_longest
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
manifest_raw = (args.archive / "sealed-manifest.json").read_bytes()
manifest = {r["path"]: r for r in json.loads(manifest_raw)["files"]}
readback = json.loads((args.archive / "independent-readback.json").read_text())
assert readback["all_files_download_verified"]
assert readback["source_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest()
root = args.archive / "files"
records = []
for left in sorted((root / "materialization/reference").glob("*.csv")):
    right = root / "grading/independent-outputs" / left.name
    identities = {}
    for label, path in [("reference", left), ("independent", right)]:
        row = manifest[path.relative_to(root).as_posix()]
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        assert digest == row["sha256"] and path.stat().st_size == row["bytes"]
        identities[label] = digest
    columns, count, unmatched = {}, 0, 0
    with left.open(newline="") as lf, right.open(newline="") as rf:
        ls, rs = csv.DictReader(lf), csv.DictReader(rf)
        assert ls.fieldnames == rs.fieldnames
        for a, b in zip_longest(ls, rs):
            count += 1
            if a is None or b is None:
                unmatched += 1
                continue
            assert set(a) == set(b) == set(ls.fieldnames)
            for key in ls.fieldnames:
                entry = columns.setdefault(
                    key,
                    dict(
                        numeric_cells=0,
                        unequal_numeric_cells=0,
                        nonfinite_cells=0,
                        max_absolute_difference=0.0,
                        max_relative_to_nonzero_reference=0.0,
                        unequal_text_cells=0,
                        differing_zero_reference_cells=0,
                    ),
                )
                try:
                    av, bv = float(a[key]), float(b[key])
                except (TypeError, ValueError):
                    entry["unequal_text_cells"] += a[key] != b[key]
                    continue
                entry["numeric_cells"] += 1
                if not math.isfinite(av) or not math.isfinite(bv):
                    entry["nonfinite_cells"] += 1
                    continue
                delta = abs(av - bv)
                entry["unequal_numeric_cells"] += av != bv
                entry["max_absolute_difference"] = max(entry["max_absolute_difference"], delta)
                if av:
                    entry["max_relative_to_nonzero_reference"] = max(
                        entry["max_relative_to_nonzero_reference"], delta / abs(av)
                    )
                else:
                    entry["differing_zero_reference_cells"] += av != bv
    records.append(
        dict(
            file=left.name, sha256=identities, rows=count, unmatched_rows=unmatched, columns=columns
        )
    )
args.output.write_text(
    json.dumps(
        {
            "source_archive_manifest_sha256": readback["source_manifest_sha256"],
            "scope": "Read-only comparison of original recorded values by row/column. No tolerance, scientific correctness, acceptance, reward or fresh execution is inferred.",
            "files": records,
        },
        indent=2,
    )
    + "\n"
)
for row in records:
    print(
        json.dumps(
            {
                "file": row["file"],
                "rows": row["rows"],
                "nonzero_differences": {
                    k: v["max_absolute_difference"]
                    for k, v in row["columns"].items()
                    if v["max_absolute_difference"]
                },
            }
        )
    )
