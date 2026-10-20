"""Streaming table observations, never scientific equivalence or grading rules."""

import csv
import hashlib
import json
from pathlib import Path


def table_profile(path):
    path = Path(path)
    if path.suffix.lower() not in {".csv", ".tsv"}:
        return None
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            rows = csv.reader(
                stream, delimiter="\t" if path.suffix.lower() == ".tsv" else ",", strict=True
            )
            header = next(rows)
            count, total = 0, 0
            for row in rows:
                if len(row) != len(header):
                    return None
                encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode()
                total = (total + int.from_bytes(hashlib.sha256(encoded).digest(), "big")) % (
                    1 << 256
                )
                count += 1
        return {"header": header, "rows": count, "row_multiset_sha256_sum": f"{total:064x}"}
    except (UnicodeError, csv.Error, StopIteration):
        return None


def observe_tables(comparisons, baseline, replay):
    for item in comparisons:
        if item["byte_identical"]:
            continue
        original = Path(baseline) / item["path"]
        current = Path(replay) / item["path"]
        # Older snapshots retain only manifests, so absence is unknown, not agreement.
        if not original.is_file() or not current.is_file():
            continue
        with original.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != item["baseline_sha256"]:
            raise ValueError("Baseline table identity mismatch")
        before, after = table_profile(original), table_profile(current)
        item["table_observation"] = {
            "baseline": before,
            "replay": after,
            "same_header_and_row_multiset": before is not None and before == after,
            "scientific_equivalence_established": False,
        }


def reviewable(result):
    """Only permit exact bytes or row-multiset evidence to reach semantic review."""
    return result["all_outputs_byte_identical_to_original"] or result.get(
        "all_output_differences_limited_to_table_serialization_or_row_order", False
    )
