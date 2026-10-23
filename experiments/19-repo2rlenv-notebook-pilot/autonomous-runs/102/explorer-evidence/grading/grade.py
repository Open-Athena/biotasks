#!/usr/bin/env python3
"""Deterministic grader for the CTCF motif-to-peak assignment task.

Comparisons against the reference copies:
  * peaks_with_strongest_motif_blacklist_filtered.csv  (multiset of rows)
  * motifs_per_peak.csv                                (positional sequence)

Scientific comparison basis:
  * chromosome labels and strand are compared by exact text (no renaming or
    canonicalization);
  * coordinates and counts are compared as exact parsed integer values,
    and counts must be nonnegative;
  * fc and pval_2 are compared as exact parsed decimal values (no tolerance,
    no rounding, no rescaling).
Numeric tokens must use plain decimal grammar; any two textual forms that
conform and parse to the same value (trailing zeros, an optional decimal
point, an optional leading '+' sign, '0' vs '0.0') are value-equal and are
not distinguished. Tokens carrying exponents, underscores, padded
whitespace or non-finite spellings are rejected.
Row order of the peak table is not a scientific target (order-insensitive
multiset comparison with multiplicity); the counts file is compared
positionally because its row order encodes the peak-record correspondence.

The no-motif sentinel encoding: rows with no assigned motif must have empty
chrom_2/start_2/end_2/strand_2 and pval_2 equal to -1 or an empty field
(parsed-value equality: '-1', '-1.0' and '' are all accepted).
"""
import argparse
import csv
import decimal
import json
import os
import re
from collections import Counter

OUT_TABLE = "peaks_with_strongest_motif_blacklist_filtered.csv"
OUT_COUNTS = "motifs_per_peak.csv"
TABLE_HEADER = ["chrom", "start", "end", "fc",
                "chrom_2", "start_2", "end_2", "pval_2", "strand_2"]
COUNTS_HEADER = ["motifs_per_peak"]
SENTINEL = -1  # compared as exact Decimal value

_DEC_GRAMMAR = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
_CTX = decimal.Context(Emax=decimal.MAX_EMAX, Emin=decimal.MIN_EMIN,
                       traps=[decimal.InvalidOperation, decimal.Overflow])


