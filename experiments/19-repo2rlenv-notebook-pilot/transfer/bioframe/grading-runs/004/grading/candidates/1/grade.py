#!/usr/bin/env python3
"""grade.py -- content grader for the CTCF strongest-motif peak table.

Grades the single declared endpoint file ``ctcf_peaks_maxmotif_clean.csv``
against its reference copy.  The enforced rules are exactly the published
acceptance rules:

  csv_format (structural)
      the file exists and is readable, decodes as UTF-8 (a leading byte order
      mark is ignored), parses as comma-separated text, has exactly one header
      line whose nine column names and their order are exactly the required
      ones, holds at least one data row, and every data row carries exactly
      nine fields; empty lines are ignored;
  value_domains (structural)
      chrom and motif_chrom are non-empty names with no surrounding
      whitespace, start/end and motif_start/motif_end denote non-negative
      integers below 2**62 with start < end and motif_start < motif_end,
      fc and motif_pval are plain finite decimal numbers, motif_strand is +
      or -, and the five motif fields are blank together or present together;
  peak_rows_match (scientific)
      the multiset of (chrom, start, end, fc) equals the reference multiset,
      so the retained peak sub-intervals, their multiplicity and their fold
      change all agree;
  motif_annotation_match (scientific)
      for every reported peak sub-interval the multiset of motif annotations
      (motif_chrom, motif_start, motif_end, motif_pval, motif_strand) equals
      the reference, blank annotations included;
  full_table_match (scientific)
      the multiset of complete rows equals the reference multiset, so fold
      change and motif annotation are paired correctly inside each row.

Every field is compared by the value its text denotes: chromosomes and
strands as exact strings, coordinates as integers, and fc / motif_pval as
exact decimal numbers with no tolerance (450, 450.0 and 4.5e2 are equal; a
text denoting a different number is not).  Rows are compared as multisets,
so row order is free and coverage, multiplicity and duplicates are all
enforced.  Non-finite or malformed values are rejected, never ignored.

The grader reads only the two CSV files, never executes submission code,
modifies nothing and writes only the requested report file.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

OUTPUT_NAME = "ctcf_peaks_maxmotif_clean.csv"
REQUIRED_HEADER = [
    "chrom",
    "start",
    "end",
    "fc",
    "motif_chrom",
    "motif_start",
    "motif_end",
    "motif_pval",
    "motif_strand",
]
MOTIF_COLUMNS = ("motif_chrom", "motif_start", "motif_end", "motif_pval",
                 "motif_strand")
N_FIELDS = len(REQUIRED_HEADER)
MAX_FILE_BYTES = 64 << 20
COORD_LIMIT = Decimal(1 << 62)
MAX_EXAMPLES = 3
STRANDS = ("+", "-")

NUMBER_RE = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")

CHECK_IDS = (
    "csv_format",
    "value_domains",
    "peak_rows_match",
    "motif_annotation_match",
    "full_table_match",
)
LATER_CHECKS_AT = 2  # csv_format and value_domains come first


class Bad(Exception):
    """One invalid row; collected and reported, never propagated."""


# --------------------------------------------------------------------------- #
# reading and validating
# --------------------------------------------------------------------------- #
def read_table(path, label):
    """Return (data_rows, errors). data_rows is None when the file is unusable."""
    if not os.path.exists(path):
        return None, ["the required file %s is missing from the %s directory"
                      % (OUTPUT_NAME, label)]
    if not os.path.isfile(path):
        return None, ["%s in the %s directory is not a regular file"
                      % (OUTPUT_NAME, label)]
    size = os.path.getsize(path)
    if size == 0:
        return None, ["%s in the %s directory is empty, so it has no header line"
                      % (OUTPUT_NAME, label)]
    if size > MAX_FILE_BYTES:
        return None, ["%s in the %s directory is %d bytes long, above the %d "
                      "byte reading limit" % (OUTPUT_NAME, label, size,
                                              MAX_FILE_BYTES)]
    with open(path, "rb") as handle:
        raw = handle.read()
    if raw[:3] == b"\xef\xbb\xbf":  # a byte order mark is an encoding marker
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return None, ["%s in the %s directory is not valid UTF-8 (%s at byte %d)"
                      % (OUTPUT_NAME, label, error.reason, error.start)]
    if "\x00" in text:
        return None, ["%s in the %s directory contains a NUL character"
                      % (OUTPUT_NAME, label)]
    try:
        csv.field_size_limit(min(MAX_FILE_BYTES, 2 ** 31 - 1))
    except (OverflowError, ValueError):  # pragma: no cover
        pass
    try:
        rows = [row for row in
                csv.reader(io.StringIO(text, newline=""), strict=True)
                if row]  # ignore empty lines
    except csv.Error as error:
        return None, ["%s in the %s directory is not parseable as "
                      "comma-separated text (%s)" % (OUTPUT_NAME, label, error)]
    if not rows:
        return None, ["%s in the %s directory contains no header line"
                      % (OUTPUT_NAME, label)]
    header, data = rows[0], rows[1:]
    if header != REQUIRED_HEADER:
        return None, ["the header line of %s in the %s directory must be exactly "
                      "%s, but it reads %s"
                      % (OUTPUT_NAME, label, ",".join(REQUIRED_HEADER),
                         ",".join(header))]
    if not data:
        return None, ["%s in the %s directory has a header line but no data rows"
                      % (OUTPUT_NAME, label)]
    bad = [row for row in data if len(row) != N_FIELDS]
    if bad:
        return None, ["%d of the %d data rows of %s in the %s directory do not "
                      "have exactly %d comma-separated fields; the first such "
                      "row is data row %d of the file and holds %d field(s)"
                      % (len(bad), len(data), OUTPUT_NAME, label, N_FIELDS,
                         data.index(bad[0]) + 1, len(bad[0]))]
    return data, []


def parse_number(text):
    """Exact value of a plain finite decimal literal, or raise Bad."""
    if not NUMBER_RE.match(text):
        raise Bad("%r is not a plain decimal number; NaN, Inf, empty fields and "
                  "values with surrounding whitespace are not accepted" % text)
    try:
        value = Decimal(text)
    except InvalidOperation:  # pragma: no cover - the regex admits Decimals
        raise Bad("%r is not a decimal number" % text)
    if not value.is_finite():  # pragma: no cover - regex matches are finite
        raise Bad("%r is not a finite number" % text)
    return value


def parse_coord(text, column):
    """Non-negative integer value, or raise Bad."""
    value = parse_number(text)
    if value != value.to_integral_value():
        raise Bad("%s %r does not denote an integer" % (column, text))
    if not -COORD_LIMIT < value < COORD_LIMIT:
        raise Bad("%s %r is outside the permitted coordinate range [0, %s)"
                  % (column, text, COORD_LIMIT))
    if value < 0:
        raise Bad("%s %r is negative" % (column, text))
    return int(value)


def canonical_rows(data):
    """Validate data rows; return (rows, errors, n_bad_rows)."""
    rows = []
    errors = []
    n_bad = 0
    for position, row in enumerate(data, start=1):
        try:
            chrom = row[0]
            if chrom == "":
                raise Bad("chrom is empty")
            if chrom != chrom.strip():
                raise Bad("chrom %r carries leading or trailing whitespace" % chrom)
            start = parse_coord(row[1], "start")
            end = parse_coord(row[2], "end")
            if start >= end:
                raise Bad("the peak interval has start %d not smaller than end %d"
                          % (start, end))
            fc = parse_number(row[3])
            blanks = [row[4 + i] == "" for i in range(5)]
            if all(blanks):
                motif = (None, None, None, None, None)
            elif any(blanks):
                empty = [MOTIF_COLUMNS[i] for i in range(5) if blanks[i]]
                filled = [MOTIF_COLUMNS[i] for i in range(5) if not blanks[i]]
                raise Bad("the five motif fields must be blank together, for a "
                          "peak without an assigned motif, or present together; "
                          "blank here: %s; present here: %s"
                          % (", ".join(empty), ", ".join(filled)))
            else:
                motif_chrom = row[4]
                if motif_chrom != motif_chrom.strip():
                    raise Bad("motif_chrom %r carries leading or trailing "
                              "whitespace" % motif_chrom)
                motif_start = parse_coord(row[5], "motif_start")
                motif_end = parse_coord(row[6], "motif_end")
                if motif_start >= motif_end:
                    raise Bad("the motif interval has motif_start %d not smaller "
                              "than motif_end %d" % (motif_start, motif_end))
                motif_pval = parse_number(row[7])
                if row[8] not in STRANDS:
                    raise Bad("motif_strand must be + or -, but it is %r" % row[8])
                motif = (motif_chrom, motif_start, motif_end, motif_pval, row[8])
            rows.append((chrom, start, end, fc) + motif)
        except Bad as error:
            n_bad += 1
            if len(errors) < MAX_EXAMPLES:
                errors.append("data row %d: %s" % (position, error))
    if n_bad > MAX_EXAMPLES:
        errors.append("and %d further data rows with invalid values"
                      % (n_bad - MAX_EXAMPLES))
    return rows, errors, n_bad


# --------------------------------------------------------------------------- #
# message helpers
# --------------------------------------------------------------------------- #
def fmt_cell(value):
    """Short printable form of a cell; never expands extreme exponents."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        # a plain expansion would be enormous for values like 1e999999999,
        # so extremely large or tiny values stay in exponent notation
        if abs(value.adjusted()) > 40 or len(value.as_tuple().digits) > 40:
            return str(value)
        return format(value, "f")
    return str(value)


