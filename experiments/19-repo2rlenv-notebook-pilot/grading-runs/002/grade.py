#!/usr/bin/env python3
"""Acceptance grader for the per-cluster marker-gene (DE) analysis task.

Compares the submission's cluster_marker_genes.csv against the reference
cluster_marker_genes.csv on scientific content, aligned by the stable
(cluster, gene) key.

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys

VALUES = ("score", "pval", "pval_adj", "log2fc")
COLUMNS = ("cluster", "rank", "gene", "score", "pval", "pval_adj", "log2fc")

# --- numerical acceptance tolerances (see the public instruction) -------------
SCORE_ATOL = 2.0e-4      # absolute, on the Wilcoxon rank-sum z statistic
LOG2FC_ATOL = 1.0e-4     # absolute, on the stabilized log2 fold change
P_RTOL = 1.0e-2          # relative, on uncorrected and adjusted p-values
P_TINY = 1.0e-303        # p-value scale at/below which a reported 0 and any smaller
                        # retained value are treated as equivalent (see instruction)

NUMERIC_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


class Result:
    def __init__(self):
        self.checks = []

    def add(self, check_id, kind, requirement, passed, message):
        self.checks.append(
            {
                "id": check_id,
                "kind": kind,
                "artifacts": ["cluster_marker_genes.csv"],
                "public_requirement": requirement,
                "passed": bool(passed),
                "message": str(message),
            }
        )


def read_table(path):
    """Parse the CSV strictly: exact header, fixed field count, no blank fields."""
    if not os.path.isfile(path):
        return None, f"file not found: {path}"
    try:
        with open(path, "r", newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                return None, "file is empty"
            if tuple(header) != COLUMNS:
                return None, f"unexpected header {header!r}, expected {list(COLUMNS)}"
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return None, f"could not read file: {exc}"
    for i, r in enumerate(rows):
        if len(r) != len(COLUMNS):
            return None, f"row {i + 2} has {len(r)} fields, expected {len(COLUMNS)}"
        if any(f.strip() == "" for f in r):
            return None, f"blank field on row {i + 2}"
    table = [dict(zip(COLUMNS, r)) for r in rows]
    if not table:
        return None, "file contains no data rows"
    return table, None


def parse_number(text):
    """Parse a numeric CSV field; None when malformed or non-finite."""
    if text is None:
        return None
    s = text.strip()
    if s == "" or s.lower() in (
        "nan", "inf", "-inf", "+inf", "infinity", "-infinity", "+infinity",
    ):
        return None
    if not NUMERIC_RE.match(s):
        return None
    try:
        value = float(s)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(value):
        return None
    return value


def parse_rank(text):
    s = (text or "").strip()
    if not re.fullmatch(r"[+-]?\d+", s):
        return None
    value = int(s)
    if value <= 0:
        return None
    return value


def p_close(ref, sub):
    """p-value comparison: relative tolerance plus a 0/underflow equivalence zone.

    Below P_TINY the tail probability is produced by |z| >= ~37, where a
    reference-vs-submission difference in z of the score-tolerance scale
    (about 1e-4, from tie resolution and single-precision storage in the
    reference) changes the tail by orders of magnitude and can legitimately
    underflow to exactly 0 in one evaluation while remaining representable in
    another. Both faithful evaluations are therefore accepted within that
    zone, and Benjamini-Hochberg scaled values (the adjustment multiplies by
    m/j) stay inside it.
    """
    a = min(max(ref, 0.0), 1.0)
    b = min(max(sub, 0.0), 1.0)
    if a <= P_TINY and b <= P_TINY:
        return True
    if a <= P_TINY or b <= P_TINY:
        return False
    if a == 0.0 or b == 0.0:
        return False
    return abs(a - b) <= P_RTOL * min(a, b)


def order_key(label):
    s = label.strip()
    if re.fullmatch(r"[+-]?\d+", s):
        try:
            v = float(s)
        except ValueError:
            v = None
        if v is not None and math.isfinite(v):
            return (0, v, s)
    return (1, 0.0, s)


REQ_KEY_COVERAGE = (
    "One row for every (cluster label, gene identifier) pair of the "
    "reference cross product, each exactly once, using the same cluster "
    "labels and gene identifiers verbatim; the tested gene set is identical "
    "for every cluster and per-cluster row counts match.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    ref_path = os.path.join(args.reference_dir, "cluster_marker_genes.csv")
    sub_path = os.path.join(args.submission_dir, "cluster_marker_genes.csv")

    res = Result()
    ref, ref_err = read_table(ref_path)

    struct_req = (
        "cluster_marker_genes.csv exists, is a plain CSV with the exact header "
        "cluster,rank,gene,score,pval,pval_adj,log2fc, has a fixed number of "
        "fields on every row, and contains no blank or malformed fields."
    )
    fail_block = (
        ("row_key_coverage", "scientific",
         REQ_KEY_COVERAGE),
        ("row_ordering", "scientific",
         "Rows sorted by ascending numeric cluster label then ascending rank; "
         "rank is exactly 1..G within every cluster, where G is the number of "
         "tested genes; the cluster label is written verbatim and used "
         "consistently throughout the file."),
        ("numeric_finiteness", "scientific",
         "score, pval, pval_adj and log2fc are present on every row, parse as "
         "finite decimal numbers, contain no NaN/inf, and preserve non-zero "
         "values (no rounding away of meaningful zeros)."),
        ("score_agreement", "scientific",
         "The Wilcoxon rank-sum z-score of every (cluster, gene) agrees with "
         "the reference within the stated absolute tolerance."),
        ("pvalue_agreement", "scientific",
         "The uncorrected two-sided p-value of every (cluster, gene) agrees "
         "with the reference within the stated relative tolerance, treating "
         "underflowed zeros and subnormal tails as equivalent."),
        ("pvalue_adj_agreement", "scientific",
         "The Benjamini-Hochberg adjusted p-value of every (cluster, gene) "
         "agrees with the reference within the stated relative tolerance, "
         "treating underflowed zeros and subnormal tails as equivalent."),
        ("log2fc_agreement", "scientific",
         "The stabilized log2 fold change of every (cluster, gene) agrees "
         "with the reference within the stated absolute tolerance."),
        ("rank_consistency", "scientific",
         "The submitted within-cluster ranking is a valid descending-score "
         "ordering and is consistent with the reference's score ordering."),
    )

    if ref is None:
        res.add("reference_readable", "structural",
                "The reference table must be readable for validation to proceed.",
                False, f"reference unreadable: {ref_err}")
        emit(args.report, res)
        return 0

    sub, sub_err = read_table(sub_path)
    if sub is None:
        res.add("file_present_parseable", "structural", struct_req, False, sub_err)
        for cid, kind, req in fail_block:
            res.add(cid, kind, req, False, "submission table unreadable; check failed")
        emit(args.report, res)
        return 0

    res.add("file_present_parseable", "structural", struct_req, True,
            f"{len(sub)} data rows parsed with the required header")

    # ---------------------------------------------------------- key alignment
    ref_keys = [(r["cluster"], r["gene"]) for r in ref]
    sub_keys = [(r["cluster"], r["gene"]) for r in sub]
    ref_set = set(ref_keys)
    sub_set = set(sub_keys)
    dup = len(sub_keys) - len(sub_set)
    missing = ref_set - sub_set
    extra = sub_set - ref_set
    coverage_ok = dup == 0 and not missing and not extra
    if coverage_ok:
        res.add("row_key_coverage", "scientific", REQ_KEY_COVERAGE, True,
                f"{len(sub_set)} (cluster, gene) pairs match the reference exactly")
    else:
        res.add("row_key_coverage", "scientific", REQ_KEY_COVERAGE, False,
                f"duplicate rows: {dup}; missing pairs: {len(missing)} "
                f"(e.g. {sorted(missing)[:3]}); unexpected pairs: {len(extra)} "
                f"(e.g. {sorted(extra)[:3]})")

    ref_by_key = {k: r for k, r in zip(ref_keys, ref)}
    sub_by_key = {k: r for k, r in zip(sub_keys, sub)}

    # per-cluster reference gene sets for rank checks
    clusters = {}
    for k in ref_keys:
        clusters.setdefault(k[0], set()).add(k[1])
    g_ref = len(next(iter(clusters.values()))) if clusters else 0

    # -------------------------------------------------------- ordering / rank
    order_msgs = []
    file_keys = [(r["cluster"], parse_rank(r["rank"])) for r in sub]
    if any(rk is None for _, rk in file_keys):
        order_msgs.append("some rank values are not positive integers")
        ranks_ok = False
    else:
        expected = sorted(file_keys, key=lambda t: (order_key(t[0]), t[1]))
        ranks_ok = file_keys == expected
        if not ranks_ok:
            order_msgs.append("rows are not sorted by ascending numeric cluster label then ascending rank")
    for label, genes in clusters.items():
        rows = [r for r in sub if r["cluster"] == label]
        ranks = [parse_rank(r["rank"]) for r in rows]
        if any(v is None for v in ranks):
            if "some rank values are not positive integers" not in order_msgs:
                order_msgs.append(f"cluster {label}: rank is not a positive integer")
            continue
        if len(rows) != len(genes) or sorted(ranks) != list(range(1, len(genes) + 1)):
            order_msgs.append(f"cluster {label}: ranks are not exactly 1..{len(genes)}")
            ranks_ok = False
    res.add("row_ordering", "scientific", fail_block[1][2], ranks_ok,
            "; ".join(order_msgs) if order_msgs else
            f"rows ordered by ascending numeric cluster then rank; ranks 1..{g_ref} in every cluster")

    # ------------------------------------------------------- numeric validity
    bad_numeric = []
    for r in sub:
        for col in VALUES:
            v = parse_number(r[col])
            if v is None:
                bad_numeric.append((r["cluster"], r["gene"], col, r[col]))
                continue
            if col in ("pval", "pval_adj") and not (0.0 <= v <= 1.0):
                bad_numeric.append((r["cluster"], r["gene"], col, r[col]))
    if bad_numeric:
        res.add("numeric_finiteness", "scientific", fail_block[2][2], False,
                f"invalid values: {bad_numeric[:5]}")
    else:
        res.add("numeric_finiteness", "scientific", fail_block[2][2], True,
                "all score/pval/pval_adj/log2fc values present, finite and in range")

    # ----------------------------------------------------- numeric agreement
    comparable = coverage_ok and not bad_numeric
    if comparable:
        fails = {c: [] for c in VALUES}
        for key in ref_keys:
            rr = ref_by_key[key]
            sr = sub_by_key[key]
            a_score = parse_number(rr["score"])
            b_score = parse_number(sr["score"])
            if a_score is None or b_score is None:
                fails["score"].append((key, "non-finite"))
                continue
            if abs(a_score - b_score) > SCORE_ATOL:
                fails["score"].append((key, f"{a_score!r} vs {b_score!r} "
                                            f"(|diff| = {abs(a_score - b_score):.3g} > {SCORE_ATOL:g})"))
            a_fc = parse_number(rr["log2fc"])
            b_fc = parse_number(sr["log2fc"])
            if a_fc is None or b_fc is None:
                fails["log2fc"].append((key, "non-finite"))
            elif abs(a_fc - b_fc) > LOG2FC_ATOL:
                fails["log2fc"].append((key, f"{a_fc!r} vs {b_fc!r} "
                                             f"(|diff| = {abs(a_fc - b_fc):.3g} > {LOG2FC_ATOL:g})"))
            for col in ("pval", "pval_adj"):
                a = parse_number(rr[col])
                b = parse_number(sr[col])
                if a is None or b is None:
                    fails[col].append((key, "non-finite"))
                elif not p_close(a, b):
                    fails[col].append((key, f"{a!r} vs {b!r} (relative difference "
                                            f"{abs(a - b) / max(min(abs(a), abs(b)), 1e-300):.3g} "
                                            f"> {P_RTOL:g})"))
        for col, cid, req in (
            ("score", "score_agreement", fail_block[3][2]),
            ("pval", "pvalue_agreement", fail_block[4][2]),
            ("pval_adj", "pvalue_adj_agreement", fail_block[5][2]),
            ("log2fc", "log2fc_agreement", fail_block[6][2]),
        ):
            if fails[col]:
                key, why = fails[col][0]
                res.add(cid, "scientific", req, False,
                        f"{len(fails[col])} of {len(ref_keys)} {col} values disagree; "
                        f"first: {key} {why}")
            else:
                res.add(cid, "scientific", req, True,
                        f"all {len(ref_keys)} {col} values agree within tolerance")
    else:
        for cid, _kind, req in fail_block[3:]:
            res.add(cid, "scientific", req, False,
                    "row keys do not align or values are invalid; comparison not possible")

    # ------------------------------------------------------- rank consistency
    if coverage_ok:
        rank_ok = True
        rank_msgs = []
        for label in clusters:
            rows = [r for r in sub if r["cluster"] == label and parse_rank(r["rank"]) is not None]
            rows.sort(key=lambda r: parse_rank(r["rank"]))
            ref_scores = []
            for r in rows:
                v = parse_number(ref_by_key[(r["cluster"], r["gene"])]["score"])
                ref_scores.append(v if v is not None else 0.0)
            own_scores = []
            for r in rows:
                v = parse_number(r["score"])
                own_scores.append(v if v is not None else 0.0)
            prev_ref = None
            prev_own = None
            for i, (rv, ov) in enumerate(zip(ref_scores, own_scores)):
                if prev_ref is not None and rv > prev_ref + SCORE_ATOL:
                    rank_ok = False
                    if len(rank_msgs) < 3:
                        rank_msgs.append(
                            f"cluster {label}: reference score increases by "
                            f"{rv - prev_ref:.3g} between submitted ranks {i} and {i + 1}")
                if prev_own is not None and ov > prev_own + SCORE_ATOL:
                    rank_ok = False
                    if len(rank_msgs) < 6:
                        rank_msgs.append(
                            f"cluster {label}: submitted score increases by "
                            f"{ov - prev_own:.3g} between ranks {i} and {i + 1}")
                prev_ref = rv
                prev_own = ov
        res.add("rank_consistency", "scientific", fail_block[7][2], rank_ok,
                "; ".join(rank_msgs) if rank_msgs else
                "within-cluster ranking is a valid descending-score order consistent with the reference")
    else:
        res.add("rank_consistency", "scientific", fail_block[7][2], False,
                "row keys do not align; ranking not comparable")

    emit(args.report, res)
    return 0


def emit(path, result):
    payload = {
        "passed": all(c["passed"] for c in result.checks),
        "checks": [
            {"id": c["id"], "passed": c["passed"], "message": c["message"]}
            for c in result.checks
        ],
    }
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


if __name__ == "__main__":
    sys.exit(main())

