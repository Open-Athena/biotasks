#!/usr/bin/env python3
"""Deterministic scientific grader for the GNPS natural-products-library
similarity task.

Compares the four declared output files against the recorded reference:
  processed_spectra.json, similarity_scores.npz, best_matches.csv, peak_counts.csv

All reference quantities are read dynamically from the reference directory.
Never imports or executes submission code.
"""
import argparse
import csv
import json
import math
import os
import sys

import numpy as np

OUTPUT_PATHS = [
    "processed_spectra.json",
    "similarity_scores.npz",
    "best_matches.csv",
    "peak_counts.csv",
]

SCORE_KEYS = ("cosine_greedy_score", "modified_cosine_score")
MATCH_KEYS = ("cosine_greedy_matches", "modified_cosine_matches")
REQ_KEYS = ("spectrum_index", "spectrum_id", "compound_name", "inchikey",
            "inchi", "smiles", "precursor_mz", "peaks")
STRING_FIELDS = ("spectrum_id", "compound_name", "inchikey", "inchi", "smiles")

# Branches of the ranked best-match lists (from the public question).
# (query_index, similarity_measure, min_match_filter or None)
BRANCHES = [
    (5, "CosineGreedy", None),
    (5, "CosineGreedy", 5),
    (5, "ModifiedCosine", 5),
    (11, "ModifiedCosine", 5),
    (97, "ModifiedCosine", 5),
]
TOP_N = 10

# Absolute tolerances against the reference value (pass iff |v - v_ref| <= tol).
SCORE_ATOL = 1e-9
MZ_ATOL = 1e-6
INTENSITY_ATOL = 1e-9
# Scores whose reference values differ by at most this are treated as tied
# for the ranked lists; distinct results in this library are separated by far
# larger gaps (>= ~1.4e-4 among the reported top-10 entries).
TIE_ATOL = 1e-9

BEST_MATCHES_HEADER = ["query_index", "similarity_measure", "min_match_filter",
                       "rank", "matched_spectrum_index", "matched_smiles",
                       "matched_inchikey", "score", "matches"]
PEAK_COUNTS_HEADER = ["spectrum_index", "n_peaks_before_filtering",
                      "n_peaks_after_filtering"]


class CheckFailure(Exception):
    pass


def fail(msg):
    raise CheckFailure(msg)


def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def no_duplicate_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            fail("duplicate JSON key %r" % k)
        d[k] = v
    return d


