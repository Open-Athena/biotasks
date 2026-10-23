#!/usr/bin/env python3
"""Deterministic grader for the HRV-of-resting-ECG task.

Compares the four required CSV tables (hrv_time.csv, hrv_frequency.csv,
hrv_nonlinear.csv, hrv_indices.csv) between a reference directory and a
submission directory on parsed scientific content:

  - exact expected column sets (extra/missing/renamed columns rejected),
  - exactly one data row,
  - empty-field ("not defined for this recording") agreement; a whitespace-only
    cell is NOT an empty field and is rejected,
  - populated fields must be plain decimal representations of one finite
    floating-point number (optional sign, optional decimal point, optional
    decimal exponent; no surrounding whitespace, no underscore separators,
    no nan/inf/hex text),
  - numeric values compared with a relative tolerance of 1e-9 with an
    absolute floor of 1e-12 (per non-empty reference cell),
  - the combined hrv_indices.csv must match the per-domain tables
    column-by-column (cross-table consistency).

Exit code 0 with a JSON report at --report in every case (pass or fail).
"""

import argparse
import csv
import json
import math
import os
import re

REL_TOL = 1e-9
ABS_TOL = 1e-12

# Plain decimal grammar for one finite floating-point number: optional sign,
# digits with an optional decimal point and/or a decimal exponent. Deliberately
# excludes surrounding whitespace, underscore separators (Python float()
# accepts "1_000.5"), nan/inf/-inf text, and hexadecimal/binary literals.
NUMBER_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)

TIME_COLS = [
    "HRV_MeanNN", "HRV_SDNN", "HRV_SDANN1", "HRV_SDNNI1", "HRV_SDANN2",
    "HRV_SDNNI2", "HRV_SDANN5", "HRV_SDNNI5", "HRV_RMSSD", "HRV_SDSD",
    "HRV_CVNN", "HRV_CVSD", "HRV_MedianNN", "HRV_MadNN", "HRV_MCVNN",
    "HRV_IQRNN", "HRV_SDRMSSD", "HRV_Prc20NN", "HRV_Prc80NN", "HRV_pNN50",
    "HRV_pNN20", "HRV_MinNN", "HRV_MaxNN", "HRV_HTI", "HRV_TINN",
]
FREQ_COLS = [
    "HRV_ULF", "HRV_VLF", "HRV_LF", "HRV_HF", "HRV_VHF", "HRV_TP",
    "HRV_LFHF", "HRV_LFn", "HRV_HFn", "HRV_LnHF",
]
NONLINEAR_COLS = [
    "HRV_SD1", "HRV_SD2", "HRV_SD1SD2", "HRV_S", "HRV_CSI", "HRV_CVI",
    "HRV_CSI_Modified", "HRV_PIP", "HRV_IALS", "HRV_PSS", "HRV_PAS",
    "HRV_GI", "HRV_SI", "HRV_AI", "HRV_PI", "HRV_C1d", "HRV_C1a",
    "HRV_SD1d", "HRV_SD1a", "HRV_C2d", "HRV_C2a", "HRV_SD2d", "HRV_SD2a",
    "HRV_Cd", "HRV_Ca", "HRV_SDNNd", "HRV_SDNNa", "HRV_DFA_alpha1",
    "HRV_MFDFA_alpha1_Width", "HRV_MFDFA_alpha1_Peak",
    "HRV_MFDFA_alpha1_Mean", "HRV_MFDFA_alpha1_Max",
    "HRV_MFDFA_alpha1_Delta", "HRV_MFDFA_alpha1_Asymmetry",
    "HRV_MFDFA_alpha1_Fluctuation", "HRV_MFDFA_alpha1_Increment",
    "HRV_DFA_alpha2", "HRV_MFDFA_alpha2_Width", "HRV_MFDFA_alpha2_Peak",
    "HRV_MFDFA_alpha2_Mean", "HRV_MFDFA_alpha2_Max", "HRV_MFDFA_alpha2_Delta",
    "HRV_MFDFA_alpha2_Asymmetry", "HRV_MFDFA_alpha2_Fluctuation",
    "HRV_MFDFA_alpha2_Increment", "HRV_ApEn", "HRV_SampEn", "HRV_ShanEn",
    "HRV_FuzzyEn", "HRV_MSEn", "HRV_CMSEn", "HRV_RCMSEn", "HRV_CD",
    "HRV_HFD", "HRV_KFD", "HRV_LZC", "HRV_Symbolic_EqualProb4_0V",
    "HRV_Symbolic_EqualProb4_1V", "HRV_Symbolic_EqualProb4_2LV",
    "HRV_Symbolic_EqualProb4_2UV",
]
INDICES_COLS = TIME_COLS + FREQ_COLS + NONLINEAR_COLS

