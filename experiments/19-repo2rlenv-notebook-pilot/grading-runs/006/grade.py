#!/usr/bin/env python3
"""Acceptance grader for the per-cluster marker-gene (DE) analysis task.

Compares the submission's cluster_marker_genes.csv against the reference
cluster_marker_genes.csv on scientific content, aligned by the stable
(cluster, gene) key.

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH

Every declared check is emitted exactly once in every scenario (valid,
missing, unreadable or malformed submission; unreadable reference).
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
P_TINY = 1.0e-303        # tail scale at/below which a reported 0 and any
                        # smaller retained value are treated as equivalent

NUMERIC_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

# --- declared checks, in report order ----------------------------------------
CHECK_ORDER = (
    "file_present_parseable",
    "row_key_coverage",
    "row_ordering",
    "numeric_finiteness",
    "score_agreement",
    "pvalue_agreement",
    "pvalue_adj_agreement",
    "log2fc_agreement",
    "rank_consistency",
)


class Results:
    """Collects exactly one result per declared check id."""

    def __init__(self):
        self._data = {cid: [False, "not evaluated"] for cid in CHECK_ORDER}

    def set(self, check_id, passed, message):
        if check_id not in self._data:
            raise KeyError(f"undeclared check id {check_id!r}")
        self._data[check_id] = [bool(passed), str(message)]

    def fail_all(self, message):
        for check_id in CHECK_ORDER:
            self.set(check_id, False, message)

    def emit(self, path):
        payload = {
            "passed": all(v[0] for v in self._data.values()),
            "checks": [
                {"id": cid, "passed": self._data[cid][0],
                 "message": self._data[cid][1]}
                for cid in CHECK_ORDER
            ],
        }
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)


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
    """p-value comparison: relative tolerance plus a 0/underflow equivalence
    zone.

    At or below P_TINY the tail probability belongs to |z| far beyond the
    point where a double-precision two-sided tail can remain representable,
    so a faithful evaluation may legitimately underflow to exactly 0 in one
    implementation while remaining representable in another (and
    Benjamini-Hochberg scaling by m/j keeps adjusted values that arise from
    such tails inside the same zone). Both are accepted within the zone; a
    reported 0 against a reference value above the zone is a failure, not an
    equivalence.
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
    """Ascending numeric cluster label ordering, with a non-numeric fallback."""
    s = label.strip()
    if re.fullmatch(r"[+-]?\d+", s):
        try:
            v = float(s)
        except ValueError:
            v = None
        if v is not None and math.isfinite(v):
            return (0, v, s)
    return (1, 0.0, s)


