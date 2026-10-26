#!/usr/bin/env python3
"""Acceptance grader: GNPS natural-products library spectral similarities.

Compares parsed scientific content of the five declared outputs against the
reference. Never imports or executes submission code; reads reference values
dynamically.
"""
import argparse
import csv
import json
import math
import os
import sys

import numpy as np

JSON_PATH = "processed_spectra.json"
COS_PATH = "cosine_greedy_scores.npz"
MOD_PATH = "modified_cosine_scores.npz"
META_PATH = "spectrum_metadata.csv"
BEST_PATH = "best_matches_spectrum97.csv"
ALL_PATHS = [JSON_PATH, COS_PATH, MOD_PATH, META_PATH, BEST_PATH]

# Absolute tolerances (no relative term; the reference value is the comparison
# target and no denominator is used). Scores are dimensionless similarity
# values in [0,1] up to rounding; differences attributable to summation order
# or text formatting are bounded far below these limits, while any scientific
# deviation (wrong peak set, matching tolerance or assignment) changes scores
# by orders of magnitude more.
SCORE_ATOL = 1e-8     # matrix / ranked-list scores
VAL_ATOL = 1e-9       # m/z, normalized intensity, precursor m/z
CROSS_ATOL = 1e-7     # internal cross-file consistency of the ranked list
QUERY_INDEX = 97
MIN_MATCH = 5
MAX_ROWS = 10

META_HEADER = ["spectrum_index", "compound_name", "precursor_mz", "inchikey", "smiles"]
BEST_HEADER = ["rank", "smiles", "inchikey", "ModifiedCosine_score", "ModifiedCosine_matches"]


class Failure(Exception):
    """A failed acceptance condition with a non-leaking message."""


