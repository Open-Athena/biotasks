#!/usr/bin/env python3
"""Deterministic grader for E. coli core knockout FBA outputs.

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH

Compares four CSV artifacts (knockouts,growth,status) row-by-row after keying
on the knockouts label. Populations are derived from the trusted task input
(BIOTASKS_TRUSTED_INPUT_DIR/e_coli_core.xml), never from the submission.
"""

import argparse
import csv
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

FBC = "{http://www.sbml.org/sbml/level3/version1/fbc/version2}"
CORE = "{http://www.sbml.org/sbml/level3/version1/core}"

GENE_FILE = "single_gene_deletions.csv"
REACTION_FILE = "single_reaction_deletions.csv"
DOUBLE_FILE = "double_reaction_deletions.csv"
PFK_FILE = "pfk_knockout_optima.csv"

PFK_LABELS = ["", "PFK", "b1723", ";".join(sorted(("b1723", "b3916")))]
HEADER = ["knockouts", "growth", "status"]

REL_TOL = 1e-9
ABS_TOL = 1e-11

ALL_FILES = [DOUBLE_FILE, GENE_FILE, PFK_FILE, REACTION_FILE]


# ---------------------------------------------------------------- table syntax

def _read_table(path):
    """Read a comma-delimited table; return (header, rows) or raise."""
    try:
        from biotasks_table_io import read_delimited_table  # type: ignore
    except ImportError:
        read_delimited_table = None
    if read_delimited_table is not None:
        return read_delimited_table(path)
    records = []
    with open(path, encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream, delimiter=",", strict=True):
            if not row:
                raise ValueError("empty CSV record")
            records.append(row)
    if not records:
        raise ValueError("table has no header")
    header, rows = records[0], records[1:]
    if any(len(row) != len(header) for row in rows):
        raise ValueError("inconsistent row widths")
    return header, rows


def _load(path):
    """Return (table dict, None) or (None, error message)."""
    if not os.path.isfile(path):
        return None, "file not found: %s" % path
    try:
        header, rows = _read_table(path)
    except Exception as exc:  # malformed syntax is a failed check, not a crash
        return None, "unreadable or malformed CSV (%s): %s" % (path, exc)
    if header != HEADER:
        return None, "header is %r, expected %r" % (header, HEADER)
    if len(set(header)) != len(header):
        return None, "duplicate header names"
    table = {}
    for row in rows:
        key = row[0]
        if key in table:
            return None, "duplicate knockouts entry: %r" % key
        table[key] = (row[1], row[2])
    return table, None


# ------------------------------------------------------------ model population

def _model_population(trusted_dir):
    """Gene and reaction id populations from the trusted SBML input."""
    path = os.path.join(trusted_dir, "e_coli_core.xml")
    if not os.path.isfile(path):
        raise ValueError("trusted input model not found at %s" % path)
    root = ET.parse(path).getroot()
    genes = []
    for element in root.iter(FBC + "geneProduct"):
        label = element.get(FBC + "label")
        identifier = element.get(FBC + "id")
        if not label or not identifier or not identifier.startswith("G_"):
            raise ValueError("geneProduct without usable label/id")
        if identifier[2:] != label:
            raise ValueError("geneProduct id/label mismatch: %s" % identifier)
        genes.append(label)
    reactions = []
    for element in root.iter(CORE + "reaction"):
        rid = element.get("id")
        if not rid or not rid.startswith("R_"):
            raise ValueError("reaction without usable id")
        reactions.append(rid[2:])
    if not genes or not reactions:
        raise ValueError("model population empty; unexpected SBML layout")
    if len(set(genes)) != len(genes) or len(set(reactions)) != len(reactions):
        raise ValueError("model population contains duplicate identifiers")
    return genes, reactions


def _double_population(reactions):
    keys = set(reactions)
    ordered = sorted(reactions)
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            keys.add(";".join(sorted((ordered[i], ordered[j]))))
    return keys


# ------------------------------------------------------------- value handling

def _parse_growth(cell):
    """Return (value, error). value is None for an empty cell."""
    if cell == "":
        return None, None
    try:
        value = float(cell)
    except (TypeError, ValueError):
        return None, "not a decimal number: %r" % cell
    if not math.isfinite(value):
        return None, "nonfinite value: %r" % cell
    return value, None


