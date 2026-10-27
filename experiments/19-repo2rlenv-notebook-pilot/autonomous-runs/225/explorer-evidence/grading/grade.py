#!/usr/bin/env python3
"""Grader: validate hrv_indices.csv (95 HRV metrics) against the reference."""

import argparse
import json
import math
import sys
from pathlib import Path

from biotasks_table_io import read_delimited_table

REL_TOL = 1e-6
ABS_TOL = 1e-9

TIME_COLUMNS = [
    "HRV_MeanNN", "HRV_SDNN", "HRV_SDANN1", "HRV_SDNNI1", "HRV_SDANN2",
    "HRV_SDNNI2", "HRV_SDANN5", "HRV_SDNNI5", "HRV_RMSSD", "HRV_SDSD",
    "HRV_CVNN", "HRV_CVSD", "HRV_MedianNN", "HRV_MadNN", "HRV_MCVNN",
    "HRV_IQRNN", "HRV_SDRMSSD", "HRV_Prc20NN", "HRV_Prc80NN", "HRV_pNN50",
    "HRV_pNN20", "HRV_MinNN", "HRV_MaxNN", "HRV_HTI", "HRV_TINN",
]
FREQ_COLUMNS = [
    "HRV_ULF", "HRV_VLF", "HRV_LF", "HRV_HF", "HRV_VHF", "HRV_TP",
    "HRV_LFHF", "HRV_LFn", "HRV_HFn", "HRV_LnHF",
]
NONLINEAR_COLUMNS = [
    "HRV_SD1", "HRV_SD2", "HRV_SD1SD2", "HRV_S", "HRV_CSI", "HRV_CVI",
    "HRV_CSI_Modified", "HRV_PIP", "HRV_IALS", "HRV_PSS", "HRV_PAS",
    "HRV_GI", "HRV_SI", "HRV_AI", "HRV_PI", "HRV_C1d", "HRV_C1a",
    "HRV_SD1d", "HRV_SD1a", "HRV_C2d", "HRV_C2a", "HRV_SD2d", "HRV_SD2a",
    "HRV_Cd", "HRV_Ca", "HRV_SDNNd", "HRV_SDNNa", "HRV_DFA_alpha1",
    "HRV_MFDFA_alpha1_Width", "HRV_MFDFA_alpha1_Peak",
    "HRV_MFDFA_alpha1_Mean", "HRV_MFDFA_alpha1_Max",
    "HRV_MFDFA_alpha1_Delta", "HRV_MFDFA_alpha1_Asymmetry",
    "HRV_MFDFA_alpha1_Fluctuation", "HRV_MFDFA_alpha1_Increment",
    "HRV_DFA_alpha2",
    "HRV_MFDFA_alpha2_Width", "HRV_MFDFA_alpha2_Peak",
    "HRV_MFDFA_alpha2_Mean", "HRV_MFDFA_alpha2_Max",
    "HRV_MFDFA_alpha2_Delta", "HRV_MFDFA_alpha2_Asymmetry",
    "HRV_MFDFA_alpha2_Fluctuation", "HRV_MFDFA_alpha2_Increment",
    "HRV_ApEn", "HRV_SampEn", "HRV_ShanEn", "HRV_FuzzyEn", "HRV_MSEn",
    "HRV_CMSEn", "HRV_RCMSEn", "HRV_CD", "HRV_HFD", "HRV_KFD", "HRV_LZC",
    "HRV_Symbolic_EqualProb4_0V", "HRV_Symbolic_EqualProb4_1V",
    "HRV_Symbolic_EqualProb4_2LV", "HRV_Symbolic_EqualProb4_2UV",
]
ALL_COLUMNS = TIME_COLUMNS + FREQ_COLUMNS + NONLINEAR_COLUMNS
# The declared output is the only artifact; its path is fixed by the contract.
OUTPUT_PATH = "hrv_indices.csv"


