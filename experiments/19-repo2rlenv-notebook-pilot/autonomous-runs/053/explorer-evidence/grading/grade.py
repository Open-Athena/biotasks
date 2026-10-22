#!/usr/bin/env python3
"""Deterministic scientific grader for the adenylate-kinase RMSD task.

Reads the five declared CSV outputs from the reference and submission
directories, validates their structure, and compares the parsed scientific
content (frame series and RMSD values in Angstrom) against the reference.

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH

The report JSON has exactly the keys {"passed", "checks"}; each check has the
keys {"id", "passed", "message"}. Every declared check is emitted exactly once,
also for missing, malformed or empty submissions. The grader never modifies
reference or submission files and never imports submission code.
"""

import argparse
import csv
import json
import math
import os
import re

SINGLE_OUTPUT = ("rmsd_backbone_open_closed.csv",
                 ("rmsd_backbone_angstrom",))

TRAJECTORY_OUTPUTS = [
    ("rmsd_backbone_domains.csv",
     ("frame", "rmsd_backbone_angstrom", "rmsd_core_angstrom",
      "rmsd_lid_angstrom", "rmsd_nmp_angstrom")),
    ("rmsd_ca_core.csv",
     ("frame", "rmsd_core_ca_angstrom")),
    ("rmsd_mass_weighted.csv",
     ("frame", "rmsd_ca_mass_angstrom", "rmsd_core_mass_angstrom",
      "rmsd_lid_mass_angstrom", "rmsd_nmp_mass_angstrom")),
    ("rmsd_resid_weighted.csv",
     ("frame", "rmsd_ca_resid_angstrom", "rmsd_core_resid_angstrom",
      "rmsd_lid_resid_angstrom", "rmsd_nmp_resid_angstrom")),
]

# Numeric acceptance rule: PASS iff |v - r| <= TOL_ABS + TOL_REL * |r|,
# with r the reference value (inclusive bound).
TOL_ABS = 1e-5   # Angstrom
TOL_REL = 1e-9

_NUMPY_FLOAT64_REPR = re.compile(r"^np\.float64\((.*)\)$", re.DOTALL)


class TableError(Exception):
    """Missing, malformed or invalid CSV output."""


def parse_number(cell):
    """Return the finite float denoted by a CSV cell, or None."""
    if cell is None:
        return None
    text = cell.strip()
    if not text:
        return None
    match = _NUMPY_FLOAT64_REPR.match(text)
    if match:
        text = match.group(1).strip()
        if not text:
            return None
    try:
        value = float(text)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(value):
        return None
    return value


def allowance(reference):
    """Maximum accepted |v - reference| for a reference value."""
    return TOL_ABS + TOL_REL * abs(reference)


def read_csv_table(directory, filename):
    path = os.path.join(directory, filename)
    if not os.path.isfile(path):
        raise TableError("%s: file not found under the supplied output root"
                         % filename)
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            table = [row for row in csv.reader(handle)]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise TableError("%s: cannot be read as CSV (%s)" % (filename, exc))
    if not table:
        raise TableError("%s: file has no header row" % filename)
    return table[0], table[1:]


def load_single_output(directory):
    """Load and validate the single-value endpoint (analysis A)."""
    filename, columns = SINGLE_OUTPUT
    header, rows = read_csv_table(directory, filename)
    if list(header) != list(columns):
        raise TableError("%s: header must be exactly %s"
                         % (filename, list(columns)))
    if len(rows) != 1:
        raise TableError("%s: expected exactly 1 data row, found %d"
                         % (filename, len(rows)))
    row = rows[0]
    if len(row) != len(columns):
        raise TableError("%s: data row has %d fields, expected %d"
                         % (filename, len(row), len(columns)))
    value = parse_number(row[0])
    if value is None:
        raise TableError("%s: value %r does not parse as a finite number"
                         % (filename, row[0]))
    return value


def load_trajectory_output(directory, filename, columns):
    """Load and validate one per-frame endpoint (analyses B-E)."""
    header, rows = read_csv_table(directory, filename)
    if list(header) != list(columns):
        raise TableError("%s: header must be exactly %s"
                         % (filename, list(columns)))
    if not rows:
        raise TableError("%s: file has no data rows" % filename)
    n_columns = len(columns)
    frames = []
    values = []
    for position, row in enumerate(rows):
        if len(row) != n_columns:
            raise TableError("%s: data row %d has %d fields, expected %d"
                             % (filename, position + 1, len(row), n_columns))
        frame_value = parse_number(row[0])
        if frame_value is None:
            raise TableError("%s: data row %d: frame %r is not a finite number"
                             % (filename, position + 1, row[0]))
        frame = int(frame_value)
        if frame != frame_value:
            raise TableError("%s: data row %d: frame %r is not an integer"
                             % (filename, position + 1, row[0]))
        frames.append(frame)
        row_values = []
        for index in range(1, n_columns):
            cell = row[index]
            value = parse_number(cell)
            if value is None:
                raise TableError(
                    "%s: data row %d, column %r: %r is not a finite number"
                    % (filename, position + 1, columns[index], cell))
            row_values.append(value)
        values.append(row_values)
    if frames != list(range(len(frames))):
        raise TableError(
            "%s: frame column must be the complete strictly increasing "
            "0-based frame series 0..%d (one row per trajectory frame)"
            % (filename, len(rows) - 1))
    return frames, values