def describe_alignment(dup, missing, extra):
    parts = []
    if dup:
        parts.append(f"duplicate rows: {dup}")
    if missing:
        parts.append(f"missing pairs: {len(missing)} (e.g. {sorted(missing)[:3]})")
    if extra:
        parts.append(f"unexpected pairs: {len(extra)} (e.g. {sorted(extra)[:3]})")
    return "; ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    ref_path = os.path.join(args.reference_dir, "cluster_marker_genes.csv")
    sub_path = os.path.join(args.submission_dir, "cluster_marker_genes.csv")

    res = Results()

    ref, ref_err = read_table(ref_path)
    if ref is None:
        # Unreachable for the fixed reference, but keep the report contract:
        # every declared check, exactly once, failed with the cause.
        res.fail_all(f"reference table unreadable: {ref_err}")
        res.emit(args.report)
        return 0

    sub, sub_err = read_table(sub_path)
    if sub is None:
        res.set("file_present_parseable", False, sub_err)
        for cid in CHECK_ORDER[1:]:
            res.set(cid, False, "submission table unreadable; check failed")
        res.emit(args.report)
        return 0

    res.set("file_present_parseable", True,
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
    res.set(
        "row_key_coverage", coverage_ok,
        (f"{len(sub_set)} (cluster, gene) pairs match the reference exactly"
         if coverage_ok else
         "row keys do not match the reference cross product: "
         + describe_alignment(dup, missing, extra)),
    )

    ref_by_key = {k: r for k, r in zip(ref_keys, ref)}
    sub_by_key = {k: r for k, r in zip(sub_keys, sub)}

    # reference per-cluster gene sets (authoritative G per cluster)
    ref_clusters = {}
    for k in ref_keys:
        ref_clusters.setdefault(k[0], set()).add(k[1])
    g_ref = max((len(v) for v in ref_clusters.values()), default=0)

    # submission rows grouped by cluster label, one pass
    sub_groups = {}
    for r in sub:
        sub_groups.setdefault(r["cluster"], []).append(r)

    # -------------------------------------------------------- ordering / rank
    order_msgs = []
    ranks_ok = True
    parsed_ranks = []
    for r in sub:
        rk = parse_rank(r["rank"])
        parsed_ranks.append(rk)
        if rk is None:
            ranks_ok = False
    if ranks_ok:
        file_keys = [(r["cluster"], rk) for r, rk in zip(sub, parsed_ranks)]
        if file_keys != sorted(file_keys, key=lambda t: (order_key(t[0]), t[1])):
            order_msgs.append(
                "rows are not sorted by ascending numeric cluster label then "
                "ascending rank")
            ranks_ok = False
    else:
        order_msgs.append("some rank values are not positive integers")

    unmatched = sorted(set(sub_groups) - set(ref_clusters))
    if unmatched:
        order_msgs.append(
            f"cluster labels absent from the reference grouping: {unmatched[:5]}")
        ranks_ok = False
    for label, genes in sorted(ref_clusters.items(), key=lambda kv: order_key(kv[0])):
        rows = sub_groups.get(label, [])
        ranks = sorted(rk for rk in
                       (parse_rank(r["rank"]) for r in rows) if rk is not None)
        if len(rows) != len(genes):
            order_msgs.append(
                f"cluster {label}: {len(rows)} rows for {len(genes)} tested genes")
            ranks_ok = False
        elif ranks != list(range(1, len(genes) + 1)):
            order_msgs.append(f"cluster {label}: ranks are not exactly 1..{len(genes)}")
            ranks_ok = False
    res.set(
        "row_ordering", ranks_ok,
        ("; ".join(order_msgs) if order_msgs else
         f"rows ordered by ascending numeric cluster then rank; "
         f"ranks 1..{g_ref} in every cluster"),
    )

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
    res.set(
        "numeric_finiteness", not bad_numeric,
        ("all score/pval/pval_adj/log2fc values present, finite and in range"
         if not bad_numeric else
         f"invalid numeric values: {bad_numeric[:5]}"),
    )

    def blocked_message(check_desc):
        if not coverage_ok:
            return ("row keys do not align with the reference cross product ("
                    + describe_alignment(dup, missing, extra)
                    + "); " + check_desc + " not possible")
        return (f"{len(bad_numeric)} numeric values are missing, invalid or out of "
                f"range (first: {bad_numeric[:3]}); " + check_desc
                + " not possible")

    # ----------------------------------------------------- numeric agreement
    if coverage_ok and not bad_numeric:
        abs_fails = {"score": [], "log2fc": []}
        p_fails = {"pval": [], "pval_adj": []}
        for key in ref_keys:
            rr = ref_by_key[key]
            sr = sub_by_key[key]
            for col, fails in abs_fails.items():
                a = parse_number(rr[col])
                b = parse_number(sr[col])
                tol = SCORE_ATOL if col == "score" else LOG2FC_ATOL
                if a is None or b is None:
                    fails.append((key, "non-finite"))
                elif abs(a - b) > tol:
                    fails.append((key, f"{a!r} vs {b!r} "
                                         f"(|diff| = {abs(a - b):.3g} > {tol:g})"))
            for col, fails in p_fails.items():
                a = parse_number(rr[col])
                b = parse_number(sr[col])
                if a is None or b is None:
                    fails.append((key, "non-finite"))
                elif not p_close(a, b):
                    if a == 0.0 or b == 0.0:
                        reported, refv = (b, a) if b == 0.0 else (a, b)
                        fails.append((key, f"reported {reported!r} where the "
                                              f"reference value is {refv!r}, "
                                              f"above the underflow-equivalence "
                                              f"zone ({P_TINY:g})"))
                    else:
                        fails.append((key, f"{a!r} vs {b!r} (relative difference "
                                                f"{abs(a - b) / min(a, b):.3g} "
                                                f"> {P_RTOL:g})"))
        for cid, col, fails, desc in (
            ("score_agreement", "score", abs_fails["score"], "absolute"),
            ("pvalue_agreement", "pval", p_fails["pval"], "relative"),
            ("pvalue_adj_agreement", "pval_adj", p_fails["pval_adj"], "relative"),
            ("log2fc_agreement", "log2fc", abs_fails["log2fc"], "absolute"),
        ):
            if fails:
                key, why = fails[0]
                res.set(cid, False,
                        f"{len(fails)} of {len(ref_keys)} {col} values disagree; "
                        f"first: {key} {why}")
            else:
                res.set(cid, True,
                        f"all {len(ref_keys)} {col} values agree within tolerance")
    else:
        for cid in ("score_agreement", "pvalue_agreement",
                    "pvalue_adj_agreement", "log2fc_agreement"):
            res.set(cid, False,
                    blocked_message("numerical comparison"))

    # ------------------------------------------------------- rank consistency
    bad_rank = next((r["rank"] for r in sub if parse_rank(r["rank"]) is None), None)
    if not coverage_ok:
        res.set("rank_consistency", False,
                "row keys do not align with the reference cross product; "
                "ranking not comparable")
    elif bad_numeric:
        res.set("rank_consistency", False,
                f"{len(bad_numeric)} numeric values are missing, invalid or out "
                f"of range (first: {bad_numeric[:3]}); the submitted ranking "
                f"cannot be verified")
    elif bad_rank is not None:
        res.set("rank_consistency", False,
                f"the rank column holds a value that is not a positive integer "
                f"(first: {bad_rank!r}); the submitted ranking cannot be "
                f"established")
    else:
        rank_ok = True
        rank_msgs = []
        for label in sorted(ref_clusters, key=order_key):
            # (reference scores always parse for the fixed reference table; a
            # defensive check keeps any anomaly a failed check, not a crash)
            if any(parse_number(r["score"]) is None for r in sub_groups[label]):
                rank_ok = False
                rank_msgs.append(
                    f"cluster {label}: a submitted score does not parse as a "
                    f"finite number")
                continue
            rows = sorted(sub_groups[label], key=lambda r: parse_rank(r["rank"]))
            ref_scores = [parse_number(ref_by_key[(r["cluster"], r["gene"])]["score"])
                          for r in rows]
            own_scores = [parse_number(r["score"]) for r in rows]
            prev_ref = None
            prev_own = None
            for i, (rv, ov) in enumerate(zip(ref_scores, own_scores)):
                if rv is None or ov is None:
                    rank_ok = False
                    if len(rank_msgs) < 6:
                        rank_msgs.append(
                            f"cluster {label}: a score value could not be "
                            f"parsed at submitted rank {i + 1}")
                    continue
                if prev_ref is not None and rv > prev_ref + SCORE_ATOL:
                    rank_ok = False
                    if len(rank_msgs) < 3:
                        rank_msgs.append(
                            f"cluster {label}: reference score increases by "
                            f"{rv - prev_ref:.3g} between submitted ranks {i} "
                            f"and {i + 1}")
                if prev_own is not None and ov > prev_own + SCORE_ATOL:
                    rank_ok = False
                    if len(rank_msgs) < 6:
                        rank_msgs.append(
                            f"cluster {label}: submitted score increases by "
                            f"{ov - prev_own:.3g} between ranks {i} and {i + 1}")
                prev_ref = rv
                prev_own = ov
        res.set(
            "rank_consistency", rank_ok,
            ("; ".join(rank_msgs) if rank_msgs else
             "within-cluster ranking is a valid descending-score order "
             "consistent with the reference"),
        )

    res.emit(args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

