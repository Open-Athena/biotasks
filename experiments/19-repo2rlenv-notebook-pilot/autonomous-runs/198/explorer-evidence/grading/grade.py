#!/usr/bin/env python3
"""Acceptance grader for the AdK closed->open transition RMSD task.

Compares the five declared CSV outputs against the reference outputs as
parsed scientific values (row-by-row, frame-aligned). Standard library only.
"""
import argparse
import csv
import json
import math
import os
import sys

# Numeric acceptance bounds (documented in the public addendum):
ATOL_RMSD = 1e-5   # angstrom, absolute
RTOL_RMSD = 1e-6   # relative; the reference value is the denominator
ATOL_TIME = 1e-6   # picosecond, absolute

TRAJ_HEADERS = {
    "backbone_rmsd.csv": ["Frame", "Time (ps)", "Backbone", "CORE", "LID", "NMP"],
    "core_ca_rmsd.csv": ["Frame", "Time (ps)", "CORE"],
    "mass_weighted_rmsd.csv": ["Frame", "Time (ps)", "C-alphas", "CORE", "LID", "NMP"],
    "resid_weighted_rmsd.csv": ["Frame", "Time (ps)", "C-alphas", "CORE", "LID", "NMP"],
}
SINGLE_HEADERS = {"open_closed_backbone_rmsd.csv": ["backbone_rmsd_angstrom"]}
ALL_FILES = sorted(list(TRAJ_HEADERS) + list(SINGLE_HEADERS))


def parse_table(path, expected_header):
    """Parse one CSV. Return (rows_or_None, problems).

    rows[i] is a list of floats for data row i (header excluded), or None
    when that row could not be parsed into finite numbers.
    """
    problems = []
    if not os.path.isfile(path):
        return None, ["missing file"]
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            raw = list(csv.reader(fh))
    except Exception as exc:
        return None, ["unreadable (%s)" % type(exc).__name__]
    if not raw:
        return None, ["empty file"]
    header = [h.strip() for h in raw[0]]
    expected = list(expected_header)
    if header != expected:
        return None, ["header mismatch"]
    ncol = len(header)
    rows = []
    for i, row in enumerate(raw[1:], start=1):
        if len(row) != ncol:
            problems.append("row %d: %d fields (expected %d)" % (i, len(row), ncol))
            rows.append(None)
            continue
        vals = []
        bad = False
        for cell in row:
            try:
                v = float(cell.strip())
            except ValueError:
                bad = True
                break
            if not math.isfinite(v):
                bad = True
                break
            vals.append(v)
        rows.append(None if bad else vals)
        if bad:
            problems.append("row %d: empty, non-numeric or non-finite cell" % i)
    if not rows:
        problems.append("no data rows")
        return None, problems
    return rows, problems


def close_rmsd(sub, ref):
    return abs(sub - ref) <= ATOL_RMSD or abs(sub - ref) <= RTOL_RMSD * abs(ref)


def check_structure(sub_dir, ref_dir):
    problems = []
    counts = {}
    for name in ALL_FILES:
        expected = TRAJ_HEADERS.get(name) or SINGLE_HEADERS[name]
        rows, probs = parse_table(os.path.join(sub_dir, name), expected)
        for p in probs[:2]:
            problems.append("%s: %s" % (name, p))
        if rows is not None:
            counts[name] = len(rows)
            if name in SINGLE_HEADERS and len(rows) != 1:
                problems.append("%s: %d data rows (expected exactly 1)"
                                % (name, len(rows)))
    traj = list(TRAJ_HEADERS)
    have = [counts.get(n) for n in traj]
    if all(c is not None for c in have) and len(set(have)) > 1:
        problems.append("trajectory tables have differing row counts: %s" % counts)
    if problems:
        return False, "; ".join(problems[:6])
    return True, ("all five CSV outputs exist at the declared paths with the declared "
                  "headers, uniform field counts and finite numeric values; the "
                  "open-vs-closed table has exactly one data row and the four "
                  "trajectory tables share a common row count")