def load_single_row_table(path):
    """Read the output table, returning (values_by_name, problem) or (None, msg).

    values_by_name maps column name -> float or None (None for a missing value).
    """
    try:
        header, rows = read_delimited_table(path)
    except (OSError, ValueError) as exc:
        return None, "could not read table (%s)" % exc
    if len(rows) != 1:
        return None, "expected exactly one data row, found %d" % len(rows)
    if len(header) != 95:
        return None, "expected exactly 95 columns, found %d" % len(header)
    seen = set()
    for name in header:
        if name not in seen:
            seen.add(name)
        else:
            return None, "duplicate column name: %s" % name
    missing = [c for c in ALL_COLUMNS if c not in seen]
    if missing:
        return None, "missing required columns: %s" % ", ".join(missing)
    extra = [c for c in header if c not in ALL_COLUMNS]
    if extra:
        return None, "unexpected extra columns: %s" % ", ".join(extra)
    values = {}
    problems = []
    for name, raw in zip(header, rows[0]):
        if raw == "":
            values[name] = None
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            problems.append("%s: value is not a number (%r)" % (name, raw[:32]))
            continue
        if not math.isfinite(v):
            problems.append("%s: value is not finite" % name)
            continue
        values[name] = v
    if problems:
        return None, "; ".join(problems)
    return values, None


def compare_domain(values, ref_values, columns):
    """Compare submission values against reference values column by column."""
    mismatches = []
    for name in columns:
        sub = values.get(name, "absent")
        ref = ref_values[name]
        if ref is None:
            # Undefined per the reference method: submission must be empty too.
            if sub is None:
                continue
            mismatches.append("%s: expected empty (undefined per reference), got %s"
                              % (name, sub))
            continue
        if sub is None:
            mismatches.append("%s: reference is defined, submission is empty" % name)
            continue
        diff = abs(sub - ref)
        allowed = REL_TOL * abs(ref) + ABS_TOL
        if diff > allowed:
            mismatches.append("%s: %r vs reference %r (diff %.3g, allowed %.3g)"
                              % (name, sub, ref, diff, allowed))
    return mismatches


def write_report(path, report):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(report, fh)
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    ref_path = Path(args.reference_dir) / OUTPUT_PATH
    sub_path = Path(args.submission_dir) / OUTPUT_PATH

    ref_values, ref_error = load_single_row_table(ref_path)
    if ref_error is not None:
        # A reference-side read failure is an incomplete verification.
        report = {
            "passed": False,
            "checks": [
                {"id": cid, "passed": False,
                 "message": "internal: reference table unreadable: %s" % ref_error}
                for cid in ("file_present", "structure_valid",
                            "time_domain_values", "frequency_domain_values",
                            "nonlinear_domain_values")
            ],
        }
        write_report(args.report, report)
        return 0

    results = {}

    # 1. file present
    results["file_present"] = (sub_path.is_file(),
                               "output file %s present" % OUTPUT_PATH
                               if sub_path.is_file()
                               else "output file %s missing" % OUTPUT_PATH)

    # 2. structure
    if not sub_path.is_file():
        msg = "cannot validate structure: %s missing" % OUTPUT_PATH
        results["structure_valid"] = (False, msg)
    else:
        raw = sub_path.read_bytes()
        msg = "95 named columns without duplicates, exactly one data row, " \
              "valid delimited syntax"
        structural_problems = []
        # Reject binary content / NUL bytes that could hide encodings.
        if b"\x00" in raw:
            structural_problems.append("file contains NUL bytes")
        values, error = load_single_row_table(sub_path)
        if error is not None:
            structural_problems = [error] if not structural_problems else \
                structural_problems + [error]
        results["structure_valid"] = (not structural_problems,
                                       msg if not structural_problems
                                       else "; ".join(structural_problems))

    values = None
    if sub_path.is_file():
        values, _err = load_single_row_table(sub_path)
        if _err is not None:
            values = None

    # 3-5. domain value checks
    for cid, cols in (("time_domain_values", TIME_COLUMNS),
                      ("frequency_domain_values", FREQ_COLUMNS),
                      ("nonlinear_domain_values", NONLINEAR_COLUMNS)):
        if values is None:
            results[cid] = (False, "cannot compare values: submission table "
                                   "missing or not a valid single-row "
                                   "95-column numeric table")
            continue
        mismatches = compare_domain(values, ref_values, cols)
        results[cid] = (not mismatches,
                        "all %d %s columns within tolerance"
                        % (len(cols), cid.replace("_values", ""))
                        if not mismatches
                        else "; ".join(mismatches))

    order = ["file_present", "structure_valid", "time_domain_values",
             "frequency_domain_values", "nonlinear_domain_values"]
    checks = [{"id": cid, "passed": results[cid][0], "message": results[cid][1]}
              for cid in order]
    write_report(args.report, {"passed": all(c["passed"] for c in checks),
                              "checks": checks})
    return 0


if __name__ == "__main__":
    sys.exit(main())