def _close(a, b):
    return abs(a - b) <= max(REL_TOL * max(abs(a), abs(b)), ABS_TOL)


def _compare(ref, sub):
    """Row-wise comparison keyed on knockouts. Returns list of problem strings."""
    problems = []
    for key in sorted(ref):
        ref_growth, ref_status = ref[key]
        sub_growth, sub_status = sub[key]
        if sub_status != ref_status:
            problems.append("%s: status %r != reference %r" % (key, sub_status, ref_status))
            continue
        if sub_status == "optimal":
            value, err = _parse_growth(sub_growth)
            if err is not None or value is None:
                problems.append("%s: growth %r is %s" % (key, sub_growth, err or "empty"))
                continue
            ref_value, ref_err = _parse_growth(ref_growth)
            if ref_err is not None or ref_value is None:
                problems.append("%s: reference growth unreadable" % key)
                continue
            if not _close(ref_value, value):
                problems.append(
                    "%s: growth %.17g differs from reference %.17g" % (key, value, ref_value)
                )
        else:
            if sub_growth != "":
                problems.append(
                    "%s: non-optimal status %r must have an empty growth field"
                    % (key, sub_status)
                )
    return problems


def _summary(problems, limit=5):
    if not problems:
        return "all rows match"
    shown = "; ".join(problems[:limit])
    more = "" if len(problems) <= limit else " (+%d more)" % (len(problems) - limit)
    return "%d row problems: %s%s" % (len(problems), shown, more)


# --------------------------------------------------------------------- checks

