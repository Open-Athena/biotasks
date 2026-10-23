#!/usr/bin/env python
"""Deterministic grader for the AdK domain-motion RMSD task.

Reads reference_dir/<path> and submission_dir/<path> for the five declared
output files, compares parsed scientific content, and writes a JSON report.
No answer values, dimensions or hashes are embedded; comparisons are relative
to values read from the reference directory.
"""
import argparse
import csv
import json
import math
import os
import sys

TRAJECTORY_FILES = ["backbone_rmsd.csv", "core_ca_rmsd.csv",
                    "mass_weighted_rmsd.csv", "resid_weighted_rmsd.csv"]
EXPECTED_HEADERS = {
    "backbone_rmsd.csv": ["Frame", "Time (ns)", "Backbone", "CORE", "LID", "NMP"],
    "core_ca_rmsd.csv": ["Frame", "Time (ns)", "CORE"],
    "mass_weighted_rmsd.csv": ["Frame", "Time (ns)", "C-alphas", "CORE", "LID", "NMP"],
    "resid_weighted_rmsd.csv": ["Frame", "Time (ns)", "C-alphas", "CORE", "LID", "NMP"],
}

# Tolerance limits on observable output differences (see rationale):
RMSD_ABSTOL = 3.0e-6   # Angstrom, absolute
RMSD_RELTOL = 1.0e-9   # relative to |reference value|
TIME_ABSTOL = 1.0e-9   # ns
FRAME_ABSTOL = 1.0e-9

REPORT = {"passed": False, "checks": []}


def fail(check_id, message):
    REPORT["checks"].append({"id": check_id, "passed": False, "message": message})


def ok(check_id, message):
    REPORT["checks"].append({"id": check_id, "passed": True, "message": message})


def parse_csv(path):
    """Parse a CSV file into (header, rows-of-string-lists).

    Rejects ragged rows, duplicate/garbled parsing, stray bytes, or any
    ill-formed content. Only strict RFC-style comma separation is accepted.
    """
    if not os.path.isfile(path):
        raise ValueError("missing file: %s" % os.path.basename(path))
    with open(path, "r", newline="") as fh:
        text = fh.read()
    if "\x00" in text:
        raise ValueError("file contains NUL bytes")
    reader = csv.reader(text.splitlines())
    records = [r for r in reader if r]  # drop fully empty trailing lines only
    if not records:
        raise ValueError("empty file")
    header = records[0]
    if len(records) == 1:
        raise ValueError("no data rows")
    for i, r in enumerate(records[1:], start=2):
        if len(r) != len(header):
            raise ValueError("ragged row at line %d" % i)
    return header, records[1:]


def to_float(s, what):
    t = s.strip()
    if t != s:
        raise ValueError("%s: value %r has surrounding whitespace" % (what, s))
    if not t:
        raise ValueError("%s: empty numeric field %r" % (what, s))
    if t.lower() in ("nan", "-nan", "+nan", "inf", "infinity", "-inf",
                     "+inf", "-infinity", "+infinity"):
        raise ValueError("%s: nonfinite value %r" % (what, s))
    try:
        v = float(t)
    except ValueError:
        raise ValueError("%s: not a valid number: %r" % (what, s))
    if not math.isfinite(v):
        raise ValueError("%s: nonfinite value %r" % (what, s))
    return v


