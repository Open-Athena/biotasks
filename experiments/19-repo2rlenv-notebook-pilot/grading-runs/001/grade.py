#!/usr/bin/env python3
"""Acceptance grader for the scanpy ``Preprocessing and clustering`` endpoints.

Compares the parsed scientific content of three declared endpoint files
(``cell_clusters_umap.csv``, ``rank_genes_groups_leiden_res_0.50.csv`` and
``rank_genes_groups_params.json``) against a reference copy of the same files.

The grader reads values dynamically from the reference directory, never embeds
expected values, dimensions or cluster counts, never imports or executes
submission code, never writes to the reference or submission directories and
needs no network access.  It always writes a JSON report and exits 0, whether
the submission passes or fails.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import struct
import sys
from collections import defaultdict

# ---------------------------------------------------------------------------
# Declared artifacts (fixed by the task specification)
# ---------------------------------------------------------------------------

CELL_FILE = "cell_clusters_umap.csv"
DE_FILE = "rank_genes_groups_leiden_res_0.50.csv"
PARAMS_FILE = "rank_genes_groups_params.json"

CELL_COLUMNS = (
    "cell_id",
    "sample",
    "leiden",
    "leiden_res_0.02",
    "leiden_res_0.50",
    "leiden_res_2.00",
    "cell_type_lvl1",
    "umap_1",
    "umap_2",
)
CELL_TEXT_COLUMNS = (
    "cell_id",
    "sample",
    "leiden",
    "leiden_res_0.02",
    "leiden_res_0.50",
    "leiden_res_2.00",
    "cell_type_lvl1",
)
CELL_MANDATORY_TEXT_COLUMNS = (
    "cell_id",
    "sample",
    "leiden",
    "leiden_res_0.02",
    "leiden_res_0.50",
    "leiden_res_2.00",
)
CELL_NUMERIC_COLUMNS = ("umap_1", "umap_2")

DE_COLUMNS = ("group", "names", "scores", "pvals_adj", "pvals", "logfoldchanges")
DE_TEXT_COLUMNS = ("group", "names")
DE_NUMERIC_COLUMNS = ("scores", "pvals_adj", "pvals", "logfoldchanges")
DE_FLOAT32_COLUMNS = ("scores", "logfoldchanges")
DE_PVALUE_COLUMNS = ("pvals_adj", "pvals")

CLUSTER_COLUMN_FOR_DE = "leiden_res_0.50"

MAX_REPORTED = 5

# A strict decimal floating-point literal.  Anything else (empty string, "nan",
# "inf", "Infinity", "1_0", hexadecimal, ...) is a failed value rather than a
# coerced one.
NUMBER_PATTERN = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z"
)

# Bounds that keep a deliberately oversized submission from making the grader
# read unbounded data.  They never apply to the reference itself and are set far
# above anything a correct submission can contain (a correct submission has
# exactly the reference's number of rows, so these limits are only ever hit by
# submissions that already violate the published row-count rule).
ROWS_PER_LIMIT = 2
EXTRA_ROWS_ALLOWED = 1000
BYTES_PER_LIMIT = 4
MINIMUM_BYTE_LIMIT = 64 * 1024 * 1024


class CheckFailure(Exception):
    """A definite failure of one named check; the message becomes the report."""


def _file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# float32 helpers -- the reference stores these endpoint quantities as binary32
# ---------------------------------------------------------------------------


def to_float32(value):
    """Round a float to IEEE-754 binary32; ``None`` when it cannot be represented."""
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    except (OverflowError, struct.error):
        return None


def f32_equal(left, right):
    """True when both values round to the same IEEE-754 binary32 number."""
    a = to_float32(left)
    b = to_float32(right)
    if a is None or b is None:
        return False
    return a == b


# ---------------------------------------------------------------------------
# table loading
# ---------------------------------------------------------------------------


class Table:
    """A parsed CSV endpoint file with structured, bounded diagnostics."""

    def __init__(
        self,
        path,
        filename,
        columns,
        text_columns,
        mandatory_text_columns,
        numeric_columns,
        row_limit=None,
        byte_limit=None,
    ):
        self.path = path
        self.filename = filename
        self.columns_spec = list(columns)
        self.numeric_columns = tuple(numeric_columns)
        self.present = os.path.isfile(path)
        self.fatal = None
        self.problems = []
        self.truncated = False
        self.n = 0
        self.header = None
        self.columns = {}
        self.numeric = {}
        self.numeric_problems = {}
        if not self.present:
            self.fatal = "required file %s is missing" % filename
            return
        if byte_limit is not None and _file_size(path) > byte_limit:
            self.fatal = (
                "%s is implausibly large for this endpoint; a correct submission "
                "has exactly the reference's number of rows" % filename
            )
            return
        rows = []
        field_problems = []
        overflowed = False
        try:
            with open(path, "r", encoding="utf-8", newline="", errors="strict") as handle:
                reader = csv.reader(handle)
                header = None
                record_number = 0
                for record in reader:
                    if header is None:
                        header = record
                        continue
                    if row_limit is not None and record_number >= row_limit:
                        overflowed = True
                        break
                    record_number += 1
                    if len(record) != len(self.columns_spec):
                        field_problems.append(
                            "data row %d has %d fields, %d expected"
                            % (record_number, len(record), len(self.columns_spec))
                        )
                        continue
                    rows.append(record)
        except UnicodeDecodeError:
            self.fatal = "%s is not valid UTF-8 text" % filename
            return
        except csv.Error as error:
            self.fatal = "%s is not parseable as CSV (%s)" % (filename, error)
            return
        except OSError as error:
            self.fatal = "%s could not be read (%s)" % (filename, type(error).__name__)
            return
        if header is None:
            self.fatal = "%s is empty (no header row)" % filename
            return
        self.truncated = overflowed
        self.header = list(header)
        if self.header != self.columns_spec:
            self.fatal = (
                "%s must have exactly the header %s (found %s)"
                % (filename, ",".join(self.columns_spec), ",".join(self.header))
            )
            return
        self.n = len(rows)
        if field_problems:
            self.problems.append(
                "%d data rows have the wrong number of fields (first: %s)"
                % (len(field_problems), field_problems[0])
            )
        for index, name in enumerate(self.columns_spec):
            self.columns[name] = [row[index] for row in rows]
        for name in mandatory_text_columns:
            blanks = [
                data_row + 1
                for data_row, value in enumerate(self.columns[name])
                if value == ""
            ]
            if blanks:
                self.problems.append(
                    "column %r has %d empty values (first at data row %d); "
                    "identifiers and cluster assignments are mandatory"
                    % (name, len(blanks), blanks[0])
                )
        for name in numeric_columns:
            values = []
            problems = []
            for data_row, text in enumerate(self.columns[name]):
                if not NUMBER_PATTERN.match(text):
                    problems.append(
                        "data row %d: %r is not a decimal number" % (data_row + 1, text)
                    )
                    values.append(float("nan"))
                    continue
                value = float(text)
                if not math.isfinite(value):
                    problems.append(
                        "data row %d: %r is not a finite number" % (data_row + 1, text)
                    )
                values.append(value)
            self.numeric[name] = values
            self.numeric_problems[name] = problems

    def usable(self):
        """``None`` when the table can be compared, otherwise a failure message."""
        return self.fatal

    def duplicate_rows(self, columns):
        seen = set()
        duplicates = []
        keys = list(zip(*[self.columns[name] for name in columns]))
        for index, key in enumerate(keys):
            if key in seen:
                duplicates.append(index + 1)
            else:
                seen.add(key)
        return duplicates


def de_blocks(table):
    """Consecutive blocks of equal ``group`` values: [(label, start, end), ...]."""
    labels = table.columns["group"]
    blocks = []
    position = 0
    total = len(labels)
    while position < total:
        end = position
        while end + 1 < total and labels[end + 1] == labels[position]:
            end += 1
        blocks.append((labels[position], position, end + 1))
        position = end + 1
    return blocks


def aligned_blocks(reference, submission):
    """Yield ``(label, ref_start, ref_end, sub_start, sub_end)`` per group block."""
    ref_blocks = de_blocks(reference)
    sub_blocks = de_blocks(submission)
    ref_labels = [block[0] for block in ref_blocks]
    sub_labels = [block[0] for block in sub_blocks]
    if ref_labels != sub_labels:
        if sorted(ref_labels) != sorted(sub_labels):
            raise CheckFailure(
                "the DE group blocks do not match the reference: every reference "
                "group must appear exactly once as a consecutive block of rows"
            )
        raise CheckFailure(
            "the DE group blocks are not in the reference's stored group order"
        )
    for (label, ref_start, ref_end), (_, sub_start, sub_end) in zip(ref_blocks, sub_blocks):
        if ref_end - ref_start != sub_end - sub_start:
            raise CheckFailure(
                "DE group %r has %d rows; the reference stores %d rows for this "
                "group (one row per ranked gene)"
                % (label, sub_end - sub_start, ref_end - ref_start)
            )
        yield label, ref_start, ref_end, sub_start, sub_end


def tie_classes(table):
    """Map group label -> tie-key -> list of gene names.

    A tie key is ``(score as stored float32, pvals, pvals_adj)``: rows sharing a
    key are indistinguishable in the exported leaderboard statistics, so only
    their gene identities (and their per-gene log fold changes) carry content.
    """
    classes = defaultdict(lambda: defaultdict(list))
    scores = table.numeric["scores"]
    pvalues = table.numeric["pvals"]
    adjusted = table.numeric["pvals_adj"]
    names = table.columns["names"]
    for label, start, end in de_blocks(table):
        group_classes = classes[label]
        for index in range(start, end):
            group_classes[
                (to_float32(scores[index]), pvalues[index], adjusted[index])
            ].append(names[index])
    return classes


def logfold_maps(table):
    """Map group label -> tie-key -> {gene name: [float32(logfoldchange), ...]}."""
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    scores = table.numeric["scores"]
    pvalues = table.numeric["pvals"]
    adjusted = table.numeric["pvals_adj"]
    names = table.columns["names"]
    logfolds = table.numeric["logfoldchanges"]
    for label, start, end in de_blocks(table):
        group_classes = result[label]
        for index in range(start, end):
            group_classes[
                (to_float32(scores[index]), pvalues[index], adjusted[index])
            ][names[index]].append(to_float32(logfolds[index]))
    return result


def load_params(path, byte_limit=None):
    """Return ``(mapping, None)`` on success or ``(None, failure message)``."""
    if not os.path.isfile(path):
        return None, "required file %s is missing" % PARAMS_FILE
    if byte_limit is not None and _file_size(path) > byte_limit:
        return None, "%s is implausibly large for a recorded parameter mapping" % PARAMS_FILE
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            text = handle.read()
    except UnicodeDecodeError:
        return None, "%s is not valid UTF-8 text" % PARAMS_FILE
    except OSError as error:
        return None, "%s could not be read (%s)" % (PARAMS_FILE, type(error).__name__)

    def reject_constant(name):
        raise ValueError("%s is not an accepted JSON constant" % name)

    try:
        obj = json.loads(text, parse_constant=reject_constant)
    except ValueError as error:
        return None, "%s is not valid JSON (%s)" % (PARAMS_FILE, error)
    if not isinstance(obj, dict):
        return None, "%s must contain a single JSON object" % PARAMS_FILE
    for key, value in obj.items():
        if isinstance(value, (dict, list)):
            return None, "value of key %r is not a scalar" % key
    return obj, None


class Dataset:
    """Lazily parsed endpoint files of one directory.

    When ``reference`` is supplied, submission files are read only up to a
    generous multiple of the reference's own size, so that an oversized
    submission cannot make grading unbounded.  The bound never applies to the
    reference itself.
    """

    def __init__(self, root, reference=None):
        self.root = root
        self._reference = reference
        self._cell = None
        self._de = None
        self._params = None

    def _row_limit(self, filename):
        if self._reference is None:
            return None
        table = None
        if filename == CELL_FILE:
            table = self._reference.cell()
        elif filename == DE_FILE:
            table = self._reference.de()
        if table is None or table.fatal is not None:
            return None
        return ROWS_PER_LIMIT * table.n + EXTRA_ROWS_ALLOWED

    def _byte_limit(self, filename):
        if self._reference is None:
            return None
        size = _file_size(os.path.join(self._reference.root, filename))
        if size is None:
            return None
        return max(BYTES_PER_LIMIT * size, MINIMUM_BYTE_LIMIT)

    def cell(self):
        if self._cell is None:
            self._cell = Table(
                os.path.join(self.root, CELL_FILE),
                CELL_FILE,
                CELL_COLUMNS,
                CELL_TEXT_COLUMNS,
                CELL_MANDATORY_TEXT_COLUMNS,
                CELL_NUMERIC_COLUMNS,
                row_limit=self._row_limit(CELL_FILE),
                byte_limit=self._byte_limit(CELL_FILE),
            )
        return self._cell

    def de(self):
        if self._de is None:
            self._de = Table(
                os.path.join(self.root, DE_FILE),
                DE_FILE,
                DE_COLUMNS,
                DE_TEXT_COLUMNS,
                DE_TEXT_COLUMNS,
                DE_NUMERIC_COLUMNS,
                row_limit=self._row_limit(DE_FILE),
                byte_limit=self._byte_limit(DE_FILE),
            )
        return self._de

    def params(self):
        if self._params is None:
            self._params = load_params(
                os.path.join(self.root, PARAMS_FILE), self._byte_limit(PARAMS_FILE)
            )
        return self._params


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def require_table(table):
    message = table.fatal
    if message is not None:
        raise CheckFailure(message)
    if table.n == 0:
        raise CheckFailure("%s contains no data rows" % table.filename)
    if table.truncated:
        raise CheckFailure(
            "%s contains far more data rows than the reference endpoint; a "
            "correct submission has exactly the reference's number of rows"
            % table.filename
        )


def require_numeric(table, columns):
    for name in columns:
        problems = table.numeric_problems.get(name, [])
        if problems:
            raise CheckFailure(
                "column %r of %s has invalid numeric values: %s"
                % (name, table.filename, "; ".join(problems[:MAX_REPORTED]))
            )


def require_structure(table):
    require_table(table)
    if table.problems:
        raise CheckFailure("; ".join(table.problems[:MAX_REPORTED]))


def summarize(items, limit=MAX_REPORTED):
    shown = ", ".join(str(item) for item in items[:limit])
    if len(items) > limit:
        shown += " (+%d more)" % (len(items) - limit)
    return shown


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def check_cell_structure(ref, sub):
    table = sub.cell()
    require_structure(table)
    duplicates = table.duplicate_rows(["cell_id"])
    if duplicates:
        raise CheckFailure(
            "column 'cell_id' contains repeated values (data rows %s)"
            % summarize(duplicates)
        )
    require_numeric(table, CELL_NUMERIC_COLUMNS)
    return (
        "%s has the required header, field counts, unique non-empty identifiers "
        "and assignments, and finite numeric coordinates" % CELL_FILE
    )


def check_cell_row_identity(ref, sub):
    reference = ref.cell()
    submission = sub.cell()
    require_structure(reference)
    require_structure(submission)
    reference_ids = reference.columns["cell_id"]
    submission_ids = submission.columns["cell_id"]
    if len(submission_ids) != len(reference_ids):
        raise CheckFailure(
            "%s has %d data rows; the reference endpoint has %d rows (one row "
            "per retained cell)" % (CELL_FILE, len(submission_ids), len(reference_ids))
        )
    differing = [
        index + 1
        for index, (left, right) in enumerate(zip(submission_ids, reference_ids))
        if left != right
    ]
    if differing:
        raise CheckFailure(
            "the 'cell_id' sequence differs from the reference at %d rows (first "
            "at data row %d); rows must appear in the reference's stored order"
            % (len(differing), differing[0])
        )
    return "the 'cell_id' sequence matches the reference row by row"


def _cell_column_check(column, subject):
    def check(ref, sub):
        reference = ref.cell()
        submission = sub.cell()
        require_structure(reference)
        require_structure(submission)
        if submission.n != reference.n:
            raise CheckFailure(
                "%s has %d rows; the reference endpoint has %d rows"
                % (CELL_FILE, submission.n, reference.n)
            )
        sub_values = submission.columns[column]
        ref_values = reference.columns[column]
        differing = [
            index + 1
            for index, (left, right) in enumerate(zip(sub_values, ref_values))
            if left != right
        ]
        if differing:
            raise CheckFailure(
                "column %r differs from the reference at %d rows (first at data "
                "row %d) -- %s"
                % (column, len(differing), differing[0], subject)
            )
        return (
            "column %r matches the reference for every row (%s)" % (column, subject)
        )

    return check


def check_umap_embedding(ref, sub):
    reference = ref.cell()
    submission = sub.cell()
    require_structure(reference)
    require_structure(submission)
    require_numeric(reference, CELL_NUMERIC_COLUMNS)
    require_numeric(submission, CELL_NUMERIC_COLUMNS)
    if submission.n != reference.n:
        raise CheckFailure(
            "%s has %d rows; the reference endpoint has %d rows"
            % (CELL_FILE, submission.n, reference.n)
        )
    unrepresentable = []
    mismatches = []
    for column in CELL_NUMERIC_COLUMNS:
        sub_values = submission.numeric[column]
        ref_values = reference.numeric[column]
        for index, (left, right) in enumerate(zip(sub_values, ref_values)):
            if to_float32(left) is None:
                unrepresentable.append((column, index + 1))
            elif not f32_equal(left, right):
                mismatches.append((column, index + 1))
    if unrepresentable:
        raise CheckFailure(
            "columns %s contain values outside the float32 range of the stored "
            "endpoint (first: %s)"
            % ("/".join(CELL_NUMERIC_COLUMNS), summarize(unrepresentable))
        )
    if mismatches:
        raise CheckFailure(
            "UMAP coordinates differ from the reference at the stored float32 "
            "precision at %d positions (first: %s)"
            % (len(mismatches), summarize(mismatches))
        )
    return (
        "both UMAP coordinates agree with the reference at the stored float32 "
        "precision for every row"
    )


def check_de_structure(ref, sub):
    table = sub.de()
    require_structure(table)
    duplicates = table.duplicate_rows(list(DE_TEXT_COLUMNS))
    if duplicates:
        raise CheckFailure(
            "the (group, gene) pair repeats at %d data rows (first at data row %d)"
            % (len(duplicates), duplicates[0])
        )
    require_numeric(table, DE_NUMERIC_COLUMNS)
    return (
        "%s has the required header, field counts, unique (group, gene) pairs "
        "and finite numeric values" % DE_FILE
    )


def check_de_group_blocks(ref, sub):
    reference = ref.de()
    submission = sub.de()
    require_structure(reference)
    require_structure(submission)
    blocks = list(aligned_blocks(reference, submission))
    cell_table = sub.cell()
    if cell_table.fatal is not None:
        raise CheckFailure(
            "cannot verify the group label set against %s: %s"
            % (CELL_FILE, cell_table.fatal)
        )
    cluster_values = cell_table.columns.get(CLUSTER_COLUMN_FOR_DE)
    if cluster_values is None:
        raise CheckFailure(
            "cannot verify the group label set: %s has no column %r"
            % (CELL_FILE, CLUSTER_COLUMN_FOR_DE)
        )
    de_labels = set(submission.columns["group"])
    cell_labels = set(cluster_values)
    if de_labels != cell_labels:
        only_de = sorted(de_labels - cell_labels)
        only_cells = sorted(cell_labels - de_labels)
        detail = []
        if only_de:
            detail.append("%d labels appear only in %s" % (len(only_de), DE_FILE))
        if only_cells:
            detail.append(
                "%d labels appear only in column %r of %s"
                % (len(only_cells), CLUSTER_COLUMN_FOR_DE, CELL_FILE)
            )
        raise CheckFailure(
            "the set of DE group labels does not equal the set of labels in "
            "column %r of %s (%s)"
            % (CLUSTER_COLUMN_FOR_DE, CELL_FILE, "; ".join(detail))
        )
    return (
        "group blocks are consecutive and unique, in the reference's stored "
        "order with the reference's per-group row counts, and the group label "
        "set equals the %r label set of %s (%d groups aligned)"
        % (CLUSTER_COLUMN_FOR_DE, CELL_FILE, len(blocks))
    )


def check_de_scores(ref, sub):
    reference = ref.de()
    submission = sub.de()
    require_structure(reference)
    require_structure(submission)
    require_numeric(reference, DE_FLOAT32_COLUMNS)
    require_numeric(submission, DE_FLOAT32_COLUMNS)
    sub_values = submission.numeric["scores"]
    ref_values = reference.numeric["scores"]
    unrepresentable = []
    order = []
    mismatches = []
    for label, ref_start, ref_end, sub_start, _sub_end in aligned_blocks(
        reference, submission
    ):
        previous = None
        for offset, ref_index in enumerate(range(ref_start, ref_end)):
            sub_index = sub_start + offset
            left = sub_values[sub_index]
            rounded = to_float32(left)
            if rounded is None:
                unrepresentable.append((label, sub_index + 1))
                rounded = left
            elif not f32_equal(left, ref_values[ref_index]):
                mismatches.append((label, sub_index + 1))
            if previous is not None and rounded > previous:
                order.append((label, sub_index + 1))
            previous = rounded
    if unrepresentable:
        raise CheckFailure(
            "column 'scores' contains values outside the float32 range of the "
            "stored endpoint (first: %s)" % summarize(unrepresentable)
        )
    if order:
        raise CheckFailure(
            "column 'scores' is not in descending rank order within group %r at "
            "data row %d" % (order[0][0], order[0][1])
        )
    if mismatches:
        raise CheckFailure(
            "column 'scores' differs from the reference Wilcoxon statistic at "
            "the stored float32 precision at %d positions (first: %s)"
            % (len(mismatches), summarize(mismatches))
        )
    return "Wilcoxon scores match the reference at the stored float32 precision in every group"


def check_de_pvalues(ref, sub):
    reference = ref.de()
    submission = sub.de()
    require_structure(reference)
    require_structure(submission)
    require_numeric(reference, DE_PVALUE_COLUMNS)
    require_numeric(submission, DE_PVALUE_COLUMNS)
    out_of_range = [
        name
        for name in DE_PVALUE_COLUMNS
        if any(value < 0.0 or value > 1.0 for value in submission.numeric[name])
    ]
    if out_of_range:
        raise CheckFailure(
            "columns %s contain values outside [0, 1]"
            % ", ".join(repr(name) for name in out_of_range)
        )
    zero_mismatch = []
    mismatches = {column: [] for column in DE_PVALUE_COLUMNS}
    for label, ref_start, ref_end, sub_start, _sub_end in aligned_blocks(
        reference, submission
    ):
        for column in DE_PVALUE_COLUMNS:
            sub_values = submission.numeric[column]
            ref_values = reference.numeric[column]
            for offset, ref_index in enumerate(range(ref_start, ref_end)):
                sub_index = sub_start + offset
                left = sub_values[sub_index]
                right = ref_values[ref_index]
                if (left == 0.0) != (right == 0.0):
                    zero_mismatch.append((column, label, sub_index + 1))
                elif left != right:
                    mismatches[column].append((label, sub_index + 1))
    if zero_mismatch:
        raise CheckFailure(
            "exact zero p-values are meaningful: %d positions disagree with the "
            "reference on zero versus non-zero (first: %s)"
            % (len(zero_mismatch), summarize(zero_mismatch))
        )
    failed = [column for column in DE_PVALUE_COLUMNS if mismatches[column]]
    if failed:
        detail = "; ".join(
            "column %r differs at %d positions (first: %s)"
            % (column, len(mismatches[column]), summarize(mismatches[column]))
            for column in failed
        )
        raise CheckFailure(
            "p-values must equal the reference as parsed double-precision "
            "values: %s" % detail
        )
    return (
        "raw and Benjamini-Hochberg adjusted p-values match the reference "
        "exactly, including exact zeros"
    )


def check_de_gene_ranking(ref, sub):
    reference = ref.de()
    submission = sub.de()
    require_structure(reference)
    require_structure(submission)
    require_numeric(reference, DE_NUMERIC_COLUMNS)
    require_numeric(submission, DE_NUMERIC_COLUMNS)
    ref_classes = tie_classes(reference)
    sub_classes = tie_classes(submission)
    if set(sub_classes) != set(ref_classes):
        raise CheckFailure(
            "the DE group blocks do not match the reference"
        )
    universe_problems = []
    tie_problems = []
    order_problems = []
    for label, ref_start, ref_end, sub_start, sub_end in aligned_blocks(
        reference, submission
    ):
        ref_genes = set(reference.columns["names"][ref_start:ref_end])
        sub_genes = set(submission.columns["names"][sub_start:sub_end])
        if ref_genes != sub_genes:
            missing = sorted(ref_genes - sub_genes)
            extra = sorted(sub_genes - ref_genes)
            universe_problems.append(
                (label, len(missing), len(extra), missing[:MAX_REPORTED], extra[:MAX_REPORTED])
            )
            continue
        ref_group = ref_classes[label]
        sub_group = sub_classes[label]
        if set(sub_group) != set(ref_group):
            tie_problems.append(label)
            continue
        for key, ref_names in ref_group.items():
            if sorted(sub_group[key]) != sorted(ref_names):
                order_problems.append((label, key[0]))
    if universe_problems:
        raise CheckFailure(
            "the set of ranked genes differs from the reference in %d group "
            "block(s) (first: group %r, %d missing, %d unexpected)"
            % (
                len(universe_problems),
                universe_problems[0][0],
                universe_problems[0][1],
                universe_problems[0][2],
            )
        )
    if tie_problems:
        raise CheckFailure(
            "the score/p-value tie structure of the DE leaderboard differs from "
            "the reference in %d group block(s) (first: group %r)"
            % (len(tie_problems), tie_problems[0])
        )
    if order_problems:
        raise CheckFailure(
            "the ranked gene order differs from the reference in %d tie class(es) "
            "(first: group %r); rows may only be permuted inside a class of rows "
            "with identical score, pvals and pvals_adj"
            % (len(order_problems), order_problems[0][0])
        )
    return (
        "the per-group gene ranking matches the reference, up to permutation "
        "inside rows with identical score, pvals and pvals_adj"
    )


def check_de_logfoldchanges(ref, sub):
    reference = ref.de()
    submission = sub.de()
    require_structure(reference)
    require_structure(submission)
    require_numeric(reference, DE_FLOAT32_COLUMNS)
    require_numeric(submission, DE_FLOAT32_COLUMNS)
    ref_maps = logfold_maps(reference)
    sub_maps = logfold_maps(submission)
    if set(sub_maps) != set(ref_maps):
        raise CheckFailure("the DE group blocks do not match the reference")
    structure_problems = []
    value_problems = []
    for label in ref_maps:
        ref_group = ref_maps[label]
        sub_group = sub_maps.get(label)
        if sub_group is None or set(sub_group) != set(ref_group):
            structure_problems.append(label)
            continue
        for key, ref_map in ref_group.items():
            sub_map = sub_group[key]
            if set(sub_map) != set(ref_map):
                structure_problems.append(label)
                break
            for name, ref_values in ref_map.items():
                if sub_map[name] != ref_values:
                    value_problems.append((label, name))
    if structure_problems:
        raise CheckFailure(
            "the tie-class or gene structure of the DE leaderboard differs from "
            "the reference in %d group block(s) (first: group %r)"
            % (len(structure_problems), structure_problems[0])
        )
    if value_problems:
        raise CheckFailure(
            "log fold changes differ from the reference at the stored float32 "
            "precision for %d (group, gene) pairs (first: %s)"
            % (len(value_problems), summarize(value_problems))
        )
    return (
        "per-gene log fold changes match the reference at the stored float32 "
        "precision in every group"
    )


def check_de_params(ref, sub):
    reference, ref_error = ref.params()
    if ref_error is not None:
        raise CheckFailure("reference parameters file is unreadable: %s" % ref_error)
    submission, sub_error = sub.params()
    if sub_error is not None:
        raise CheckFailure(sub_error)
    problems = []
    missing = sorted(set(reference) - set(submission))
    extra = sorted(set(submission) - set(reference))
    if missing:
        problems.append("missing keys: %s" % ", ".join(repr(k) for k in missing))
    if extra:
        problems.append("unexpected keys: %s" % ", ".join(repr(k) for k in extra))
    for key in sorted(set(reference) & set(submission)):
        expected = reference[key]
        found = submission[key]
        if type(expected) is not type(found):
            problems.append(
                "key %r must be a %s (found %s %r)"
                % (key, type(expected).__name__, type(found).__name__, found)
            )
        elif expected != found:
            problems.append(
                "key %r does not record the reference value (found %r)" % (key, found)
            )
    if problems:
        raise CheckFailure(
            "%s must record exactly the run parameters of the reference DE test: "
            "%s" % (PARAMS_FILE, "; ".join(problems))
        )
    return "%s records the reference DE run parameters" % PARAMS_FILE


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


CHECK_FUNCTIONS = {
    "cell_table_structure": check_cell_structure,
    "cell_row_identity": check_cell_row_identity,
    "cell_sample_assignment": _cell_column_check("sample", "each cell's donor sample"),
    "leiden_default_clustering": _cell_column_check(
        "leiden", "default-resolution Leiden cluster"
    ),
    "leiden_coarse_clustering": _cell_column_check(
        "leiden_res_0.02", "0.02-resolution Leiden cluster"
    ),
    "leiden_de_clustering": _cell_column_check(
        "leiden_res_0.50", "0.50-resolution Leiden cluster"
    ),
    "leiden_fine_clustering": _cell_column_check(
        "leiden_res_2.00", "2.00-resolution Leiden cluster"
    ),
    "cell_type_annotation": _cell_column_check(
        "cell_type_lvl1", "broad lineage annotation"
    ),
    "umap_embedding": check_umap_embedding,
    "de_table_structure": check_de_structure,
    "de_group_blocks": check_de_group_blocks,
    "de_wilcoxon_scores": check_de_scores,
    "de_pvalues": check_de_pvalues,
    "de_gene_ranking": check_de_gene_ranking,
    "de_logfoldchanges": check_de_logfoldchanges,
    "de_run_params": check_de_params,
}

CHECK_ORDER = (
    "cell_table_structure",
    "cell_row_identity",
    "cell_sample_assignment",
    "leiden_default_clustering",
    "leiden_coarse_clustering",
    "leiden_de_clustering",
    "leiden_fine_clustering",
    "cell_type_annotation",
    "umap_embedding",
    "de_table_structure",
    "de_group_blocks",
    "de_wilcoxon_scores",
    "de_pvalues",
    "de_gene_ranking",
    "de_logfoldchanges",
    "de_run_params",
)


def run_checks(reference_dir, submission_dir):
    reference = Dataset(reference_dir)
    submission = Dataset(submission_dir, reference=reference)
    results = []
    for check_id in CHECK_ORDER:
        try:
            message = CHECK_FUNCTIONS[check_id](reference, submission)
            passed = True
        except CheckFailure as failure:
            passed = False
            message = str(failure)
        except Exception as error:  # defensive: never crash, never accept
            passed = False
            message = "internal grading error (%s: %s)" % (type(error).__name__, error)
        results.append(
            {"id": check_id, "passed": bool(passed), "message": str(message)}
        )
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    results = run_checks(args.reference_dir, args.submission_dir)
    report = {"passed": all(item["passed"] for item in results), "checks": results}
    try:
        directory = os.path.dirname(os.path.abspath(args.report))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except OSError as error:
        print("could not write report: %s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