def fmt_row(row):
    return "(" + ", ".join(fmt_cell(value) for value in row) + ")"


def counts_phrase(missing, extra):
    return ("%d reference row(s) have no counterpart in the submission and %d "
            "submission row(s) have no counterpart in the reference"
            % (sum(missing.values()), sum(extra.values())))


# --------------------------------------------------------------------------- #
# the three content comparisons
# --------------------------------------------------------------------------- #
def compare_peaks(ref_rows, sub_rows):
    """Retained peak sub-intervals with their fold change, as a multiset."""
    ref_map = Counter(row[:4] for row in ref_rows)
    sub_map = Counter(row[:4] for row in sub_rows)
    missing = ref_map - sub_map
    extra = sub_map - ref_map
    parts = ["the submission holds %d data rows" % len(sub_rows)]
    if not missing and not extra:
        parts.append("the multiset of retained peak sub-intervals (chrom, "
                     "start, end) together with their fold change fc is "
                     "identical to the reference: every retained sub-interval, "
                     "its fold change and the number of times it is reported "
                     "agree, so peak selection, blacklist trimming and the fold "
                     "change of every distinct peak interval are correct")
        return True, "; ".join(parts)
    parts.append(counts_phrase(missing, extra))
    sub_intervals = Counter(row[:3] for row in sub_rows)
    shown = 0
    for row, count in list(extra.items())[: MAX_EXAMPLES]:
        parts.append("submission row(s) not present in the reference%s: %s"
                     % ("" if count == 1 else " (%d times)" % count, fmt_row(row)))
        shown += 1
    n_changed = sum(1 for row in missing
                    if sub_intervals.get(row[:3]))
    if n_changed:
        parts.append("%d of the missing reference rows belong to peak "
                     "sub-intervals that the submission reports with a "
                     "different fold change or coverage" % n_changed)
    if sum(missing.values()) > n_changed:
        parts.append("%d of the missing reference rows have no submission row "
                     "for their peak sub-interval at all"
                     % (sum(missing.values()) - n_changed))
    return False, "; ".join(parts)


