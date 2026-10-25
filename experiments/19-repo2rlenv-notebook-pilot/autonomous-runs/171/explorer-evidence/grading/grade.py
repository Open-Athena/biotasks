#!/usr/bin/env python3
"""Grader for the GNPS-NIH natural-products spectral similarity task.

Compares the six declared CSV outputs between a reference directory and a
submission directory by parsed scientific content (not bytes).
"""
import argparse
import csv
import json
import math
import os

SCORE_TOL = 1e-12  # absolute tolerance on cosine scores (values lie in [0, ~1])

IDENT_FILE = "spectrum_identifiers.csv"
IDENT_HEADER = ["spectrum_index", "inchikey", "smiles"]
MATCH_HEADER = ["rank", "matched_spectrum_index", "inchikey", "smiles",
               "cosine_score", "matched_peak_count"]
MATCH_TABLES = [
    ("cosine_spectrum_5_top10.csv", "cosine_spectrum_5_top10"),
    ("cosine_spectrum_5_min5.csv", "cosine_spectrum_5_min5"),
    ("modified_cosine_spectrum_5_min5.csv", "modified_cosine_spectrum_5_min5"),
    ("modified_cosine_spectrum_11_min5.csv", "modified_cosine_spectrum_11_min5"),
    ("modified_cosine_spectrum_97_min5.csv", "modified_cosine_spectrum_97_min5"),
]
CHECK_IDS = [
    "identifiers",
    "cosine_spectrum_5_top10",
    "cosine_spectrum_5_min5",
    "modified_cosine_spectrum_5_min5",
    "modified_cosine_spectrum_11_min5",
    "modified_cosine_spectrum_97_min5",
]


def parse_float(s):
    v = float(s)
    if not math.isfinite(v):
        raise ValueError("nonfinite value")
    return v


def parse_int(s):
    if not s.isdigit():
        raise ValueError("not a nonnegative integer")
    return int(s)


def read_csv_rows(path):
    if not os.path.isfile(path):
        return None, "missing file"
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.reader(fh) if r != []]
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return None, "unreadable file: %s" % e
    return rows, "ok"


def load_identifiers(path):
    rows, status = read_csv_rows(path)
    if rows is None:
        return None, status
    if not rows or rows[0] != IDENT_HEADER:
        return None, "header is not spectrum_index,inchikey,smiles"
    out = []
    for r in rows[1:]:
        if len(r) != 3:
            return None, "row with %d fields (expected 3)" % len(r)
        try:
            out.append((parse_int(r[0]), r[1], r[2]))
        except ValueError as e:
            return None, "bad spectrum_index value: %s" % e
    return out, "ok"


def load_match_table(path):
    rows, status = read_csv_rows(path)
    if rows is None:
        return None, status
    if not rows or rows[0] != MATCH_HEADER:
        return None, ("header is not "
                      "rank,matched_spectrum_index,inchikey,smiles,cosine_score,matched_peak_count")
    out = []
    for r in rows[1:]:
        if len(r) != 6:
            return None, "row with %d fields (expected 6)" % len(r)
        try:
            out.append((parse_int(r[0]), parse_int(r[1]), r[2], r[3],
                        parse_float(r[4]), parse_int(r[5])))
        except ValueError as e:
            return None, "bad cell value: %s" % e
    return out, "ok"


def check_identifiers(ref, sub):
    if len(sub) != len(ref):
        return False, "row count %d != required %d" % (len(sub), len(ref))
    for i, (s, r) in enumerate(zip(sub, ref)):
        if s[0] != i:
            return False, "spectrum_index at row %d is %r (expected %d)" % (i, s[0], i)
        if (s[1], s[2]) != (r[1], r[2]):
            if any(t[0] == s[0] and (t[1], t[2]) == (s[1], s[2]) for t in ref):
                continue  # row repositioned within an identical-identifier duplicate group
            return False, "row %d: inchikey/smiles mismatch" % i
    return True, "matched"