EXPECTED_COLUMNS = {
    "hrv_time.csv": TIME_COLS,
    "hrv_frequency.csv": FREQ_COLS,
    "hrv_nonlinear.csv": NONLINEAR_COLS,
    "hrv_indices.csv": INDICES_COLS,
}

DOMAIN_FILES = ("hrv_time.csv", "hrv_frequency.csv", "hrv_nonlinear.csv")

CHECK_IDS = (
    "time_domain_indices", "frequency_domain_indices",
    "nonlinear_domain_indices", "combined_indices_table",
    "cross_table_consistency",
)

MAX_EXAMPLES = 5


class ParseError(Exception):
    """The table file could not be interpreted as the expected table."""


def read_table(path, expected_columns, label):
    """Parse a one-row CSV into {column: float_or_None}.

    Raises ParseError on any structural deviation (missing file, wrong
    encoding, ragged rows, wrong row count, bad header, extra/missing
    columns, whitespace-only or non-decimal-grammar cells, non-numeric or
    nonfinite data).
    """
    if not os.path.isfile(path):
        raise ParseError("%s not found at the declared path" % label)
    try:
        with open(path, "r", encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.reader(fh) if r]
    except (OSError, UnicodeDecodeError) as exc:
        raise ParseError("%s unreadable as UTF-8 CSV: %s" % (label, exc))

    if len(rows) < 2:
        raise ParseError("%s has no data row (header-only or empty file)" % label)
    if len(rows) > 2:
        raise ParseError("%s must have exactly one data row, found %d"
                         % (label, len(rows) - 1))
    header, data = rows[0], rows[1]
    if len(header) != len(data):
        raise ParseError("%s has a ragged row: %d header fields vs %d data fields"
                         % (label, len(header), len(data)))
    if len(set(header)) != len(header):
        raise ParseError("%s has duplicate column names" % label)

    header_set = set(header)
    expected_set = set(expected_columns)
    if header_set != expected_set:
        missing = sorted(expected_set - header_set)
        if missing:
            raise ParseError("%s is missing column(s): %s"
                             % (label, ", ".join(missing[:5])))
        extra = sorted(header_set - expected_set)
        if extra:
            raise ParseError("%s has unexpected extra column(s): %s"
                             % (label, ", ".join(extra[:5])))

    table = {}
    for name, raw in zip(header, data):
        if raw == "":
            # A truly empty field: "not defined for this recording".
            table[name] = None
            continue
        if NUMBER_RE.match(raw) is None:
            # Not a plain decimal token: give a specific diagnostic for the
            # common nonfinite spellings, otherwise report the grammar issue
            # (which also covers whitespace-only cells, whitespace padding
            # and underscore separators that Python float() would accept).
            stripped = raw.strip()
            try:
                probe = float(stripped)
            except (ValueError, TypeError):
                probe = None
            if probe is not None and not math.isfinite(probe):
                raise ParseError(
                    "%s column %s has nonfinite value %r (an empty field must "
                    "be used for an undefined value instead)"
                    % (label, name, raw))
            if stripped == "":
                raise ParseError(
                    "%s column %s is whitespace-only, which is not an empty "
                    "field and not a number (use a truly empty field for "
                    "undefined values)"
                    % (label, name))
            raise ParseError(
                "%s column %s is not a plain decimal representation of one "
                "finite floating-point number: %r"
                % (label, name, raw))
        value = float(raw)
        if not math.isfinite(value):
            # Grammar-matching but overflowing literals such as "1e999".
            raise ParseError("%s column %s is nonfinite" % (label, name))
        table[name] = value
    return table