def compare_motifs(ref_rows, sub_rows):
    """Motif annotation per reported peak sub-interval, blanks included."""
    ref_by_key = defaultdict(Counter)
    for row in ref_rows:
        ref_by_key[row[:3]][row[4:]] += 1
    sub_by_key = defaultdict(Counter)
    for row in sub_rows:
        sub_by_key[row[:3]][row[4:]] += 1
    ref_keys, sub_keys = set(ref_by_key), set(sub_by_key)
    differing = sorted(key for key in (ref_keys & sub_keys)
                       if ref_by_key[key] != sub_by_key[key])
    missing_keys = ref_keys - sub_keys
    extra_keys = sub_keys - ref_keys
    parts = ["the submission holds %d data rows" % len(sub_rows)]
    if not differing and not missing_keys and not extra_keys:
        blanks = sum(1 for row in sub_rows if row[4] is None)
        parts.append("every reported peak sub-interval carries exactly the "
                     "reference motif annotation (motif_chrom, motif_start, "
                     "motif_end, motif_pval, motif_strand), and %d row(s) keep "
                     "all five motif fields blank exactly where the reference "
                     "has no assigned motif" % blanks)
        return True, "; ".join(parts)
    if differing:
        parts.append("%d peak sub-interval(s) reported by the submission carry a "
                     "motif annotation that differs from the reference"
                     % len(differing))
        for key in differing[: MAX_EXAMPLES]:
            only_sub = sub_by_key[key] - ref_by_key[key]
            if only_sub:
                row = next(iter(only_sub))
                parts.append("a reported peak sub-interval carries the motif "
                             "annotation %s, which the reference does not report "
                             "for that peak sub-interval" % fmt_row(row))
            else:
                parts.append("a reported peak sub-interval repeats a motif "
                             "annotation more often than the reference does")
    if missing_keys:
        parts.append("the submission is missing motif annotations for %d peak "
                     "sub-interval(s) retained by the reference"
                     % len(missing_keys))
    if extra_keys:
        parts.append("%d peak sub-interval(s) of the submission are not retained "
                     "by the reference" % len(extra_keys))
    parts.append("peak sub-intervals that are missing or added are also reported "
                 "by the peak comparison")
    return False, "; ".join(parts)


