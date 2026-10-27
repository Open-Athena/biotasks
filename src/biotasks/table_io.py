"""Read delimited output syntax without choosing scientific comparison rules."""

import csv
from pathlib import Path


def read_delimited_table(
    path: str | Path,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
    allow_blank_records: bool = False,
) -> tuple[list[str], list[list[str]]]:
    """Return a header and equal-width rows, retaining every decoded field.

    Uses Python's strict CSV reader, including quoted delimiters/newlines and
    ordinary line endings. Only completely empty CSV records may be skipped,
    and only when explicitly enabled. Quoted empty fields, whitespace-only
    fields and delimiter-only rows are data, not empty records. No stripping,
    numeric conversion, sorting, deduplication or scientific equivalence is
    inferred. Callers still validate header names, identities and values.
    """
    records = []
    try:
        with Path(path).open(encoding=encoding, newline="") as stream:
            for row in csv.reader(stream, delimiter=delimiter, strict=True):
                if not row:
                    if allow_blank_records:
                        continue
                    raise ValueError("Empty CSV record is not allowed")
                records.append(row)
    except csv.Error as error:
        raise ValueError(f"Invalid delimited syntax: {error}") from error
    if not records:
        raise ValueError("Delimited table has no header")
    header, *rows = records
    if any(len(row) != len(header) for row in rows):
        raise ValueError("Delimited table has inconsistent row widths")
    return header, rows