def compare_tables(ref_dir, sub_dir):
    """Compare the four per-frame tables value by value after parsing."""
    problems = {}
    for name in TRAJECTORY_FILES:
        exp_header = EXPECTED_HEADERS[name]
        try:
            _rh, rrows = parse_csv(os.path.join(ref_dir, name))
        except ValueError:
            continue  # reference rendering issue is out of scope here
        try:
            sh, srows = parse_csv(os.path.join(sub_dir, name))
        except ValueError as e:
            problems.setdefault(name, []).append("submission unreadable: %s" % e)
            continue
        if sh != exp_header:
            problems.setdefault(name, []).append(
                "header %r does not match required %r" % (sh, exp_header))
            continue
        if len(rrows) != len(srows):
            problems.setdefault(name, []).append(
                "row count %d != reference %d (one row per trajectory frame is "
                "required, with no extra or missing frames)" % (len(srows), len(rrows)))
            continue
        n_bad = 0
        first_msgs = []
        for row_idx, (rr, sr) in enumerate(zip(rrows, srows)):
            try:
                sframe = to_float(sr[0], "%s row %d Frame" % (name, row_idx))
            except ValueError as e:
                n_bad += 1
                if len(first_msgs) < 3:
                    first_msgs.append(str(e))
                continue
            if abs(sframe - row_idx) > FRAME_ABSTOL:
                n_bad += 1
                if len(first_msgs) < 3:
                    first_msgs.append("row %d: Frame %r is not the 0-based frame "
                                      "index" % (row_idx, sr[0]))
                continue
            for col_idx in range(1, len(exp_header)):
                col = exp_header[col_idx]
                try:
                    rv = to_float(rr[col_idx], "%s ref row %d %s" % (name, row_idx, col))
                    sv = to_float(sr[col_idx], "%s row %d %s" % (name, row_idx, col))
                except ValueError as e:
                    n_bad += 1
                    if len(first_msgs) < 3:
                        first_msgs.append(str(e))
                    continue
                if col == "Time (ns)":
                    tol = TIME_ABSTOL
                else:
                    tol = max(RMSD_ABSTOL, RMSD_RELTOL * abs(rv))
                if abs(sv - rv) > tol:
                    n_bad += 1
                    if len(first_msgs) < 3:
                        first_msgs.append(
                            "row %d column %s: submission %s vs reference %s "
                            "(diff %.3g exceeds limit %.3g)"
                            % (row_idx, col, sr[col_idx], rr[col_idx],
                               abs(sv - rv), tol))
        if n_bad:
            problems.setdefault(name, []).extend(first_msgs)

    # ---- structural check over the four tables ----
    files_present = [n for n in TRAJECTORY_FILES
                     if os.path.isfile(os.path.join(sub_dir, n))]
    specific = []
    for n in TRAJECTORY_FILES:
        specific.extend("%s: %s" % (n, m) for m in problems.get(n, []))
    if len(files_present) != len(TRAJECTORY_FILES) or specific:
        fail("trajectory_tables_structure",
             "missing/unreadable or malformed files: %s"
             % ("; ".join(specific) if specific else
                ("missing %s" % ", ".join(set(TRAJECTORY_FILES) - set(files_present)) or "none")))
    else:
        ok("trajectory_tables_structure",
           "all four trajectory tables present with correct headers, row counts "
           "and frame indexing")

    # ---- per-file scientific checks (full column coverage) ----
    sci = {
        "backbone_domain_rmsd": ["backbone_rmsd.csv"],
        "core_ca_rmsd": ["core_ca_rmsd.csv"],
        "mass_weighted_rmsd": ["mass_weighted_rmsd.csv"],
        "resid_weighted_rmsd": ["resid_weighted_rmsd.csv"],
    }
    for cid, files in sci.items():
        bad = []
        for n in files:
            bad.extend("%s: %s" % (n, m) for m in problems.get(n, []))
        if bad:
            fail(cid, "; ".join(bad[:3]))
        else:
            ok(cid, "%s matches the reference within the stated tolerances" % ", ".join(files))

    # ---- Time column cross-consistency across the four tables ----
    time_bad = []
    parsed = {}
    for name in TRAJECTORY_FILES:
        try:
            _h, rows = parse_csv(os.path.join(sub_dir, name))
            parsed[name] = rows
        except ValueError:
            time_bad.append("%s unreadable" % name)
    if len(parsed) == len(TRAJECTORY_FILES) and \
            len(set(len(r) for r in parsed.values())) == 1:
        n_rows = len(next(iter(parsed.values())))
        for i in range(n_rows):
            vals = set()
            for name in TRAJECTORY_FILES:
                try:
                    v = to_float(parsed[name][i][1], "%s row %d Time" % (name, i))
                except ValueError as e:
                    time_bad.append(str(e))
                    vals = None
                    break
                vals.add(v)
            if vals is not None and len(vals) > 1:
                time_bad.append("row %d: Time values differ across tables: %s"
                                % (i, sorted(vals)))
                if len(time_bad) > 3:
                    break
    else:
        if not time_bad:
            time_bad.append("row counts differ across the four trajectory tables")
    if time_bad:
        fail("time_column_consistency", "; ".join(time_bad[:3]))
    else:
        ok("time_column_consistency",
           "identical Time (ns) value per frame across all four trajectory tables")


def compare_open_closed(ref_dir, sub_dir):
    name = "open_closed_backbone_rmsd.csv"
    try:
        _rh, rrows = parse_csv(os.path.join(ref_dir, name))
    except ValueError as e:
        fail("open_closed_rmsd_structure", "reference unreadable: %s" % e)
        fail("open_closed_rmsd_value", "reference unreadable: %s" % e)
        return

    problems = None
    value_msg = None
    try:
        sh, srows = parse_csv(os.path.join(sub_dir, name))
        if sh != ["backbone_rmsd_angstrom"]:
            problems = "header %r does not match required ['backbone_rmsd_angstrom']" % sh
        elif len(srows) != 1:
            problems = "expected exactly one data row, found %d" % len(srows)
        else:
            rv = to_float(rrows[0][0], "reference value")
            sv = to_float(srows[0][0], "submission value")
            tol = max(RMSD_ABSTOL, RMSD_RELTOL * abs(rv))
            if abs(sv - rv) > tol:
                value_msg = ("submitted value %s vs reference %s (diff %.3g exceeds "
                             "limit %.3g)" % (srows[0][0], rrows[0][0], abs(sv - rv), tol))
    except ValueError as e:
        problems = str(e)

    struct_ok = problems is None
    if struct_ok:
        ok("open_closed_rmsd_structure",
           "open_closed_backbone_rmsd.csv present with the required single-row schema")
    else:
        fail("open_closed_rmsd_structure", problems)
    if value_msg is not None:
        fail("open_closed_rmsd_value", value_msg)
    elif struct_ok:
        ok("open_closed_rmsd_value", "static open-vs-closed RMSD within tolerance")
    else:
        fail("open_closed_rmsd_value",
             "no parseable single RMSD value to compare (missing or malformed file)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    compare_tables(args.reference_dir, args.submission_dir)
    compare_open_closed(args.reference_dir, args.submission_dir)

    REPORT["passed"] = all(c["passed"] for c in REPORT["checks"])
    with open(args.report, "w") as fh:
        json.dump(REPORT, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

