#!/usr/bin/env python3
"""grade.py -- acceptance grader for the CTCF motif-assignment task.

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH

The grader parses the single declared output file
(ctcf_peaks_maxmotif_clean.csv) from both directories and compares the parsed
scientific content. It never executes or imports submission code, never writes
into the reference or submission directories, always writes a JSON report to
--report, and always exits with status 0.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter

ENDPOINT_NAME = "ctcf_peaks_maxmotif_clean.csv"
REQUIRED_HEADER = (
    "chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand"
)
N_FIELDS = 9
# A submission may deliver the file directly in the output directory or inside
# a subdirectory named exactly "outputs" (or "output") that holds nothing else.
ALLOWED_SUBDIRS = ("outputs", "output")

CHECK_IDS = (
    "output_file_schema",
    "field_value_validity",
    "peak_interval_rows",
    "fold_change_values",
    "motif_assignment",
)

INT_RE = re.compile(r"[0-9]+")
NUM_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
NAME_RE = re.compile(r"[^\s,\"]+")


# ---------------------------------------------------------------------------
# locating and reading the output file
# ---------------------------------------------------------------------------
def find_endpoint(root):
    """Locate the declared output file inside `root`.

    Returns (path, error). The accepted layouts are <root>/<name> and
    <root>/<outputs|output>/<name>, in both cases as the only entry of the
    directory that holds it.
    """
    if not os.path.isdir(root):
        return None, "%s is not a directory" % root
    direct = os.path.join(root, ENDPOINT_NAME)
    if os.path.isfile(direct):
        siblings = sorted(e for e in os.listdir(root) if e != ENDPOINT_NAME)
        if siblings:
            return None, (
                "the output directory contains unexpected additional entr%s: %s "
                "(the required output is a single file with no additional files)"
                % ("y" if len(siblings) == 1 else "ies", ", ".join(siblings[:5]))
            )
        return direct, None
    for sub in ALLOWED_SUBDIRS:
        candidate = os.path.join(root, sub, ENDPOINT_NAME)
        if os.path.isfile(candidate):
            inner = sorted(
                e for e in os.listdir(os.path.join(root, sub)) if e != ENDPOINT_NAME
            )
            if inner:
                return None, "unexpected file%s inside the %s directory: %s" % (
                    "s" if len(inner) > 1 else "",
                    sub,
                    ", ".join(inner[:5]),
                )
            outer = sorted(e for e in os.listdir(root) if e != sub)
            if outer:
                return None, (
                    "the output directory contains unexpected additional entr%s: %s"
                    % ("y" if len(outer) == 1 else "ies", ", ".join(outer[:5]))
                )
            return candidate, None
    return None, "required output file '%s' was not found" % ENDPOINT_NAME


def read_lines(path):
    """Return the physical non-empty text lines of the output file."""
    with open(path, "rb") as handle:
        raw = handle.read()
    if not raw:
        raise ValueError("the output file is empty")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("the output file is not valid UTF-8")
    if text.startswith("﻿"):
        raise ValueError("the output file starts with a UTF-8 byte-order mark")
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    if not text:
        raise ValueError("the output file is empty")
    return text.split("\n")


def parse_table(root):
    """Load the endpoint table from `root`.

    Returns (rows, error); `rows` is a list of 9-field string tuples, or None
    when the file is missing or malformed.
    """
    path, error = find_endpoint(root)
    if error:
        return None, error
    try:
        lines = read_lines(path)
    except ValueError as exc:
        return None, str(exc)
    except OSError as exc:
        return None, "the output file could not be read: %s" % exc

    for index, line in enumerate(lines):
        if line.strip() == "":
            return None, "line %d of the output file is blank" % (index + 1)

    try:
        header = next(csv.reader([lines[0]], strict=True))
    except csv.Error as exc:
        return None, "the header line could not be parsed as CSV: %s" % exc
    if ",".join(header) != REQUIRED_HEADER:
        return None, "header line is %r; expected exactly %r" % (
            lines[0][:160],
            REQUIRED_HEADER,
        )

    rows = []
    for number, line in enumerate(lines[1:], start=2):
        try:
            fields = next(csv.reader([line], strict=True))
        except csv.Error as exc:
            return None, "line %d could not be parsed as CSV: %s" % (number, exc)
        if len(fields) != N_FIELDS:
            return None, (
                "line %d has %d comma-separated fields; expected exactly %d "
                "columns in the declared order and no index column"
                % (number, len(fields), N_FIELDS)
            )
        rows.append(tuple(fields))
    if not rows:
        return None, "the output file contains a header line but no data rows"
    return rows, None


# ---------------------------------------------------------------------------
# field-level validation
# ---------------------------------------------------------------------------
def build_records(rows):
    """Validate every row and convert it into a comparable record.

    Returns (records, problems). `problems` is empty when every row is valid;
    `records` is a list of (chrom, start, end, fc, motif) tuples where fc is a
    float and motif is None (all motif fields blank) or
    (chrom, start, end, motif_pval, strand).
    """
    problems = Counter()
    records = []
    for fields in rows:
        (
            chrom,
            start_s,
            end_s,
            fc_s,
            m_chrom,
            m_start_s,
            m_end_s,
            m_pval_s,
            m_strand,
        ) = fields
        valid = True

        if not NAME_RE.fullmatch(chrom):
            problems["chrom is empty or contains whitespace or quote characters"] += 1
            valid = False

        if not INT_RE.fullmatch(start_s) or not INT_RE.fullmatch(end_s):
            problems["start or end is not a plain non-negative integer"] += 1
            valid = False
        elif int(start_s) >= int(end_s):
            problems["retained interval is empty (start >= end)"] += 1
            valid = False

        if not NUM_RE.fullmatch(fc_s):
            problems["fc is not a decimal number"] += 1
            valid = False
        elif not math.isfinite(float(fc_s)):
            problems["fc is not finite (NaN or infinity)"] += 1
            valid = False

        motif_block = (m_chrom, m_start_s, m_end_s, m_pval_s, m_strand)
        blanks = [value == "" for value in motif_block]
        motif = None
        if all(blanks):
            motif = None
        elif any(blanks):
            problems["the five motif fields are only partially blank"] += 1
            valid = False
        else:
            motif_ok = True
            if not NAME_RE.fullmatch(m_chrom):
                problems["motif_chrom is empty or contains whitespace"] += 1
                motif_ok = False
            if not INT_RE.fullmatch(m_start_s) or not INT_RE.fullmatch(m_end_s):
                problems[
                    "motif_start or motif_end is not a plain non-negative integer"
                ] += 1
                motif_ok = False
            elif int(m_start_s) >= int(m_end_s):
                problems["motif interval is empty (motif_start >= motif_end)"] += 1
                motif_ok = False
            if not NUM_RE.fullmatch(m_pval_s):
                problems["motif_pval is not a decimal number"] += 1
                motif_ok = False
            elif not math.isfinite(float(m_pval_s)):
                problems["motif_pval is not finite (NaN or infinity)"] += 1
                motif_ok = False
            if m_strand not in ("+", "-"):
                problems["motif_strand is not exactly '+' or '-'"] += 1
                motif_ok = False
            if m_chrom != chrom:
                problems["motif_chrom differs from the peak's chrom"] += 1
                motif_ok = False
            if motif_ok:
                motif = (
                    m_chrom,
                    int(m_start_s),
                    int(m_end_s),
                    float(m_pval_s),
                    m_strand,
                )
            else:
                valid = False

        if valid:
            records.append((chrom, int(start_s), int(end_s), float(fc_s), motif))
    return records, problems


def describe(problems, limit=4):
    items = sorted(problems.items(), key=lambda kv: (-kv[1], kv[0]))
    parts = ["%d row(s): %s" % (count, text) for text, count in items[:limit]]
    if len(items) > limit:
        parts.append("and %d further issue type(s)" % (len(items) - limit))
    return "; ".join(parts)


def peak_key(record):
    return (record[0], record[1], record[2])


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def evaluate(reference_dir, submission_dir):
    results = {check_id: None for check_id in CHECK_IDS}

    sub_rows, sub_error = parse_table(submission_dir)
    sub_records = None
    sub_problems = Counter()
    if sub_error is None:
        sub_records, sub_problems = build_records(sub_rows)
        if sub_problems:
            sub_records = None

    ref_rows, ref_error = parse_table(reference_dir)
    ref_records = None
    if ref_error is None:
        ref_records, ref_problems = build_records(ref_rows)
        if ref_problems:
            ref_error = "the reference table contains invalid values"
            ref_records = None

    if sub_error is not None:
        blocked = sub_error
    elif sub_records is None:
        blocked = "the output table contains invalid values: %s" % describe(
            sub_problems
        )
    elif ref_records is None:
        blocked = ref_error or "the reference table could not be loaded"
    else:
        blocked = None

    # ---- check 1: one output file, declared schema -------------------------
    if sub_error is not None:
        results["output_file_schema"] = (False, sub_error)
    elif sub_records is None:
        results["output_file_schema"] = (
            False,
            "a single output file '%s' was delivered, but its rows are not "
            "valid: %s" % (ENDPOINT_NAME, describe(sub_problems)),
        )
    else:
        results["output_file_schema"] = (
            True,
            "a single output file '%s' with the required header '%s' and %d "
            "comma-separated data rows" % (ENDPOINT_NAME, REQUIRED_HEADER, len(sub_rows)),
        )

    # ---- check 2: field value validity -------------------------------------
    if sub_error is not None:
        results["field_value_validity"] = (False, "not evaluated: %s" % sub_error)
    elif sub_records is None:
        results["field_value_validity"] = (
            False,
            "invalid values in the output table -- %s" % describe(sub_problems),
        )
    else:
        results["field_value_validity"] = (
            True,
            "all %d data rows carry a non-empty chrom, a non-negative integer "
            "interval with start < end, a finite decimal fc, and a motif block "
            "that is blank in all five fields or complete with a finite decimal "
            "motif_pval and strand '+' or '-' on the peak's own chromosome"
            % len(sub_records),
        )

    # ---- checks 3-5: scientific content ------------------------------------
    if blocked is not None:
        for check_id in CHECK_IDS[2:]:
            results[check_id] = (False, "not evaluated: %s" % blocked)
    else:
        sub_keys = Counter(peak_key(r) for r in sub_records)
        ref_keys = Counter(peak_key(r) for r in ref_records)
        missing = sum((ref_keys - sub_keys).values())
        extra = sum((sub_keys - ref_keys).values())
        if missing or extra:
            results["peak_interval_rows"] = (
                False,
                "the rows over (chrom, start, end) do not match the reference: "
                "%d row(s) missing, %d unexpected or duplicated row(s) "
                "(submission has %d rows, reference has %d)"
                % (missing, extra, len(sub_records), len(ref_records)),
            )
        else:
            duplicates = sum(1 for count in sub_keys.values() if count > 1)
            results["peak_interval_rows"] = (
                True,
                "the multiset of retained (chrom, start, end) intervals matches "
                "the reference exactly: %d rows, %d distinct intervals, %d "
                "interval(s) reported in more than one row (row order is not "
                "evaluated)"
                % (len(sub_records), len(sub_keys), duplicates),
            )

        sub_fc = Counter((peak_key(r), r[3]) for r in sub_records)
        ref_fc = Counter((peak_key(r), r[3]) for r in ref_records)
        missing = sum((ref_fc - sub_fc).values())
        extra = sum((sub_fc - ref_fc).values())
        if missing or extra:
            results["fold_change_values"] = (
                False,
                "%d row(s) carry a fold-change value that differs from the "
                "reference value for their retained interval (or belong to a "
                "missing/extra row); fc is compared as the exact parsed number, "
                "so only its decimal rendering may differ" % (missing + extra),
            )
        else:
            results["fold_change_values"] = (
                True,
                "every one of the %d rows carries the reference fold-change "
                "value for its retained interval, compared as the exact parsed "
                "number (decimal rendering alone is not evaluated)"
                % len(sub_records),
            )

        sub_mo = Counter((peak_key(r), r[4]) for r in sub_records)
        ref_mo = Counter((peak_key(r), r[4]) for r in ref_records)
        missing = sum((ref_mo - sub_mo).values())
        extra = sum((sub_mo - ref_mo).values())
        if missing or extra:
            results["motif_assignment"] = (
                False,
                "%d row(s) report a motif block (present versus blank, "
                "coordinates, score or strand) that differs from the reference "
                "for their retained interval (or belong to a missing/extra "
                "row); motif_pval is compared as the exact parsed number"
                % (missing + extra),
            )
        else:
            blank = sum(1 for r in sub_records if r[4] is None)
            results["motif_assignment"] = (
                True,
                "every one of the %d rows carries the reference motif assignment "
                "(motif_chrom, motif_start, motif_end, exact parsed motif_pval, "
                "motif_strand) for its retained interval; %d row(s) report blank "
                "motif fields (peak sub-intervals with no assigned motif)"
                % (len(sub_records), blank),
            )

    return [
        {"id": check_id, "passed": bool(results[check_id][0]),
         "message": str(results[check_id][1])}
        for check_id in CHECK_IDS
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="acceptance grader for the CTCF motif-assignment task"
    )
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    checks = evaluate(args.reference_dir, args.submission_dir)
    report = {"passed": all(c["passed"] for c in checks), "checks": checks}

    report_dir = os.path.dirname(os.path.abspath(args.report))
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

