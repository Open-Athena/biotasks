"""Advisory final-output matches in hash-verified installed Python source.

This is discovery, not scientific comparison or answer classification. It covers
floating literals in existing priority candidates and numeric CSV/TSV cells only.
Integer-valued constants, comments, strings and other formats remain gaps.
"""

import bisect
import csv
import hashlib
import json
import math
import tokenize
from pathlib import PurePosixPath

import httpx
from package_inspection import normalized

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


async def build_hints(packages, references, priority, exclusions):
    """Use original installed identities, never a filename match alone."""
    excluded = {(normalized(r["distribution"]), r["path"], r["sha256"]) for r in exclusions}
    selected, candidates, literals = {}, [], []
    for row in priority:
        package = normalized(row["distribution"])
        if (package, row["path"], row["sha256"]) in excluded:
            candidates.append(
                {"distribution": package, "path": row["path"], "status": "declared_excluded"}
            )
        elif PurePosixPath(row["path"]).suffix == ".py":
            selected.setdefault(package, []).append(row)
        else:
            candidates.append(
                {
                    "distribution": package,
                    "path": row["path"],
                    "status": "unsupported_non_python_source",
                }
            )
    for package, assets in selected.items():
        try:
            archive = await packages.archive(package)
        except TimeoutError:
            raise
        except (ValueError, OSError, httpx.HTTPError) as error:
            candidates.extend(
                {
                    "distribution": package,
                    "path": r["path"],
                    "status": "release_source_unavailable",
                    "error_type": type(error).__name__,
                }
                for r in assets
            )
            continue
        with archive:
            members = packages.members(archive)
            for asset in assets:
                packages.remaining()
                record = {
                    "distribution": package,
                    "path": asset["path"],
                    "asset_sha256": asset["sha256"],
                }
                names = [
                    n for n in members if n == asset["path"] or n.endswith("/" + asset["path"])
                ]
                if len(names) != 1:
                    candidates.append({**record, "status": "release_member_unresolved"})
                    continue
                member = members[names[0]]
                digest = hashlib.sha256()
                with packages.open_member(archive, member) as stream:
                    while chunk := stream.read(1024 * 1024):
                        packages.remaining()
                        digest.update(chunk)
                if digest.hexdigest() != asset["sha256"]:
                    candidates.append({**record, "status": "installed_source_identity_differs"})
                    continue
                try:
                    with packages.open_member(archive, member) as stream:
                        observed = list(floating_literals(stream, packages.remaining))
                except (UnicodeError, SyntaxError, tokenize.TokenError):
                    candidates.append({**record, "status": "unreadable_python_tokens"})
                    continue
                literals.extend({**record, **value} for value in observed)
                candidates.append(
                    {
                        **record,
                        "status": "installed_source_literals_inspected",
                        "release_member": names[0],
                        "literal_count": len(observed),
                    }
                )
    findings, coverage = csv_matches(references, literals)
    return {
        "scope": (
            "Advisory magnitude matches between floating Python literals in existing priority "
            "package-source candidates and final hash-verified CSV/TSV cells. Source bytes "
            "must match the recorded installed asset. This is not an exhaustive fixture or "
            "semantic audit. Integer-valued constants, strings, comments, other artifacts "
            "and nonpriority files are not covered. A match may be coincidental or unrelated; "
            "inspect provenance, methods and inputs. Absence is not answer-isolation approval. "
            "The first matching cell is shown and all matching cells are counted."
        ),
        "relative_discovery_distance": RELATIVE_HINT_DISTANCE,
        "distance_is_not_grading_tolerance": True,
        "candidates": candidates,
        "reference_coverage": coverage,
        "findings": findings,
    }