def parse_spectra_json(path, expect_n, what):
    # expect_n = None means the count is not yet known (reference load).
    if not os.path.isfile(path):
        fail("%s file is missing: %s" % (what, path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh, object_pairs_hook=no_duplicate_keys)
    except CheckFailure:
        raise
    except Exception as exc:  # malformed JSON
        fail("%s is not valid JSON: %s" % (what, exc))
    if not isinstance(data, list):
        fail("%s must be a JSON array of spectrum objects" % what)
    if expect_n is not None and len(data) != expect_n:
        fail("%s has %d records, expected %d spectra" % (what, len(data), expect_n))
    for i, rec in enumerate(data):
        if not isinstance(rec, dict):
            fail("%s record %d is not a JSON object" % (what, i))
        for key in REQ_KEYS:
            if key not in rec:
                fail("%s record %d lacks required key %r" % (what, i, key))
        idx = rec["spectrum_index"]
        if isinstance(idx, bool) or not isinstance(idx, int) or idx != i:
            fail("%s record %d has spectrum_index %r (expected %d)"
                 % (what, i, idx, i))
        for key in STRING_FIELDS:
            if not isinstance(rec[key], str):
                fail("%s record %d field %r is not a string" % (what, i, key))
        pmz = rec["precursor_mz"]
        if not is_number(pmz) or not math.isfinite(float(pmz)):
            fail("%s record %d has a non-numeric or nonfinite precursor_mz" % (what, i))
        peaks = rec["peaks"]
        if not isinstance(peaks, list):
            fail("%s record %d has a non-list 'peaks'" % (what, i))
        for k, pk in enumerate(peaks):
            if not isinstance(pk, list) or len(pk) != 2:
                fail("%s record %d peak %d is not a [mz, intensity] pair" % (what, i, k))
            if not all(is_number(x) and math.isfinite(float(x)) for x in pk):
                fail("%s record %d peak %d has non-numeric or nonfinite values" % (what, i, k))
    return data


def read_csv_rows(path, header, what):
    if not os.path.isfile(path):
        fail("%s file is missing: %s" % (what, path))
    try:
        with open(path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh, restkey="__extra__", restval=None)
            if reader.fieldnames is None:
                fail("%s is empty" % what)
            if list(reader.fieldnames) != header:
                fail("%s header is %r, expected exactly %r" % (what, list(reader.fieldnames), header))
            rows = []
            for rnum, row in enumerate(reader, start=2):
                if "__extra__" in row:
                    fail("%s row %d has extra columns" % (what, rnum))
                if any(v is None for v in row.values()):
                    fail("%s row %d has missing fields" % (what, rnum))
                rows.append((row, rnum))
    except CheckFailure:
        raise
    except Exception as exc:
        fail("%s could not be parsed as CSV: %s" % (what, exc))
    return rows


def parse_int_field(value, what, rnum, field):
    s = value
    try:
        return int(s)
    except (TypeError, ValueError):
        fail("%s row %d field %r is not an integer: %r" % (what, rnum, field, s))


def parse_float_field(value, what, rnum, field):
    try:
        v = float(value)
    except (TypeError, ValueError):
        fail("%s row %d field %r is not numeric: %r" % (what, rnum, field, value))
    if not math.isfinite(v):
        fail("%s row %d field %r is nonfinite (%r)" % (what, rnum, field, value))
    return v


def load_npz(path, what):
    if not os.path.isfile(path):
        fail("%s file is missing: %s" % (what, path))
    try:
        return np.load(path, allow_pickle=False)
    except Exception as exc:
        fail("%s could not be loaded as a NumPy .npz archive: %s" % (what, exc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    ref_dir = args.reference_dir
    sub_dir = args.submission_dir

    results = []

    def record(check_id, ok, message):
        results.append({"id": check_id, "passed": bool(ok), "message": message})

    def run(check_id, kind, fn):
        try:
            msg = fn()
            record(check_id, True, msg if msg else "passed")
        except CheckFailure as exc:
            record(check_id, False, str(exc))
        except Exception as exc:  # defensive: never crash on bad submissions
            record(check_id, False, "unexpected failure: %r" % (exc,))

    # ---------------- shared reference / submission state ----------------
    state = {}

    def load_reference():
        ref_records = parse_spectra_json(os.path.join(ref_dir, "processed_spectra.json"),
                                         None, "reference processed_spectra.json")
        # reference itself defines the expected spectrum count
        state["n"] = len(ref_records)
        state["ref_records"] = ref_records
        with load_npz(os.path.join(ref_dir, "similarity_scores.npz"), "reference similarity_scores.npz") as zref:
            state["ref_npz"] = {k: np.array(zref[k]) for k in zref.files}
        rows = read_csv_rows(os.path.join(ref_dir, "best_matches.csv"), BEST_MATCHES_HEADER,
                             "reference best_matches.csv")
        state["ref_best_matches"] = rows
        rows = read_csv_rows(os.path.join(ref_dir, "peak_counts.csv"), PEAK_COUNTS_HEADER,
                             "reference peak_counts.csv")
        state["ref_peak_counts"] = rows
        return "reference loaded: %d spectra" % state["n"]

    run("reference_load", "structural", load_reference)
    n = state.get("n")

    # ---------- 1. files present at the declared paths ----------
    def check_files():
        missing = [p for p in OUTPUT_PATHS if not os.path.isfile(os.path.join(sub_dir, p))]
        if missing:
            fail("missing required output files: %s" % ", ".join(missing))
        return "all four required files are present"

    run("files_present", "structural", check_files)

    # ---------- 2. processed_spectra.json schema ----------
    def check_spectra_schema():
        if n is None:
            fail("reference unavailable")
        recs = parse_spectra_json(os.path.join(sub_dir, "processed_spectra.json"), n,
                                  "submission processed_spectra.json")
        state["sub_records"] = recs
        return "parsed %d spectrum records with required keys, in spectrum-index order" % n

    run("spectra_schema", "structural", check_spectra_schema)

    # ---------- 3. processed_spectra.json scientific content ----------
    def check_spectra_content():
        if "ref_records" not in state or "sub_records" not in state:
            fail("spectra records unavailable")
        ref_records = state["ref_records"]
        sub_records = state["sub_records"]
        worst_mz = 0.0
        worst_int = 0.0
        for i, (rrec, srec) in enumerate(zip(ref_records, sub_records)):
            for key in STRING_FIELDS:
                if srec[key] != rrec[key]:
                    fail("spectrum %d: field %r is %r, expected %r"
                         % (i, key, srec[key][:80], rrec[key][:80]))
            pmz = float(srec["precursor_mz"])
            rpmz = float(rrec["precursor_mz"])
            if abs(pmz - rpmz) > MZ_ATOL:
                fail("spectrum %d: precursor_mz %r differs from reference %r"
                     % (i, pmz, rpmz))
            sp = srec["peaks"]
            rp = rrec["peaks"]
            if len(sp) != len(rp):
                fail("spectrum %d: %d retained peaks, expected %d" % (i, len(sp), len(rp)))
            for k, (sp_, rp_) in enumerate(zip(sp, rp)):
                smz, sint = float(sp_[0]), float(sp_[1])
                rmz, rint = float(rp_[0]), float(rp_[1])
                dmz = abs(smz - rmz)
                dint = abs(sint - rint)
                worst_mz = max(worst_mz, dmz)
                worst_int = max(worst_int, dint)
                if dmz > MZ_ATOL:
                    fail("spectrum %d peak %d: m/z %r differs from reference %r"
                         % (i, k, smz, rmz))
                if dint > INTENSITY_ATOL:
                    fail("spectrum %d peak %d: normalized intensity %r differs from "
                         "reference %r" % (i, k, sint, rint))
                if sint < 0.01 - INTENSITY_ATOL or sint > 1.0 + INTENSITY_ATOL:
                    fail("spectrum %d peak %d: normalized intensity %r outside [0.01, 1]"
                         % (i, k, sint))
                if smz < 10.0 - MZ_ATOL or smz > 1000.0 + MZ_ATOL:
                    fail("spectrum %d peak %d: m/z %r outside [10, 1000]" % (i, k, smz))
                if sint == 0.0 and rint != 0.0:
                    fail("spectrum %d peak %d: intensity zero where reference is nonzero"
                         % (i, k))
            if sp:
                smax = max(float(p[1]) for p in sp)
                if smax < 1.0 - 1e-9:
                    fail("spectrum %d: maximum normalized intensity is %r, expected 1"
                         % (i, smax))
        return ("all %d spectra match reference metadata, precursor m/z and peak lists "
                "(max |dmz|=%.3e Da, max |dintensity|=%.3e)" % (n, worst_mz, worst_int))

    run("spectra_content", "scientific", check_spectra_content)

    # ---------- 4. similarity matrices ----------
    def check_matrices():
        if "ref_npz" not in state or n is None:
            fail("reference matrices unavailable")
        zsub = load_npz(os.path.join(sub_dir, "similarity_scores.npz"),
                        "submission similarity_scores.npz")
        sub_keys = sorted(zsub.files)
        ref_keys = sorted(state["ref_npz"].keys())
        if sub_keys != ref_keys:
            fail("similarity_scores.npz contains arrays %r, expected exactly %r"
                 % (sub_keys, ref_keys))
        expected_shape = (n, n)
        with np.errstate(invalid="ignore"):
            for key in SCORE_KEYS:
                arr = zsub[key]
                if arr.dtype.kind != "f":
                    fail("%s must be a floating-point array, got dtype %s" % (key, arr.dtype))
                if arr.shape != expected_shape:
                    fail("%s has shape %r, expected %r" % (key, arr.shape, expected_shape))
                if not np.all(np.isfinite(arr)):
                    fail("%s contains nonfinite values" % key)
                ref = state["ref_npz"][key].astype(np.float64, copy=False)
                d = np.abs(arr.astype(np.float64, copy=False) - ref)
                worst = float(d.max()) if d.size else 0.0
                if worst > SCORE_ATOL:
                    fail("%s differs from the reference by up to %.3e (> %g)"
                         % (key, worst, SCORE_ATOL))
                sym = float(np.abs(arr - arr.T).max()) if arr.size else 0.0
                if sym > SCORE_ATOL:
                    fail("%s is not symmetric (max asymmetry %.3e)" % (key, sym))
            for key in MATCH_KEYS:
                arr = zsub[key]
                if arr.dtype.kind not in "iu":
                    fail("%s must be an integer array, got dtype %s" % (key, arr.dtype))
                if arr.shape != expected_shape:
                    fail("%s has shape %r, expected %r" % (key, arr.shape, expected_shape))
                if not np.array_equal(arr, arr.T):
                    fail("%s is not symmetric" % key)
                ref = state["ref_npz"][key]
                if not np.array_equal(arr.astype(ref.dtype, copy=False), ref):
                    bad = np.count_nonzero(arr.astype(ref.dtype, copy=False) != ref)
                    fail("%s differs from the reference in %d entries (match counts are integers)"
                         % (key, bad))
        state["sub_npz"] = {k: np.array(zsub[k]) for k in zsub.files}
        return ("four N x N matrices match the reference (score tolerance %g, match counts exact)"
                % SCORE_ATOL)

    run("similarity_matrices", "scientific", check_matrices)

    # ---------- 5. best_matches.csv ranked lists ----------
    def expected_branch_list(query_index, measure, mmf):
        score_key = "cosine_greedy_score" if measure == "CosineGreedy" else "modified_cosine_score"
        match_key = "cosine_greedy_matches" if measure == "CosineGreedy" else "modified_cosine_matches"
        S = state["ref_npz"][score_key].astype(np.float64, copy=False)
        M = state["ref_npz"][match_key]
        if mmf is None:
            candidates = list(range(n))
        else:
            col = np.asarray(M[:, query_index])
            candidates = [i for i in range(n) if col[i] >= mmf]
        candidates.sort(key=lambda i: (-float(S[i, query_index]), i))
        return candidates[:TOP_N], S, M

    def check_best_matches():
        if "ref_records" not in state or n is None:
            fail("reference unavailable")
        rows = read_csv_rows(os.path.join(sub_dir, "best_matches.csv"), BEST_MATCHES_HEADER,
                             "submission best_matches.csv")
        groups = {}
        for row, rnum in rows:
            key = (row["query_index"], row["similarity_measure"], row["min_match_filter"])
            groups.setdefault(key, []).append((row, rnum))
        for key in groups:
            q, meas, mmf = key
            if not any(q == str(bq) and meas == bm and mmf == ("none" if bf is None else str(bf))
                       for bq, bm, bf in BRANCHES):
                fail("best_matches.csv row group (query_index=%r, similarity_measure=%r, "
                     "min_match_filter=%r) is not one of the required branches A-E" % key)
        for query_index, measure, mmf in BRANCHES:
            key = (str(query_index), measure, "none" if mmf is None else str(mmf))
            expected, S, M = expected_branch_list(query_index, measure, mmf)
            sub_rows = groups.get(key, [])
            if len(sub_rows) != len(expected):
                fail("branch (query %d, %s, filter %s) has %d rows, expected %d"
                     % (query_index, measure, mmf, len(sub_rows), len(expected)))
            # tie groups among expected reference scores
            groups_of = [0] * len(expected)
            g = 0
            for r in range(len(expected)):
                if r > 0:
                    s_prev = float(S[expected[r - 1], query_index])
                    s_cur = float(S[expected[r], query_index])
                    if abs(s_prev - s_cur) > TIE_ATOL:
                        g += 1
                groups_of[r] = g
            allowed = {}
            for r in range(len(expected)):
                allowed.setdefault(groups_of[r], []).append(expected[r])
            seen_indices = []
            for r, (row, rnum) in enumerate(sub_rows):
                rank = parse_int_field(row["rank"], "best_matches.csv", rnum, "rank")
                if rank != r + 1:
                    fail("branch (query %d, %s, filter %s) row %d has rank %d, expected %d "
                         "(ranks are 1-based within the truncated branch list)"
                         % (query_index, measure, mmf, rnum, rank, r + 1))
                mi = parse_int_field(row["matched_spectrum_index"], "best_matches.csv",
                                     rnum, "matched_spectrum_index")
                if not (0 <= mi < n):
                    fail("branch (query %d, %s, filter %s) row %d: matched_spectrum_index %d "
                         "out of range" % (query_index, measure, mmf, rnum, mi))
                if mi not in allowed[groups_of[r]]:
                    fail("branch (query %d, %s, filter %s) rank %d: matched_spectrum_index %d "
                         "is not a permitted selection at this rank"
                         % (query_index, measure, mmf, r + 1, mi))
                seen_indices.append(mi)
                score = parse_float_field(row["score"], "best_matches.csv", rnum, "score")
                ref_score = float(S[mi, query_index])
                if abs(score - ref_score) > SCORE_ATOL:
                    fail("branch (query %d, %s, filter %s) rank %d: score %r differs from "
                         "the reference matrix value %r" % (query_index, measure, mmf, r + 1, score, ref_score))
                matches = parse_int_field(row["matches"], "best_matches.csv", rnum, "matches")
                ref_matches = int(M[mi, query_index])
                if matches != ref_matches:
                    fail("branch (query %d, %s, filter %s) rank %d: matches %d differs from "
                         "the reference value %d" % (query_index, measure, mmf, r + 1, matches, ref_matches))
                rec = state["ref_records"][mi]
                if row["matched_smiles"] != rec["smiles"]:
                    fail("branch (query %d, %s, filter %s) rank %d: matched_smiles does not "
                         "match the reference record of spectrum %d" % (query_index, measure, mmf, r + 1, mi))
                if row["matched_inchikey"] != rec["inchikey"]:
                    fail("branch (query %d, %s, filter %s) rank %d: matched_inchikey does not "
                         "match the reference record of spectrum %d" % (query_index, measure, mmf, r + 1, mi))
            # multiplicity: each matched index used at most once per branch
            if len(seen_indices) != len(set(seen_indices)):
                fail("branch (query %d, %s, filter %s) repeats matched_spectrum_index values"
                     % (query_index, measure, mmf))
        return ("all five ranked branches A-E match the reference selection, ordering, "
                "scores, match counts and matched identifiers")

    run("best_matches_ranked_lists", "scientific", check_best_matches)

    # ---------- 6. peak_counts.csv ----------
    def check_peak_counts():
        if "ref_peak_counts" not in state or n is None:
            fail("reference unavailable")
        rows = read_csv_rows(os.path.join(sub_dir, "peak_counts.csv"), PEAK_COUNTS_HEADER,
                             "submission peak_counts.csv")
        if len(rows) != n:
            fail("peak_counts.csv has %d rows, expected %d" % (len(rows), n))
        for i, (row, rnum) in enumerate(rows):
            idx = parse_int_field(row["spectrum_index"], "peak_counts.csv", rnum, "spectrum_index")
            if idx != i:
                fail("peak_counts.csv row %d has spectrum_index %d, expected %d "
                     "(rows must appear once per spectrum in spectrum-index order)"
                     % (rnum, idx, i))
            rrow, _ = state["ref_peak_counts"][i]
            before = parse_int_field(row["n_peaks_before_filtering"], "peak_counts.csv",
                                     rnum, "n_peaks_before_filtering")
            after = parse_int_field(row["n_peaks_after_filtering"], "peak_counts.csv",
                                    rnum, "n_peaks_after_filtering")
            if before < 0 or after < 0:
                fail("peak_counts.csv row %d has a negative peak count" % rnum)
            if before != int(rrow["n_peaks_before_filtering"]):
                fail("peak_counts.csv row %d: n_peaks_before_filtering %d differs from the "
                     "reference value %s" % (rnum, before, rrow["n_peaks_before_filtering"]))
            if after != int(rrow["n_peaks_after_filtering"]):
                fail("peak_counts.csv row %d: n_peaks_after_filtering %d differs from the "
                     "reference value %s" % (rnum, after, rrow["n_peaks_after_filtering"]))
        state["sub_peak_counts_after"] = [
            int(row["n_peaks_after_filtering"]) for row, _ in rows]
        return "peak counts before/after filtering match the reference exactly for all %d spectra" % n

    run("peak_counts_summary", "scientific", check_peak_counts)

    # ---------- 7. cross-output consistency ----------
    def check_consistency():
        need = ("sub_records", "sub_npz", "sub_peak_counts_after")
        for k in need:
            if k not in state:
                fail("cross-output consistency could not be evaluated: %s not available "
                     "(the corresponding check reports the underlying failure)" % k)
        after = state["sub_peak_counts_after"]
        npk = [len(rec["peaks"]) for rec in state["sub_records"]]
        gm = state["sub_npz"]["cosine_greedy_matches"]
        mm = state["sub_npz"]["modified_cosine_matches"]
        for i in range(n):
            if not (after[i] == npk[i] == int(gm[i, i]) == int(mm[i, i])):
                fail("spectrum %d: retained peak count %d, diagonal greedy matches %d and "
                     "diagonal modified matches %d are inconsistent"
                     % (i, npk[i], int(gm[i, i]), int(mm[i, i])))
        # Identifier join: every best_matches.csv row must carry the identifiers of
        # its matched_spectrum_index in the submission's own processed_spectra.json
        # (empty string where the spectrum's post-pipeline value is undefined).
        try:
            bm_rows = read_csv_rows(os.path.join(sub_dir, "best_matches.csv"),
                                    BEST_MATCHES_HEADER, "submission best_matches.csv")
        except CheckFailure:
            fail("cross-output consistency could not be evaluated: submission "
                 "best_matches.csv is missing or malformed (the corresponding check "
                 "reports the underlying failure)")
        for row, rnum in bm_rows:
            mi = parse_int_field(row["matched_spectrum_index"], "best_matches.csv",
                                 rnum, "matched_spectrum_index")
            if not (0 <= mi < n):
                fail("best_matches.csv row %d: matched_spectrum_index %d is out of range "
                     "for the identifier join to processed_spectra.json" % (rnum, mi))
            rec = state["sub_records"][mi]
            if row["matched_smiles"] != rec["smiles"]:
                fail("best_matches.csv row %d: matched_smiles does not equal the "
                     "matched_spectrum_index %d record of processed_spectra.json" % (rnum, mi))
            if row["matched_inchikey"] != rec["inchikey"]:
                fail("best_matches.csv row %d: matched_inchikey does not equal the "
                     "matched_spectrum_index %d record of processed_spectra.json" % (rnum, mi))
        return ("diagonal match counts equal each spectrum's retained peak count in "
                "processed_spectra.json and peak_counts.csv for all %d spectra, and every "
                "best_matches.csv row joins to the identifiers of its matched spectrum in "
                "processed_spectra.json" % n)

    run("cross_output_consistency", "scientific", check_consistency)

    passed = all(r["passed"] for r in results)
    report = {"passed": passed, "checks": results}
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