def read_csv(path, ncols):
    """Read a CSV file, returning (header, body). Raises ValueError on any
    structural problem (missing file, no header, ragged rows)."""
    if not os.path.isfile(path):
        raise ValueError("required file not found: %s" % path)
    with open(path, "r", newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError("file is empty; header line missing")
    header = rows[0]
    body = rows[1:]
    for i, row in enumerate(body):
        if len(row) != ncols:
            raise ValueError("data row %d has %d fields; expected %d"
                             % (i + 2, len(row), ncols))
    return header, body


def plain_decimal(text, what):
    """Parse a plain-decimal numeric token to an exact Decimal.

    The token must conform to plain decimal grammar: an optional sign, then
    digits with an optional fractional part (an empty fractional part such as
    in '5.' or a bare '.5' is accepted). Exponent/scientific notation,
    underscores and padded whitespace are not part of the grammar and are
    rejected, as are non-finite spellings (NaN/Infinity)."""
    if text == "":
        raise ValueError("%s: empty field where a finite number is required"
                         % what)
    if not _DEC_GRAMMAR.fullmatch(text):
        raise ValueError("%s: token %r is not a plain decimal number "
                         "(no exponents, underscores or padded whitespace)"
                         % (what, text))
    try:
        d = _CTX.create_decimal(text)
    except (decimal.InvalidOperation, decimal.Overflow, ValueError,
            ArithmeticError):
        raise ValueError("%s: value does not parse to a finite number" % what)
    if not d.is_finite():
        raise ValueError("%s: value is not a finite number (NaN/Inf)" % what)
    return d


def plain_int(text, what):
    """Parse a plain-decimal token whose value must be a whole number.

    '0' and '0.0' are not distinguished because both parse to the same
    integer value; a fractional value such as '2.5' is rejected."""
    d = plain_decimal(text, what)
    if d != d.to_integral_value():
        raise ValueError("%s: value is not an integer; counts and "
                         "coordinates must be whole numbers" % what)
    return d


def normalize_table_row(row):
    """Normalize one 9-field data row of the peak table to a hashable tuple.

    Motif-bearing rows keep the parsed (chrom_2, start_2, end_2, pval_2,
    strand_2) values; no-motif rows carry None for all five. Numeric fields
    compare by exact parsed value: '-1', '-1.0' and an empty pval_2 field all
    encode the no-assignment sentinel, and '1234.0' equals the integer
    '1234'."""
    if row[0] == "":
        raise ValueError("chrom: empty chromosome label")
    start = plain_int(row[1], "start")
    end = plain_int(row[2], "end")
    if start < 0 or end < 0:
        raise ValueError("fragment coordinates must be nonnegative")
    if start >= end:
        raise ValueError("fragment interval has start >= end")
    fc = plain_decimal(row[3], "fc")
    present = [row[i] != "" for i in (4, 5, 6, 8)]
    if any(present) and not all(present):
        raise ValueError("motif fields (chrom_2, start_2, end_2, strand_2) "
                         "must be all present or all empty")
    if all(present):
        if row[4] == "":
            raise ValueError("chrom_2: empty chromosome label")
        start_2 = plain_int(row[5], "start_2")
        end_2 = plain_int(row[6], "end_2")
        if start_2 < 0 or end_2 < 0:
            raise ValueError("assigned motif coordinates must be nonnegative")
        if start_2 >= end_2:
            raise ValueError("assigned motif interval has start_2 >= end_2")
        pval_2 = plain_decimal(row[7], "pval_2")
        if pval_2 == SENTINEL:
            raise ValueError("pval_2: motif row carries the no-assignment "
                             "sentinel value -1")
        strand_2 = row[8]
        if strand_2 not in ("+", "-"):
            raise ValueError("strand_2 must be '+' or '-', got %r" % strand_2)
        return (row[0], start, end, fc, row[4], start_2, end_2, pval_2,
                strand_2)
    # no assigned motif: pval_2 must be -1 or empty (both encode the sentinel)
    if row[7] == "":
        pass
    else:
        if plain_decimal(row[7], "pval_2") != SENTINEL:
            raise ValueError("pval_2: row without a motif assignment must "
                             "carry the sentinel -1 (or an empty field)")
    return (row[0], start, end, fc, None, None, None, None, None)


def normalize_counts(body):
    """Parse the single-column count rows. Counts are whole numbers and must
    be nonnegative (a count of overlapping motifs cannot be negative)."""
    counts = []
    for i, row in enumerate(body):
        v = plain_int(row[0], "motifs_per_peak row %d" % (i + 2))
        if v < 0:
            raise ValueError("motifs_per_peak row %d: count is negative; "
                             "counts must be nonnegative" % (i + 2))
        counts.append(v)
    return counts


def multiset_diff(ref_counter, sub_counter):
    missing = ref_counter - sub_counter   # in reference, not in submission
    extra = sub_counter - ref_counter     # in submission, not in reference
    return missing, extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    out = []

    def add(cid, ok, msg):
        out.append({"id": cid, "passed": bool(ok), "message": msg})

    sub_table_path = os.path.join(args.submission_dir, OUT_TABLE)
    sub_counts_path = os.path.join(args.submission_dir, OUT_COUNTS)

    # ---- load submissions defensively (missing/malformed -> failed checks)
    sub_table = None       # (header, body) or None
    sub_table_err = None
    try:
        sub_table = read_csv(sub_table_path, 9)
    except Exception as e:
        sub_table_err = str(e)

    sub_counts = None
    sub_counts_err = None
    try:
        sub_counts = read_csv(sub_counts_path, 1)
    except Exception as e:
        sub_counts_err = str(e)

    # ---- load + normalize reference (same code path)
    ref_rows = None
    ref_rows_err = None
    try:
        _, ref_body = read_csv(os.path.join(args.reference_dir, OUT_TABLE), 9)
        ref_rows = [normalize_table_row(r) for r in ref_body]
    except Exception as e:
        ref_rows_err = "reference table problem: %s" % e

    ref_counts = None
    ref_counts_err = None
    try:
        _, ref_cbody = read_csv(os.path.join(args.reference_dir, OUT_COUNTS), 1)
        ref_counts = normalize_counts(ref_cbody)
    except Exception as e:
        ref_counts_err = "reference counts problem: %s" % e

    # ---------------- Check 1: peaks table structure ----------------
    if sub_table_err is not None:
        add("peaks_table_structure", False, sub_table_err)
    elif sub_table[0] != TABLE_HEADER:
        add("peaks_table_structure", False,
            "header mismatch: expected %s, got %s" % (TABLE_HEADER,
                                                      sub_table[0]))
    else:
        ok = True
        msg = ("file present with the required header and 9 fields per row; "
               "all rows satisfy the row-validity rules")
        try:
            for row in sub_table[1]:
                normalize_table_row(row)
        except ValueError as e:
            ok = False
            msg = str(e)
        add("peaks_table_structure", ok, msg)

    # ---------------- Check 2: counts file structure ----------------
    if sub_counts_err is not None:
        add("motifs_per_peak_structure", False, sub_counts_err)
    elif sub_counts[0] != COUNTS_HEADER:
        add("motifs_per_peak_structure", False,
            "header mismatch: expected %s, got %s" % (COUNTS_HEADER,
                                                      sub_counts[0]))
    else:
        ok_parse = True
        msg = ("file present with the required single-column header; all "
               "count tokens are plain decimal integers")
        try:
            normalize_counts(sub_counts[1])
        except ValueError as e:
            ok_parse = False
            msg = str(e)
        add("motifs_per_peak_structure", ok_parse, msg)

    # ---------------- Check 3: counts values (positional) ----------------
    sub_cvals = None
    cvals_err = None
    if sub_counts is not None:
        try:
            sub_cvals = normalize_counts(sub_counts[1])
        except ValueError as e:
            cvals_err = str(e)
    if ref_counts_err is not None:
        add("motifs_per_peak_counts", False, ref_counts_err)
    elif sub_counts_err is not None:
        add("motifs_per_peak_counts", False,
            "counts file unusable: %s" % sub_counts_err)
    elif cvals_err is not None:
        add("motifs_per_peak_counts", False, cvals_err)
    elif sub_cvals == ref_counts:
        add("motifs_per_peak_counts", True,
            "motif counts per peak record match the reference exactly, "
            "position by position")
    else:
        n_len = abs(len(sub_cvals) - len(ref_counts))
        n_mis = 0
        if not n_len:
            n_mis = sum(1 for a, b in zip(sub_cvals, ref_counts) if a != b)
        detail = []
        if n_len:
            detail.append("row count differs from the reference by %d"
                          % n_len)
        if n_mis:
            detail.append("%d positions with a different count value" % n_mis)
        if not detail:
            detail.append("sequences differ")
        add("motifs_per_peak_counts", False,
            "counts do not match the reference sequence: "
            + "; ".join(detail))

    # ---------------- Check 4 & 5: peaks table content ----------------
    sub_rows = None
    sub_rows_err = None
    if sub_table is not None:
        try:
            sub_rows = [normalize_table_row(r) for r in sub_table[1]]
        except ValueError as e:
            sub_rows_err = str(e)

    if ref_rows_err is not None:
        add("peaks_blacklist_fragments", False, ref_rows_err)
        add("peaks_motif_assignment", False, ref_rows_err)
    elif sub_table_err is not None:
        add("peaks_blacklist_fragments", False,
            "peak table unusable: %s" % sub_table_err)
        add("peaks_motif_assignment", False,
            "peak table unusable: %s" % sub_table_err)
    elif sub_rows_err is not None:
        add("peaks_blacklist_fragments", False,
            "unparseable or invalid row content: %s" % sub_rows_err)
        add("peaks_motif_assignment", False,
            "unparseable or invalid row content: %s" % sub_rows_err)
    else:
        # 4: fragment multiset (chrom, start, end) — blacklist filtering
        ref_frag = Counter((r[0], r[1], r[2]) for r in ref_rows)
        sub_frag = Counter((r[0], r[1], r[2]) for r in sub_rows)
        missing, extra = multiset_diff(ref_frag, sub_frag)
        if not missing and not extra:
            add("peaks_blacklist_fragments", True,
                "surviving fragment intervals (chrom, start, end) match the "
                "reference multiset with multiplicity")
        else:
            add("peaks_blacklist_fragments", False,
                "fragment intervals differ from the reference: %d "
                "reference fragments missing, %d extra fragments submitted"
                % (sum(missing.values()), sum(extra.values())))

        # 5: full rows — fc and strongest-motif assignment on fragments
        ref_full = Counter(ref_rows)
        sub_full = Counter(sub_rows)
        missing, extra = multiset_diff(ref_full, sub_full)
        if not missing and not extra:
            add("peaks_motif_assignment", True,
                "all rows match the reference multiset: peak fc, assigned "
                "motif coordinates, pval_2 and strand_2 agree exactly")
        else:
            add("peaks_motif_assignment", False,
                "rows differ from the reference: %d reference rows missing, "
                "%d submitted rows not present in the reference (with "
                "multiplicity)"
                % (sum(missing.values()), sum(extra.values())))

    report = {
        "passed": all(c["passed"] for c in out),
        "checks": out,
    }
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