def check_open_closed(reference_dir, submission_dir):
    reference_value = load_single_output(reference_dir)
    submission_value = load_single_output(submission_dir)
    if submission_value < 0:
        return False, ("rmsd_backbone_angstrom = %.12g is negative; RMSD "
                       "values must be nonnegative" % submission_value)
    deviation = abs(submission_value - reference_value)
    if deviation > allowance(reference_value):
        return False, ("rmsd_backbone_angstrom = %.12g deviates from the "
                      "reference by %.3g A, exceeding the accepted %.3g A"
                      % (submission_value, deviation,
                         allowance(reference_value)))
    return True, ("single value agrees with the reference within the "
                  "accepted bound (%.3g A)" % allowance(reference_value))


def check_trajectory_output(reference_dir, submission_dir, filename, columns):
    ref_frames, ref_values = load_trajectory_output(reference_dir, filename,
                                                    columns)
    sub_frames, sub_values = load_trajectory_output(submission_dir, filename,
                                                     columns)
    if len(sub_frames) != len(ref_frames):
        return False, ("%s: expected %d data rows (one per trajectory "
                       "frame), found %d"
                       % (filename, len(ref_frames), len(sub_frames)))
    value_columns = columns[1:]
    for row_index in range(len(ref_frames)):
        frame = ref_frames[row_index]
        for column_index, column in enumerate(value_columns):
            reference = ref_values[row_index][column_index]
            value = sub_values[row_index][column_index]
            if value < 0:
                return False, ("%s: frame %d, column %s: value %.12g is "
                               "negative; RMSD values must be nonnegative"
                               % (filename, frame, column, value))
            deviation = abs(value - reference)
            if deviation > allowance(reference):
                return False, ("%s: frame %d, column %s: value %.12g deviates "
                               "from the reference by %.3g A, exceeding the "
                               "accepted %.3g A"
                               % (filename, frame, column, value, deviation,
                                  allowance(reference)))
    return True, ("%s: header, all %d frames and all %d value columns agree "
                  "with the reference"
                  % (filename, len(ref_frames), len(value_columns)))


def check_frame_series(reference_dir, submission_dir):
    reference_series = None
    for filename, columns in TRAJECTORY_OUTPUTS:
        frames, _ = load_trajectory_output(reference_dir, filename, columns)
        if reference_series is None:
            reference_series = frames
        elif frames != reference_series:
            raise TableError("%s: reference frame series is inconsistent "
                             "with the other reference tables" % filename)
    for filename, columns in TRAJECTORY_OUTPUTS:
        frames, _ = load_trajectory_output(submission_dir, filename, columns)
        if frames != reference_series:
            return False, ("%s: frame series does not match the shared frame "
                           "series of the trajectory tables" % filename)
    return True, ("all four trajectory tables carry the identical complete "
                  "0-based frame series")


def grade(reference_dir, submission_dir):
    check_functions = [
        ("open_closed_rmsd", check_open_closed),
        ("backbone_fit_domain_rmsd",
         lambda ref, sub: check_trajectory_output(ref, sub,
                                                   *TRAJECTORY_OUTPUTS[0])),
        ("ca_core_rmsd",
         lambda ref, sub: check_trajectory_output(ref, sub,
                                                   *TRAJECTORY_OUTPUTS[1])),
        ("mass_weighted_rmsd",
         lambda ref, sub: check_trajectory_output(ref, sub,
                                                   *TRAJECTORY_OUTPUTS[2])),
        ("resid_weighted_rmsd",
         lambda ref, sub: check_trajectory_output(ref, sub,
                                                   *TRAJECTORY_OUTPUTS[3])),
        ("trajectory_frame_series", check_frame_series),
    ]
    results = []
    for check_id, func in check_functions:
        try:
            passed, message = func(reference_dir, submission_dir)
        except TableError as exc:
            passed, message = False, str(exc)
        except Exception as exc:  # defensive: the grader must not crash
            passed, message = False, "internal grading error: %s" % exc
        results.append({"id": check_id, "passed": bool(passed),
                        "message": str(message)})
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Grade the adenylate-kinase RMSD task outputs.")
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    checks = grade(args.reference_dir, args.submission_dir)
    report = {"passed": all(entry["passed"] for entry in checks),
              "checks": checks}
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