def compare_cells(ref_table, sub_table):
    """Cell-wise comparison; returns a list of (column, description) problems."""
    bad = []
    for name in sorted(ref_table):
        ref_value = ref_table[name]
        sub_value = sub_table.get(name)
        if ref_value is None and sub_value is None:
            continue
        if ref_value is None or sub_value is None:
            if ref_value is None:
                bad.append((name, "reference is empty (not defined for this "
                                  "recording) but the submission provides %r"
                                  % (sub_value,)))
            else:
                bad.append((name, "submission is empty but the reference has %r"
                                  % (ref_value,)))
            continue
        difference = abs(ref_value - sub_value)
        allowed = REL_TOL * abs(ref_value)
        if allowed < ABS_TOL:
            allowed = ABS_TOL
        if difference > allowed:
            bad.append((name, "reference %r vs submission %r "
                              "(|diff| %.17g > tolerance %.17g)"
                              % (ref_value, sub_value, difference, allowed)))
    return bad


def first_n(problems, n):
    return ["%s: %s" % (name, description) for name, description in problems[:n]]


def grade(reference_dir, submission_dir):
    ref_tables = {}
    sub_tables = {}
    parse_failures = {}
    value_problems = {}

    for filename, expected_columns in EXPECTED_COLUMNS.items():
        ref_path = os.path.join(reference_dir, filename)
        sub_path = os.path.join(submission_dir, filename)
        try:
            ref_table = read_table(ref_path, expected_columns,
                                   "reference " + filename)
        except ParseError as exc:
            # The reference itself is unusable; this is a validation-side
            # defect and cannot be attributed to the submission.
            message = "reference table unusable: %s" % exc
            return {
                "passed": False,
                "checks": [{"id": check_id, "passed": False,
                            "message": message} for check_id in CHECK_IDS],
            }
        ref_tables[filename] = ref_table
        try:
            sub_tables[filename] = read_table(sub_path, expected_columns,
                                              filename)
            parse_failures[filename] = None
        except ParseError as exc:
            parse_failures[filename] = str(exc)
            sub_tables[filename] = None
        value_problems[filename] = (
            compare_cells(ref_tables[filename], sub_tables[filename])
            if sub_tables[filename] is not None else []
        )

    # Cross-table consistency inside the submission: hrv_indices vs the three
    # per-domain tables. It can only be verified when all four files parsed;
    # a missing, malformed or misplaced table leaves the relation unsatisfied.
    cross_problems = []
    if not all(parse_failures[f] is None for f in EXPECTED_COLUMNS):
        cross_problems.append(
            ("hrv_indices.csv", "cross-table consistency cannot be verified: "
             "not all of hrv_time.csv, hrv_frequency.csv, hrv_nonlinear.csv "
             "and hrv_indices.csv were readable at the declared paths"))
    else:
        indices_sub = sub_tables["hrv_indices.csv"]
        for domain_name in DOMAIN_FILES:
            domain_sub = sub_tables[domain_name]
            for col in EXPECTED_COLUMNS[domain_name]:
                idx_value = indices_sub.get(col)
                dom_value = domain_sub.get(col)
                if idx_value is None and dom_value is None:
                    continue
                if idx_value is None or dom_value is None:
                    same = False
                else:
                    allowed = REL_TOL * max(abs(idx_value), abs(dom_value))
                    if allowed < ABS_TOL:
                        allowed = ABS_TOL
                    same = abs(idx_value - dom_value) <= allowed
                if not same:
                    cross_problems.append(
                        (col, "hrv_indices.csv value %r does not match the %s "
                              "value %r" % (idx_value, domain_name, dom_value)))

    per_file = [
        ("time_domain_indices", "hrv_time.csv"),
        ("frequency_domain_indices", "hrv_frequency.csv"),
        ("nonlinear_domain_indices", "hrv_nonlinear.csv"),
        ("combined_indices_table", "hrv_indices.csv"),
    ]
    checks = []
    for check_id, filename in per_file:
        if parse_failures[filename] is not None:
            message = "%s: %s" % (filename, parse_failures[filename])
            passed = False
        else:
            problems = value_problems[filename]
            passed = len(problems) == 0
            message = ("; ".join(first_n(problems, MAX_EXAMPLES))
                       if problems else "ok")
        checks.append({"id": check_id, "passed": passed, "message": message})

    checks.append({
        "id": "cross_table_consistency",
        "passed": len(cross_problems) == 0,
        "message": ("; ".join(first_n(cross_problems, MAX_EXAMPLES))
                    if cross_problems else "ok"),
    })

    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    report = grade(args.reference_dir, args.submission_dir)

    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