def check_match_table(ref, sub, n_ident, sub_ident):
    msgs = []
    for i, r in enumerate(sub):
        if r[0] != i:
            msgs.append("rank column is not 0,1,...,n-1 in file order")
            break
    inv = None
    for i in range(len(sub) - 1):
        if sub[i][4] < sub[i + 1][4] - SCORE_TOL:
            if inv is None:
                inv = i
    if inv is not None:
        msgs.append("rows not sorted by descending cosine_score "
                    "(first inversion at rank %d/%d)" % (inv, inv + 1))
    if n_ident is not None and not all(0 <= r[1] < n_ident for r in sub):
        msgs.append("matched_spectrum_index out of range")
    idxs = [r[1] for r in sub]
    if len(set(idxs)) != len(idxs):
        msgs.append("duplicate matched_spectrum_index")
    ref_map = {r[1]: (r[2], r[3], r[4], r[5]) for r in ref}
    if set(idxs) != set(ref_map):
        only_sub = sorted(set(idxs) - set(ref_map))
        only_ref = sorted(set(ref_map) - set(idxs))
        msgs.append("matched spectrum index set differs from reference "
                    "(unexpected: %s; missing: %s)" % (only_sub[:5], only_ref[:5]))
    else:
        # value comparison for every included spectrum index
        for r in sub:
            rik, rsm, rscore, rcount = ref_map[r[1]]
            if (r[2], r[3]) != (rik, rsm):
                msgs.append("matched index %d: inchikey/smiles mismatch" % r[1])
            if abs(r[4] - rscore) > SCORE_TOL:
                msgs.append("matched index %d: cosine_score %r differs from reference %r"
                            % (r[1], r[4], rscore))
            if r[5] != rcount:
                msgs.append("matched index %d: matched_peak_count %d != reference %d"
                            % (r[1], r[5], rcount))
        # ordering may differ from the reference order only inside blocks of
        # equal (within tolerance) reference scores, i.e. genuine score ties.
        ref_pos = {r[1]: i for i, r in enumerate(ref)}
        for i, r in enumerate(sub):
            j = ref_pos.get(r[1])
            if j is None or j == i:
                continue
            lo, hi = min(i, j), max(i, j)
            if any(abs(ref[k][4] - r[4]) > SCORE_TOL for k in range(lo, hi + 1)):
                msgs.append("rank order differs from reference beyond equal-score tie "
                            "blocks (index %d at rank %d vs reference rank %d)"
                            % (r[1], i, j))
                break
    if sub_ident is not None and len(sub) == len(sub_ident):
        for r in sub:
            if not (0 <= r[1] < len(sub_ident)) or sub_ident[r[1]][1:3] != (r[2], r[3]):
                msgs.append("matched index %d: inchikey/smiles inconsistent with the "
                            "submission's own spectrum_identifiers.csv" % r[1])
                break
    if msgs:
        return False, "; ".join(msgs)
    return True, "matched"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    results = {}
    ref_ident = None
    ref_n = None
    sub_ident = None
    try:
        ref_ident, st = load_identifiers(os.path.join(args.reference_dir, IDENT_FILE))
        if ref_ident is None:
            results["identifiers"] = (False,
                                      "reference identifiers table unreadable: %s" % st)
        else:
            ref_n = len(ref_ident)

        sub_ident, st = load_identifiers(os.path.join(args.submission_dir, IDENT_FILE))
        if sub_ident is None:
            results["identifiers"] = (False,
                                      "spectrum_identifiers.csv rejected: %s" % st)
        elif ref_ident is None:
            results["identifiers"] = (False, "reference identifiers table unreadable")
        else:
            results["identifiers"] = check_identifiers(ref_ident, sub_ident)

        for fname, cid in MATCH_TABLES:
            sub_rows, sst = load_match_table(os.path.join(args.submission_dir, fname))
            if sub_rows is None:
                results[cid] = (False, "%s rejected: %s" % (fname, sst))
                continue
            ref_rows, rst = load_match_table(os.path.join(args.reference_dir, fname))
            if ref_rows is None:
                results[cid] = (False, "reference table unreadable: %s" % rst)
                continue
            if not sub_rows:
                results[cid] = (False, "%s has no data rows (expected %d)"
                                % (fname, len(ref_rows)))
                continue
            n_ident = ref_n if ref_n is not None else (len(sub_ident) if sub_ident else None)
            results[cid] = check_match_table(ref_rows, sub_rows, n_ident, sub_ident)
    except Exception as e:  # never crash: fail every declared check instead
        for cid in CHECK_IDS:
            if cid not in results:
                results[cid] = (False, "grader error: %s" % e)

    for cid in CHECK_IDS:
        if cid not in results:
            results[cid] = (False, "check not executed")

    checks = [{"id": cid, "passed": bool(results[cid][0]), "message": results[cid][1]}
              for cid in CHECK_IDS]
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump({"passed": all(c["passed"] for c in checks), "checks": checks}, fh)


if __name__ == "__main__":
    main()