CHECKS = [
    ("structure_single_gene_table", "structural", [GENE_FILE]),
    ("structure_single_reaction_table", "structural", [REACTION_FILE]),
    ("structure_double_reaction_table", "structural", [DOUBLE_FILE]),
    ("structure_pfk_table", "structural", [PFK_FILE]),
    ("values_single_gene_deletions", "scientific", [GENE_FILE]),
    ("values_single_reaction_deletions", "scientific", [REACTION_FILE]),
    ("values_double_reaction_deletions", "scientific", [DOUBLE_FILE]),
    ("values_pfk_knockout_optima", "scientific", [PFK_FILE]),
    ("cross_table_consistency", "scientific", ALL_FILES),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    results = {}

    def record(check_id, passed, message):
        results[check_id] = (bool(passed), str(message))

    # trusted model population (input-grounded coverage)
    trusted_dir = os.environ.get("BIOTASKS_TRUSTED_INPUT_DIR", "")
    population_error = None
    genes = reactions = None
    try:
        genes, reactions = _model_population(trusted_dir)
    except Exception as exc:
        population_error = "cannot derive model population from trusted input: %s" % exc

    gene_keys = set(genes) if genes is not None else None
    reaction_keys = set(reactions) if reactions is not None else None
    double_keys = _double_population(reactions) if reactions is not None else None
    if genes is not None:
        for identifier in ("b1723", "b3916"):
            if identifier not in gene_keys:
                population_error = "gene %s missing from trusted model" % identifier
        if "PFK" not in reaction_keys:
            population_error = "reaction PFK missing from trusted model"

    expected = {
        GENE_FILE: (gene_keys, "every gene defined in the supplied model"),
        REACTION_FILE: (reaction_keys, "every reaction defined in the supplied model"),
        DOUBLE_FILE: (double_keys, "all singleton and unordered pairwise reaction sets"),
        PFK_FILE: (set(PFK_LABELS), "exactly the four defined scenario labels"),
    }

    # load reference and submission tables
    ref = {}
    ref_errors = {}
    for name in ALL_FILES:
        table, err = _load(os.path.join(args.reference_dir, name))
        ref[name] = table
        ref_errors[name] = err

    sub = {}
    sub_errors = {}
    for name in ALL_FILES:
        table, err = _load(os.path.join(args.submission_dir, name))
        sub[name] = table
        sub_errors[name] = err

    # -------------------------------------------------------- structural checks
    structure_ids = {
        GENE_FILE: "structure_single_gene_table",
        REACTION_FILE: "structure_single_reaction_table",
        DOUBLE_FILE: "structure_double_reaction_table",
        PFK_FILE: "structure_pfk_table",
    }
    for name in ALL_FILES:
        check_id = structure_ids[name]
        want, description = expected[name]
        if sub_errors[name] is not None:
            record(check_id, False, sub_errors[name])
            continue
        if population_error is not None:
            record(check_id, False, population_error)
            continue
        keys = set(sub[name])
        if keys != want:
            missing = sorted(want - keys)
            extra = sorted(keys - want)
            detail = []
            if missing:
                detail.append("missing %d (e.g. %s)" % (len(missing), missing[:3]))
            if extra:
                detail.append("unexpected %d (e.g. %s)" % (len(extra), extra[:3]))
            record(
                check_id,
                False,
                "knockout key set does not cover %s: %s"
                % (description, "; ".join(detail)),
            )
            continue
        record(
            check_id,
            True,
            "%s: header, %d unique rows and the full knockout population are present"
            % (name, len(sub[name])),
        )

    # -------------------------------------------------------- scientific checks
    value_ids = {
        GENE_FILE: "values_single_gene_deletions",
        REACTION_FILE: "values_single_reaction_deletions",
        DOUBLE_FILE: "values_double_reaction_deletions",
        PFK_FILE: "values_pfk_knockout_optima",
    }
    for name in ALL_FILES:
        check_id = value_ids[name]
        if sub_errors[name] is not None:
            record(check_id, False, sub_errors[name])
            continue
        if ref_errors[name] is not None:
            record(check_id, False, "reference unreadable, comparison not performed: %s" % ref_errors[name])
            continue
        if population_error is not None:
            record(check_id, False, population_error)
            continue
        if set(sub[name]) != expected[name][0]:
            record(check_id, False, "key set invalid; see the structural check")
            continue
        problems = _compare(ref[name], sub[name])
        record(check_id, not problems, _summary(problems))

    # ---------------------------------------------------- cross-file consistency
    gene_t = sub[GENE_FILE] if sub_errors[GENE_FILE] is None else {}
    reaction_t = sub[REACTION_FILE] if sub_errors[REACTION_FILE] is None else {}
    double_t = sub[DOUBLE_FILE] if sub_errors[DOUBLE_FILE] is None else {}
    pfk_t = sub[PFK_FILE] if sub_errors[PFK_FILE] is None else {}
    problems = []
    if population_error is not None:
        problems.append(population_error)
    else:
        for rid in sorted(reaction_keys):
            left, right = double_t.get(rid), reaction_t.get(rid)
            if left is None or right is None:
                problems.append("missing key %s" % rid)
                continue
            if left[1] != right[1]:
                problems.append("%s: status %r vs single-reaction %r" % (rid, left[1], right[1]))
                continue
            if left[0] == "" or right[0] == "":
                if left[0] != right[0]:
                    problems.append("%s: growth presence differs between tables" % rid)
                continue
            lv, lerr = _parse_growth(left[0])
            rv, rerr = _parse_growth(right[0])
            if lerr or rerr or not _close(lv, rv):
                problems.append("%s: double-table singleton disagrees with single-reaction row" % rid)

        pairs = [
            ("", GENE_FILE, "b1723"),
            ("PFK", REACTION_FILE, "PFK"),
            ("b1723", GENE_FILE, "b1723"),
            ("b1723;b3916", REACTION_FILE, "PFK"),
        ]
        for pfk_label, other_file, other_key in pairs:
            other_t = gene_t if other_file == GENE_FILE else reaction_t
            left, right = pfk_t.get(pfk_label), other_t.get(other_key)
            if left is None or right is None:
                problems.append("missing key %r in %s relation" % (pfk_label, other_file))
                continue
            if left[1] != right[1]:
                problems.append("%s: status %r vs %s row %r" % (pfk_label, left[1], other_file, right[1]))
                continue
            if left[0] == "" or right[0] == "":
                if left[0] != right[0]:
                    problems.append("%s: growth presence differs from %s row" % (pfk_label, other_file))
                continue
            lv, lerr = _parse_growth(left[0])
            rv, rerr = _parse_growth(right[0])
            if lerr or rerr or not _close(lv, rv):
                problems.append("%s: growth disagrees with %s row" % (pfk_label, other_file))
    record("cross_table_consistency", not problems, _summary(problems))

    report = {
        "passed": all(passed for passed, _ in results.values()),
        "checks": [
            {"id": check_id, "passed": results[check_id][0], "message": results[check_id][1]}
            for check_id, _, _ in CHECKS
        ],
    }
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