def compare_full(ref_rows, sub_rows):
    """Complete rows: peak coordinates, fold change and motif together."""
    ref_map = Counter(ref_rows)
    sub_map = Counter(sub_rows)
    missing = ref_map - sub_map
    extra = sub_map - ref_map
    parts = ["the submission holds %d data rows" % len(sub_rows)]
    if not missing and not extra:
        parts.append("the submission table equals the reference table as a "
                     "multiset of complete rows: apart from row order, which is "
                     "free, no row is missing, added or different, and rows that "
                     "appear more than once appear the same number of times")
        return True, "; ".join(parts)
    parts.append(counts_phrase(missing, extra))
    shown = 0
    for row, count in list(extra.items())[: MAX_EXAMPLES]:
        parts.append("submission row(s) not present in the reference%s: %s"
                     % ("" if count == 1 else " (%d times)" % count, fmt_row(row)))
        shown += 1
    if sum(missing.values()) > shown:
        parts.append("%d further reference row(s) have no submission row with "
                     "the same fold change and motif annotation"
                     % (sum(missing.values())))
    return False, "; ".join(parts)


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def evaluate(reference_dir, submission_dir):
    results = {name: [False, "not evaluated"] for name in CHECK_IDS}

    def fail_all(message):
        for name in CHECK_IDS:
            results[name] = [False, message]

    ref_data, ref_errors = read_table(
        os.path.join(reference_dir, OUTPUT_NAME), "reference")
    if ref_errors:
        fail_all("internal grading problem: the reference copy of %s does not "
                 "meet the published rules (%s), so the submission was not "
                 "evaluated" % (OUTPUT_NAME, "; ".join(ref_errors)))
        return results
    ref_rows, ref_bad_messages, ref_bad = canonical_rows(ref_data)
    if ref_bad:
        fail_all("internal grading problem: %d row(s) of the reference copy of "
                 "%s violate the published value rules (%s), so the submission "
                 "was not evaluated"
                 % (ref_bad, OUTPUT_NAME, "; ".join(ref_bad_messages)))
        return results

    sub_data, sub_errors = read_table(
        os.path.join(submission_dir, OUTPUT_NAME), "submission")
    if sub_errors:
        results["csv_format"] = [False, "; ".join(sub_errors)]
        for name in CHECK_IDS[LATER_CHECKS_AT:]:
            results[name] = [False, "not evaluated: %s does not meet the "
                                    "published file and column layout rules, "
                                    "see csv_format" % OUTPUT_NAME]
        return results
    results["csv_format"] = [
        True,
        "%s was found in the submission directory and read as UTF-8 text: one "
        "header line whose nine column names and their order match the required "
        "header exactly, followed by %d data rows, each with exactly nine "
        "comma-separated fields; empty lines, a byte order mark and quoting of "
        "fields are ignored" % (OUTPUT_NAME, len(sub_data))]

    sub_rows, bad_messages, n_bad = canonical_rows(sub_data)
    if n_bad:
        results["value_domains"] = [
            False, "%d data row(s) violate the published value rules: %s"
            % (n_bad, "; ".join(bad_messages))]
        for name in CHECK_IDS[LATER_CHECKS_AT:]:
            results[name] = [False, "not evaluated: the submission contains data "
                                    "rows with invalid values, see value_domains"]
        return results
    results["value_domains"] = [
        True,
        "all %d data rows satisfy the published value rules: chrom and "
        "motif_chrom are non-empty names without surrounding whitespace, "
        "start/end and motif_start/motif_end denote non-negative integers with "
        "start < end and motif_start < motif_end, fc and motif_pval are finite "
        "decimal numbers, motif_strand is + or -, and the five motif fields are "
        "blank together or present together" % len(sub_rows)]

    ok, message = compare_peaks(ref_rows, sub_rows)
    results["peak_rows_match"] = [ok, message]
    ok, message = compare_motifs(ref_rows, sub_rows)
    results["motif_annotation_match"] = [ok, message]
    ok, message = compare_full(ref_rows, sub_rows)
    results["full_table_match"] = [ok, message]
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Grade the strongest-motif CTCF peak table.")
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    try:
        results = evaluate(args.reference_dir, args.submission_dir)
    except Exception as error:  # a grader defect must not become a crash
        results = {name: [False, "internal grading error: %s: %s"
                          % (type(error).__name__, error)]
                   for name in CHECK_IDS}

    checks = [{"id": name, "passed": bool(results[name][0]),
               "message": str(results[name][1])} for name in CHECK_IDS]
    report = {"passed": all(entry["passed"] for entry in checks), "checks": checks}
    report_path = os.path.abspath(args.report)
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

