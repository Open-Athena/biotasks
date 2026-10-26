"""Stream numeric discovery hints without importing scientific or provider libraries.

This shared lexical/table inspection does not classify an answer or define a
scientific grading tolerance. Callers must supply validated file identities.
"""

import bisect
import csv
import hashlib
import json
import math
import tokenize
from pathlib import PurePosixPath

# A discovery radius, never a grader tolerance or a portability assertion.
RELATIVE_HINT_DISTANCE = 1e-8


def floating_literals(stream, remaining):
    """Stream lexical literals without importing, executing or rewriting code."""
    for token in tokenize.tokenize(stream.readline):
        remaining()
        if token.type != tokenize.NUMBER or not any(c in token.string.lower() for c in ".e"):
            continue
        try:
            value = abs(float(token.string))
        except ValueError:
            continue
        if not math.isfinite(value) or value.is_integer():
            continue
        yield {
            "literal_magnitude": value,
            "source_token": token.string,
            "source_line": token.start[0],
            "source_column": token.start[1] + 1,
            "source_text": token.line.rstrip("\r\n"),
        }


def verify_reference(references, name):
    references.remaining()
    path = references.root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Linked reference is not inspection evidence")
    if not path.is_file() or not path.resolve().is_relative_to(references.root.resolve()):
        raise ValueError("Recorded reference is unavailable")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            references.remaining()
            digest.update(chunk)
            size += len(chunk)
    if {"sha256": digest.hexdigest(), "bytes": size} != references.catalog[name]:
        raise ValueError("Reference identity changed during value inspection")
    return path


def csv_matches(references, literals):
    """Index source literals; stream final outputs rather than loading matrices."""
    by_value = {}
    for literal in literals:
        by_value.setdefault(literal["literal_magnitude"], []).append(literal)
    values = sorted(by_value)
    findings, coverage = [], []
    for name, identity in references.catalog.items():
        suffix = PurePosixPath(name).suffix.casefold()
        if suffix not in {".csv", ".tsv"}:
            coverage.append({"path": name, "status": "unsupported_format"})
            continue
        path = verify_reference(references, name)
        matched = {}
        try:
            with path.open(encoding="utf-8", newline="") as stream:
                rows = csv.reader(stream, delimiter="\t" if suffix == ".tsv" else ",")
                for row in rows:
                    references.remaining()
                    for column, text in enumerate(row, 1):
                        try:
                            number = float(text)
                        except ValueError:
                            continue
                        magnitude = abs(number)
                        if not math.isfinite(magnitude) or magnitude in {0, 1}:
                            continue
                        distance = magnitude * RELATIVE_HINT_DISTANCE
                        lower = bisect.bisect_left(values, magnitude - distance)
                        upper = bisect.bisect_right(values, magnitude + distance)
                        for value in values[lower:upper]:
                            for literal in by_value[value]:
                                key = (
                                    literal["asset_sha256"],
                                    literal["path"],
                                    literal["source_line"],
                                    literal["source_column"],
                                )
                                if key not in matched:
                                    matched[key] = {
                                        **literal,
                                        "reference_path": name,
                                        "reference_sha256": identity["sha256"],
                                        "reference_line": rows.line_num,
                                        "reference_column": column,
                                        "reference_value": number,
                                        "matching_cells": 0,
                                    }
                                matched[key]["matching_cells"] += 1
        except (UnicodeError, csv.Error):
            verify_reference(references, name)
            coverage.append({"path": name, "status": "unreadable_text_table"})
            continue
        verify_reference(references, name)
        coverage.append({"path": name, "status": "numeric_cells_inspected"})
        for finding in matched.values():
            raw = json.dumps(finding, sort_keys=True, allow_nan=False).encode()
            findings.append({"hint_id": hashlib.sha256(raw).hexdigest(), **finding})
    return findings, coverage