def check_open_closed(sub_dir, ref_dir):
    name = "open_closed_backbone_rmsd.csv"
    expected = SINGLE_HEADERS[name]
    sub_rows, sub_p = parse_table(os.path.join(sub_dir, name), expected)
    ref_rows, ref_p = parse_table(os.path.join(ref_dir, name), expected)
    if sub_rows is None or ref_rows is None:
        return False, "%s: %s" % (name, "; ".join((sub_p + ref_p)[:2]) or "unparseable")
    if len(sub_rows) != len(ref_rows):
        return False, "%s: %d data rows (expected %d)" % (name, len(sub_rows),
                                                          len(ref_rows))
    s, r = sub_rows[0][0], ref_rows[0][0]
    if s < 0:
        return False, "%s: negative RMSD value" % name
    if not close_rmsd(s, r):
        return False, ("%s: open-vs-closed backbone RMSD %r differs from the "
                       "reference value beyond the stated tolerance" % (name, s))
    return True, ("%s: open-vs-closed backbone RMSD matches the reference value "
                  "within the stated tolerance" % name)


def make_traj_check(name):
    def run(sub_dir, ref_dir):
        expected = TRAJ_HEADERS[name]
        sub_rows, sub_p = parse_table(os.path.join(sub_dir, name), expected)
        ref_rows, ref_p = parse_table(os.path.join(ref_dir, name), expected)
        if sub_rows is None or ref_rows is None:
            return False, "%s: %s" % (name, "; ".join((sub_p + ref_p)[:2])
                                     or "unparseable")
        n = len(ref_rows)
        if len(sub_rows) != n:
            return False, ("%s: %d data rows (expected %d, one per trajectory "
                          "frame)" % (name, len(sub_rows), n))
        ncol = len(expected)
        for i in range(n):
            s, r = sub_rows[i], ref_rows[i]
            if s is None or r is None:
                return False, "%s: row %d could not be parsed" % (name, i)
            if s[0] != i or s[0] != r[0] or s[0] != int(s[0]):
                return False, ("%s: row %d Frame %r is not this row's 0-based "
                              "trajectory frame index" % (name, i, s[0]))
            if abs(s[1] - r[1]) > ATOL_TIME:
                return False, ("%s: row %d Time %r ps differs from the reference %r ps "
                               "by more than %g ps" % (name, i, s[1], r[1], ATOL_TIME))
            for ci in range(2, ncol):
                sv, rv = s[ci], r[ci]
                if sv < 0:
                    return False, "%s: row %d column %s is negative" \
                        % (name, i, expected[ci])
                if not close_rmsd(sv, rv):
                    return False, ("%s: row %d column %s value %r differs from the "
                                   "reference %r beyond the stated tolerance"
                                   % (name, i, expected[ci], sv, rv))
        return True, ("%s: all %d rows match the reference frame indices, times and "
                      "per-frame RMSD values within the stated tolerances"
                      % (name, n))
    return run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    checks = [
        ("structural_schema", check_structure),
        ("open_closed_backbone_rmsd", check_open_closed),
        ("backbone_rmsd", make_traj_check("backbone_rmsd.csv")),
        ("core_ca_rmsd", make_traj_check("core_ca_rmsd.csv")),
        ("mass_weighted_rmsd", make_traj_check("mass_weighted_rmsd.csv")),
        ("resid_weighted_rmsd", make_traj_check("resid_weighted_rmsd.csv")),
    ]

    results = []
    for cid, fn in checks:
        try:
            ok, msg = fn(args.submission_dir, args.reference_dir)
        except Exception as exc:
            ok, msg = False, "grader error (%s: %s)" % (type(exc).__name__, exc)
        results.append({"id": cid, "passed": bool(ok), "message": msg})

    report = {"passed": all(r["passed"] for r in results), "checks": results}
    with open(args.report, "w") as fh:
        json.dump(report, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())