def as_finite_float(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Failure("%s is not a number" % what)
    v = float(value)
    if not math.isfinite(v):
        raise Failure("%s is not finite" % what)
    return v


def parse_finite(text, what):
    if isinstance(text, bool):
        raise Failure("%s is not a number" % what)
    try:
        v = float(text)
    except (TypeError, ValueError):
        raise Failure("%s is not a parseable number" % what)
    if not math.isfinite(v):
        raise Failure("%s is not finite" % what)
    return v


def parse_int(text, what):
    if isinstance(text, bool):
        raise Failure("%s is not an integer" % what)
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        raise Failure("%s is not a parseable integer" % what)


# ---------------------------------------------------------------- files present
def check_files_present(ref_dir, sub_dir):
    missing = []
    for rel in ALL_PATHS:
        p = os.path.join(sub_dir, rel)
        if not os.path.isfile(p):
            missing.append(rel)
            continue
        if os.path.getsize(p) <= 0:
            missing.append(rel)
    if missing:
        raise Failure("missing or empty output file(s): %s" % ", ".join(missing))
    return "all five declared output files present and non-empty"


# ------------------------------------------------------------------- JSON spectra
def load_json_array(path, label):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise Failure("%s is not valid JSON (parse error)" % label)
    except OSError as exc:
        raise Failure("%s could not be read" % label)
    if not isinstance(data, list):
        raise Failure("%s top-level JSON value is %s, expected an array"
                      % (label, type(data).__name__))
    return data


def spectrum_peaks_array(spec, index, label):
    peaks = spec.get("peaks_json")
    if not isinstance(peaks, list):
        raise Failure("%s spectrum %d: peaks_json is missing or not a list" % (label, index))
    arr = np.empty((len(peaks), 2), dtype=np.float64)
    for k, peak in enumerate(peaks):
        if not isinstance(peak, (list, tuple)) or len(peak) != 2:
            raise Failure("%s spectrum %d peak %d is not a [mz, intensity] pair"
                          % (label, index, k))
        mz, inten = peak
        arr[k, 0] = as_finite_float(mz, "%s spectrum %d peak %d m/z" % (label, index, k))
        arr[k, 1] = as_finite_float(inten, "%s spectrum %d peak %d intensity" % (label, index, k))
    return arr


def compare_metadata_field(index, key, ref_val, sub_val):
    if isinstance(ref_val, bool) or isinstance(sub_val, bool):
        if ref_val != sub_val:
            raise Failure("spectrum %d field %s differs" % (index, key))
        return
    if isinstance(ref_val, (int, float)):
        if not isinstance(sub_val, (int, float)):
            raise Failure("spectrum %d field %s has wrong value type" % (index, key))
        rv = as_finite_float(ref_val, "reference value")
        sv = as_finite_float(sub_val, "spectrum %d field %s" % (index, key))
        if abs(rv - sv) > VAL_ATOL:
            raise Failure("spectrum %d field %s differs numerically" % (index, key))
        return
    if isinstance(ref_val, str):
        if not isinstance(sub_val, str) or sub_val != ref_val:
            raise Failure("spectrum %d field %s differs" % (index, key))
        return
    raise Failure("spectrum %d field %s has an unsupported value type" % (index, key))


def check_processed_spectra(ref_dir, sub_dir):
    ref = load_json_array(os.path.join(ref_dir, JSON_PATH), "reference")
    sub = load_json_array(os.path.join(sub_dir, JSON_PATH), "submission")
    n_ref = len(ref)
    if len(sub) != n_ref:
        raise Failure("spectrum count is %d, expected %d" % (len(sub), n_ref))
    total_peaks = 0
    for i in range(n_ref):
        rs, ss = ref[i], sub[i]
        if not isinstance(ss, dict):
            raise Failure("spectrum %d is not a JSON object" % i)
        ref_keys = set(rs.keys())
        sub_keys = set(ss.keys())
        if sub_keys != ref_keys:
            missing = sorted(ref_keys - sub_keys)
            extra = sorted(sub_keys - ref_keys)
            raise Failure("spectrum %d metadata field set differs (missing: %s; unexpected: %s)"
                          % (i, ",".join(missing) or "none", ",".join(extra) or "none"))
        for key in sorted(ref_keys):
            if key == "peaks_json":
                continue
            compare_metadata_field(i, key, rs[key], ss[key])
        rp = spectrum_peaks_array(rs, i, "reference")
        sp = spectrum_peaks_array(ss, i, "submission")
        if rp.shape[0] != sp.shape[0]:
            raise Failure("spectrum %d has %d processed peaks, expected %d"
                          % (i, sp.shape[0], rp.shape[0]))
        if rp.shape[0] == 0:
            continue
        total_peaks += int(rp.shape[0])
        # canonical ordering of each peak list before value comparison
        rord = np.lexsort((rp[:, 1], rp[:, 0]))
        sord = np.lexsort((sp[:, 1], sp[:, 0]))
        if not np.allclose(rp[rord, 0], sp[sord, 0], rtol=0.0, atol=VAL_ATOL):
            raise Failure("spectrum %d peak m/z values differ (more than %g absolute)"
                          % (i, VAL_ATOL))
        if not np.allclose(rp[rord, 1], sp[sord, 1], rtol=0.0, atol=VAL_ATOL):
            raise Failure("spectrum %d peak intensities differ (more than %g absolute)"
                          % (i, VAL_ATOL))
    return ("all %d spectra match: metadata fields, peak counts and peak values "
            "(m/z and normalized intensity within %g)" % (n_ref, VAL_ATOL))


# ----------------------------------------------------------------------- matrices
def load_npz(path, label):
    try:
        z = np.load(path, allow_pickle=False)
    except Exception:
        raise Failure("%s could not be loaded as an .npz archive" % label)
    return z


def check_matrices(ref_dir, sub_dir, score_key, match_key, label):
    archive = COS_PATH if score_key.startswith("Cosine") else MOD_PATH
    zr = load_npz(os.path.join(ref_dir, archive), "reference")
    try:
        if set(zr.files) != {score_key, match_key}:
            raise Failure("reference archive layout unexpected")
        sr = np.asarray(zr[score_key])
        mr = np.asarray(zr[match_key])
    finally:
        zr.close()
    zs = load_npz(os.path.join(sub_dir, archive), "submission")
    try:
        if set(zs.files) != {score_key, match_key}:
            raise Failure("archive contains keys %s, expected exactly %s and %s"
                          % (sorted(zs.files), score_key, match_key))
        ss = np.asarray(zs[score_key])
        ms = np.asarray(zs[match_key])
    finally:
        zs.close()

    if ss.ndim != 2 or ss.shape != sr.shape:
        raise Failure("%s array shape is %s, expected %s"
                      % (score_key, list(ss.shape), list(sr.shape)))
    if ms.shape != sr.shape:
        raise Failure("%s array shape is %s, expected %s"
                      % (match_key, list(ms.shape), list(sr.shape)))
    if not np.issubdtype(ss.dtype, np.floating):
        raise Failure("%s array is not of floating-point type" % score_key)
    if not np.issubdtype(ms.dtype, np.integer):
        raise Failure("%s array is not of integer type" % match_key)
    if not np.isfinite(ss).all():
        raise Failure("%s array contains nonfinite values" % score_key)
    if (ms < 0).any():
        raise Failure("%s array contains negative values" % match_key)

    asym = float(np.max(np.abs(ss - ss.T))) if ss.size else 0.0
    if asym > SCORE_ATOL:
        raise Failure("%s matrix is not symmetric (max |M - M.T| exceeds %g)"
                      % (score_key, SCORE_ATOL))
    if (ms != ms.T).any():
        raise Failure("%s matrix is not symmetric" % match_key)

    nbad = int((np.abs(ss - sr) > SCORE_ATOL).sum())
    if nbad:
        first = np.argwhere(np.abs(ss - sr) > SCORE_ATOL)[0].tolist()
        raise Failure("%s differs from the reference in %d of %d score entries "
                      "(first at row %d, column %d; tolerance %g absolute)"
                      % (score_key, nbad, ss.size, first[0], first[1], SCORE_ATOL))
    mdiff = int((ms != mr).sum())
    if mdiff:
        first = np.argwhere(ms != mr)[0].tolist()
        raise Failure("%s differs from the reference in %d of %d match-count entries "
                      "(first at row %d, column %d)" % (match_key, mdiff, ms.size,
                                                        first[0], first[1]))
    return ("%s and %s match the reference (%d x %d; scores within %g absolute, "
            "match counts exact)" % (score_key, match_key, ss.shape[0], ss.shape[1],
                                      SCORE_ATOL))


# --------------------------------------------------------------------------- CSVs
def read_csv_rows(path, label):
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
    except OSError:
        raise Failure("%s could not be read" % label)
    except csv.Error:
        raise Failure("%s is not well-formed CSV" % label)
    return rows


def compare_numeric_field(ref_text, sub_text, row_label, field, atol):
    if not isinstance(ref_text, str):
        ref_text = str(ref_text)
    if not isinstance(sub_text, str):
        sub_text = str(sub_text)
    if ref_text.strip() == "":
        if sub_text.strip() == "":
            return
        raise Failure("%s %s: value present where the reference has missing metadata"
                      % (row_label, field))
    rv = parse_finite(ref_text, "%s %s (reference)" % (row_label, field))
    if sub_text.strip() == "":
        raise Failure("%s %s: missing value where the reference has one"
                      % (row_label, field))
    sv = parse_finite(sub_text, "%s %s" % (row_label, field))
    if abs(rv - sv) > atol:
        raise Failure("%s %s differs numerically (tolerance %g absolute)"
                      % (row_label, field, atol))


def check_metadata_table(ref_dir, sub_dir):
    rrows = read_csv_rows(os.path.join(ref_dir, META_PATH), "reference")
    srows = read_csv_rows(os.path.join(sub_dir, META_PATH), "submission")
    if not srows or srows[0] != META_HEADER:
        raise Failure("header row must be exactly: %s" % ",".join(META_HEADER))
    body = srows[1:]
    n_ref = len(rrows) - 1
    if len(body) != n_ref:
        raise Failure("table has %d spectrum rows, expected %d" % (len(body), n_ref))
    for i in range(n_ref):
        row = body[i]
        if len(row) != 5:
            raise Failure("spectrum row %d has %d fields, expected 5" % (i, len(row)))
        idx = parse_int(row[0], "row %d spectrum_index" % i)
        if idx != i:
            raise Failure("row %d has spectrum_index %d; rows must be numbered 0..%d "
                          "in order" % (i, idx, n_ref - 1))
        for col, name in ((1, "compound_name"), (3, "inchikey"), (4, "smiles")):
            if row[col] != rrows[i + 1][col]:
                raise Failure("row %d %s differs from the reference" % (i, name))
        compare_numeric_field(rrows[i + 1][2], row[2], "row %d" % i, "precursor_mz", VAL_ATOL)
    return ("all %d metadata rows match (exact identifiers, precursor m/z within %g)"
            % (n_ref, VAL_ATOL))


def check_best_matches(ref_dir, sub_dir):
    rrows = read_csv_rows(os.path.join(ref_dir, BEST_PATH), "reference")
    srows = read_csv_rows(os.path.join(sub_dir, BEST_PATH), "submission")
    if not srows or srows[0] != BEST_HEADER:
        raise Failure("header row must be exactly: %s" % ",".join(BEST_HEADER))
    body = srows[1:]
    n_ref = len(rrows) - 1
    if len(body) != n_ref:
        raise Failure("table has %d rows, expected %d" % (len(body), n_ref))
    if len(body) > MAX_ROWS:
        raise Failure("table has more than %d rows" % MAX_ROWS)
    prev_score = None
    for i in range(n_ref):
        row = body[i]
        if len(row) != 5:
            raise Failure("row %d has %d fields, expected 5" % (i, len(row)))
        rank = parse_int(row[0], "row %d rank" % i)
        if rank != i:
            raise Failure("row %d has rank %d; ranks must run 0..%d in order"
                          % (i, rank, n_ref - 1))
        if row[1] != rrows[i + 1][1]:
            raise Failure("row %d smiles differs from the reference" % i)
        if row[2] != rrows[i + 1][2]:
            raise Failure("row %d inchikey differs from the reference" % i)
        rv = parse_finite(rrows[i + 1][3], "row %d ModifiedCosine_score (reference)" % i)
        sv = parse_finite(row[3], "row %d ModifiedCosine_score" % i)
        if abs(rv - sv) > SCORE_ATOL:
            raise Failure("row %d ModifiedCosine_score differs (tolerance %g absolute)"
                          % (i, SCORE_ATOL))
        mt = parse_int(row[4], "row %d ModifiedCosine_matches" % i)
        ref_mt = parse_int(rrows[i + 1][4], "row %d matches (reference)" % i)
        if mt != ref_mt:
            raise Failure("row %d ModifiedCosine_matches is %d, expected %d" % (i, mt, ref_mt))
        if mt < MIN_MATCH:
            raise Failure("row %d ModifiedCosine_matches is below %d" % (i, MIN_MATCH))
        if prev_score is not None and sv > prev_score + 1e-12:
            raise Failure("row %d score is larger than the previous row's score "
                          "(list must be ordered by score descending)" % i)
        prev_score = sv
    # cross-file consistency with the submission's own matrix and metadata table
    cross = cross_check_ranked_list(sub_dir, body)
    if cross is not None:
        raise Failure(cross)
    return ("all %d ranked matches match the reference (identifiers exact, score "
            "within %g, match counts exact) and are consistent with the submitted "
            "modified-cosine matrices and metadata table" % (n_ref, SCORE_ATOL))


def cross_check_ranked_list(sub_dir, body):
    """Verify each ranked row against row 97 of the submitted modified-cosine
    matrices, identifying candidates through the submitted metadata table.
    Returns None when consistent, an error message when not, and None as well
    if the needed files cannot be parsed (their own checks report that)."""
    if not body:
        return None
    try:
        zs = np.load(os.path.join(sub_dir, MOD_PATH), allow_pickle=False)
        try:
            if set(zs.files) != {"ModifiedCosine_score", "ModifiedCosine_matches"}:
                return None
            ss = np.asarray(zs["ModifiedCosine_score"])
            ms = np.asarray(zs["ModifiedCosine_matches"])
        finally:
            zs.close()
    except Exception:
        return None
    if ss.ndim != 2 or ss.shape[0] != ss.shape[1]:
        return None
    n = ss.shape[0]
    if QUERY_INDEX >= n or not np.issubdtype(ss.dtype, np.floating):
        return None
    try:
        srows = read_csv_rows(os.path.join(sub_dir, META_PATH), "submission")
    except Failure:
        return None
    if len(srows) < 2 or srows[0] != META_HEADER or len(srows) - 1 != n:
        return None
    id_map = {}
    for j in range(n):
        row = srows[j + 1]
        if len(row) != 5:
            return None
        id_map.setdefault((row[4], row[3]), []).append(j)
    for i, row in enumerate(body):
        try:
            sc = parse_finite(row[3], "row %d ModifiedCosine_score" % i)
            mt = parse_int(row[4], "row %d ModifiedCosine_matches" % i)
        except Failure:
            return None  # already reported by the primary comparison
        candidates = id_map.get((row[1], row[2]), [])
        ok = False
        for j in candidates:
            if not (np.isfinite(ss[QUERY_INDEX, j]) and int(ms[QUERY_INDEX, j]) == mt):
                continue
            if abs(float(ss[QUERY_INDEX, j]) - sc) <= CROSS_ATOL:
                ok = True
                break
        if not ok:
            return ("row %d is not consistent with the submitted outputs: its score and "
                    "match count do not occur at any candidate index in row %d of the "
                    "submitted modified-cosine matrices for a spectrum whose submitted "
                    "metadata matches the row's smiles/inchikey" % (i, QUERY_INDEX))
    return None


# ------------------------------------------------------------------------- driver
def run_check(fn, ref_dir, sub_dir):
    try:
        message = fn(ref_dir, sub_dir)
        return True, message
    except Failure as exc:
        return False, str(exc)
    except Exception as exc:  # never crash: report as failed check
        return False, "check could not be completed: %s" % type(exc).__name__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    checks = [
        ("files_present", "structural", ALL_PATHS, check_files_present),
        ("processed_spectra_library", "scientific", [JSON_PATH], check_processed_spectra),
        ("cosine_greedy_matrices", "scientific", [COS_PATH],
         lambda r, s: check_matrices(r, s, "CosineGreedy_score", "CosineGreedy_matches",
                                      "greedy cosine")),
        ("modified_cosine_matrices", "scientific", [MOD_PATH],
         lambda r, s: check_matrices(r, s, "ModifiedCosine_score", "ModifiedCosine_matches",
                                      "modified cosine")),
        ("spectrum_metadata_table", "scientific", [META_PATH], check_metadata_table),
        ("ranked_matches_spectrum97", "scientific", [BEST_PATH], check_best_matches),
    ]

    report = []
    all_passed = True
    for check_id, kind, artifacts, fn in checks:
        passed, message = run_check(fn, args.reference_dir, args.submission_dir)
        all_passed = all_passed and passed
        report.append({"id": check_id, "passed": passed, "message": message})

    payload = {"passed": all_passed, "checks": report}
    report_dir = os.path.dirname(os.path.abspath(args.report))
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

