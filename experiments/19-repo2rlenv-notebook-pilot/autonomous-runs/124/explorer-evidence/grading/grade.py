#!/usr/bin/env python3
"""Acceptance grader for the LuxC profile-HMM build and database search task.

Compares the two declared outputs (LuxC.hmm, LuxC.domtbl) against the
reference outputs, using HMMER3 plan7 ASCII and hmmsearch domain-table
parsing conventions.
"""

import argparse
import json
import math
import os
import sys

HMM_REL = "LuxC.hmm"
DOMTBL_REL = "LuxC.domtbl"

# Tolerances (documented in the public acceptance rules)
TOL_HMM = 2e-5          # HMMER3 ASCII prints parameters with 5 decimals
TOL_SCORE = 0.06         # hmmsearch domtbl prints scores/bias with 1 decimal
TOL_ACC = 0.006         # domtbl prints average posterior accuracy with 2 decimals
TOL_INT_FIELD = 0.5     # integer-length/coordinate fields: effectively exact
TOL_EVALUE_REL = 0.05   # E-value relative tolerance (<= 5% of the larger magnitude)

IDENTITY_KEYS = ["NAME", "ACC", "DESC", "LENG", "NSEQ", "CKSUM", "GA", "TC", "NC"]


def try_float(token):
    """Parse a printable numeric token; reject '*' and non-finite values."""
    try:
        value = float(token)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


# ---------------------------------------------------------------- HMM parsing

def load_hmm_tokens(path):
    """Tokenize an HMMER3 ASCII HMM, skipping run-specific lines.

    The HMMER3/f version banner, DATE and COM lines are run-specific and
    excluded from every comparison. Everything else is tokenized on
    whitespace so formatting/indentation differences do not matter.
    """
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", errors="replace")
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        tokens = line.split()
        head = tokens[0]
        if head.startswith("HMMER3/") or head in ("DATE", "COM"):
            continue
        rows.append(tokens)
    return rows


def split_hmm_rows(rows):
    """Split parsed rows into annotation rows (by header key) and data rows."""
    annotation = []
    data = []
    for tokens in rows:
        if tokens[0] in IDENTITY_KEYS:
            annotation.append(tokens)
        else:
            data.append(tokens)
    return annotation, data


def count_model_positions(rows):
    """Return the number of match-state positions implied by the row layout.

    HMMER3 plan7 ASCII layout after the per-position column header:
      - a "m->m m->i m->d i->m i->i d->m d->d" transition-labels row,
      - a "COMPO" block of 3 rows (compound emission, insert, transition),
      - then one 3-row block per model position (match emissions, insert
        emissions, transitions), terminated by the // line.
    """
    try:
        hmm_idx = next(i for i, t in enumerate(rows) if t[0] == "HMM")
    except StopIteration:
        return None
    if hmm_idx + 5 >= len(rows):
        return None
    if rows[hmm_idx + 1][0] != "m->m":
        return None
    if rows[hmm_idx + 2][0] != "COMPO":
        return None
    rest = rows[hmm_idx + 5:]
    if not rest:
        return None
    while rest and rest[-1][0] == "//":
        rest = rest[:-1]
    if not rest or len(rest) % 3 != 0:
        return None
    return len(rest) // 3


def annotation_value(rows, key):
    for tokens in rows:
        if tokens[0] == key:
            return tokens[1] if len(tokens) > 1 else ""
    return None


# ------------------------------------------------------------- domtbl parsing

# 0-based column indices, hmmsearch --domtblout domain table layout (22 fixed
# fields + free-text description).
DOMTBL_EVALUE_COLS = (6, 11, 12)
DOMTBL_SCORE_COLS = (7, 13)
DOMTBL_BIAS_COLS = (8, 14)
DOMTBL_ACC_COL = 21
DOMTBL_INT_COLS = (2, 5, 9, 10, 15, 16, 17, 18, 19, 20)
DOMTBL_STR_COLS = (0, 1, 3, 4, 22)


def load_domtbl_rows(path):
    """Parse the domain table into field lists in file order.

    Comment lines (leading '#') are header text and not compared. Each data
    row must split into the 22 standard fields; an optional 23rd field is the
    free-text description.
    """
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", errors="replace")
    rows = []
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        fields = line.split(None, 22)
        if len(fields) < 22:
            raise ValueError("domain-table row has fewer than 22 fields")
        if len(fields) == 22:
            fields = fields + [""]
        rows.append(fields)
    return rows


def domtbl_row_is_structurally_valid(fields):
    """Check that every numeric column parses as a finite number."""
    for idx in DOMTBL_INT_COLS:
        if try_float(fields[idx]) is None:
            return False, "column %d (%s) is not a finite number" % (idx + 1, fields[idx])
    for idx in DOMTBL_EVALUE_COLS:
        if try_float(fields[idx]) is None:
            return False, "E-value column %d (%s) is not a finite number" % (idx + 1, fields[idx])
    for idx in DOMTBL_SCORE_COLS + DOMTBL_BIAS_COLS:
        if try_float(fields[idx]) is None:
            return False, "score/bias column %d (%s) is not a finite number" % (idx + 1, fields[idx])
    if try_float(fields[DOMTBL_ACC_COL]) is None:
        return False, "accuracy column is not a finite number"
    dom_num = try_float(fields[9])
    dom_total = try_float(fields[10])
    if dom_num is None or dom_total is None or dom_num < 1 or dom_num > dom_total:
        return False, "domain index out of range"
    return True, ""


# ----------------------------------------------------------- comparison logic

def compare_hmm_token_rows(sub_rows, ref_rows, tol, label):
    """Compare equal-length tokenized HMM rows numerically or textually."""
    if len(sub_rows) != len(ref_rows):
        return False, "%s: line count %d does not match reference %d" % (label, len(sub_rows), len(ref_rows))
    for lineno, (stokens, rtokens) in enumerate(zip(sub_rows, ref_rows), start=1):
        if len(stokens) != len(rtokens):
            return False, "%s line %d: field count %d != %d" % (label, lineno, len(stokens), len(rtokens))
        for pos, (s, r) in enumerate(zip(stokens, rtokens)):
            fs, fr = try_float(s), try_float(r)
            if fs is not None and fr is not None:
                if abs(fs - fr) > tol:
                    return False, "%s line %d field %d: %s != %s" % (label, lineno, pos + 1, s, r)
            elif s != r:
                return False, "%s line %d field %d: %r != %r" % (label, lineno, pos + 1, s, r)
    return True, ""


def annotation_map(annotation_rows):
    """Map header key -> value tokens (each HMMER3 header key appears once)."""
    amap = {}
    for tokens in annotation_rows:
        key = tokens[0]
        if key in amap:
            raise ValueError("duplicate header key %s" % key)
        amap[key] = tokens[1:]
    return amap


def compare_hmm_annotation(sub_rows, ref_rows, tol):
    """Compare annotation lines key-by-key, order-insensitively."""
    try:
        sub_map = annotation_map(sub_rows)
        ref_map = annotation_map(ref_rows)
    except ValueError as exc:
        return False, "model header: %s" % exc
    if set(sub_map) != set(ref_map):
        missing = sorted(set(ref_map) - set(sub_map))
        extra = sorted(set(sub_map) - set(ref_map))
        return False, ("model header key set differs; missing %s, unexpected %s"
                       % (",".join(missing) or "-", ",".join(extra) or "-"))
    for key in sorted(ref_map):
        stokens, rtokens = sub_map[key], ref_map[key]
        if len(stokens) != len(rtokens):
            return False, "model header %s: %d values, expected %d" % (key, len(stokens), len(rtokens))
        for pos, (s, r) in enumerate(zip(stokens, rtokens)):
            fs, fr = try_float(s), try_float(r)
            if fs is not None and fr is not None:
                if abs(fs - fr) > tol:
                    return False, "model header %s value %d: %s != %s" % (key, pos + 1, s, r)
            elif s != r:
                return False, "model header %s value %d: %r != %r" % (key, pos + 1, s, r)
    return True, ""


def compare_domtbl_row(sub, ref, idx):
    for col in DOMTBL_STR_COLS:
        if col >= len(sub) or col >= len(ref):
            return False, "row %d column %d missing" % (idx + 1, col + 1)
        if sub[col] != ref[col]:
            return False, "row %d column %d: %r != %r" % (idx + 1, col + 1, sub[col], ref[col])
    for col in DOMTBL_INT_COLS:
        fs, fr = try_float(sub[col]), try_float(ref[col])
        if fs is None or fr is None or abs(fs - fr) > TOL_INT_FIELD:
            return False, "row %d column %d (coordinate/length): %s != %s" % (idx + 1, col + 1, sub[col], ref[col])
    for col in DOMTBL_EVALUE_COLS:
        fs, fr = try_float(sub[col]), try_float(ref[col])
        if fs is None or fr is None:
            return False, "row %d column %d: non-finite E-value" % (idx + 1, col + 1)
        if abs(fs - fr) > TOL_EVALUE_REL * max(abs(fs), abs(fr)):
            return False, "row %d column %d (E-value): %s != %s" % (idx + 1, col + 1, sub[col], ref[col])
    for col in DOMTBL_SCORE_COLS + DOMTBL_BIAS_COLS:
        fs, fr = try_float(sub[col]), try_float(ref[col])
        # scores/bias are printed with 1 decimal; half a printed unit plus
        # floating-point rounding slack is the acceptance boundary
        if fs is None or fr is None or abs(fs - fr) > TOL_SCORE:
            return False, "row %d column %d (score/bias): %s != %s" % (idx + 1, col + 1, sub[col], ref[col])
    fs, fr = try_float(sub[DOMTBL_ACC_COL]), try_float(ref[DOMTBL_ACC_COL])
    if fs is None or fr is None or abs(fs - fr) > TOL_ACC:
        return False, "row %d accuracy column: %s != %s" % (idx + 1, sub[DOMTBL_ACC_COL], ref[DOMTBL_ACC_COL])
    return True, ""


# ------------------------------------------------------------------- grading

class Registry(object):
    def __init__(self):
        self.checks = []

    def record(self, check_id, passed, message):
        self.checks.append({"id": check_id, "passed": bool(passed), "message": message})


def grade(reference_dir, submission_dir):
    registry = Registry()

    ref_hmm_path = os.path.join(reference_dir, HMM_REL)
    sub_hmm_path = os.path.join(submission_dir, HMM_REL)
    ref_dom_path = os.path.join(reference_dir, DOMTBL_REL)
    sub_dom_path = os.path.join(submission_dir, DOMTBL_REL)

    # ---- reference side (guaranteed present) ------------------------------
    ref_hmm_tokens = load_hmm_tokens(ref_hmm_path)
    ref_annotation, ref_data = split_hmm_rows(ref_hmm_tokens)
    ref_n_positions = count_model_positions(ref_hmm_tokens)
    ref_dom_rows = load_domtbl_rows(ref_dom_path)

    # ---- check: hmm_ascii_structure ---------------------------------------
    check_id = "hmm_ascii_structure"
    ok = True
    msgs = []
    if not os.path.isfile(sub_hmm_path):
        registry.record(check_id, False, "required output %s is missing" % HMM_REL)
    else:
        try:
            sub_hmm_tokens = load_hmm_tokens(sub_hmm_path)
        except Exception as exc:  # pragma: no cover - defensive
            registry.record(check_id, False, "could not read %s: %s" % (HMM_REL, exc))
            sub_hmm_tokens = None
        if sub_hmm_tokens is not None:
            if not sub_hmm_tokens:
                ok = False
                msgs.append("%s contains no parseable content" % HMM_REL)
            else:
                if sub_hmm_tokens[-1][0] != "//":
                    ok = False
                    msgs.append("file is not terminated by a // line")
                n_pos = count_model_positions(sub_hmm_tokens)
                if n_pos is None:
                    ok = False
                    msgs.append("HMM column header / COMPO block layout is malformed")
                elif n_pos != ref_n_positions:
                    ok = False
                    msgs.append("model has %d match positions, expected the reference %d" % (n_pos, ref_n_positions))
                present = set(t[0] for t in sub_hmm_tokens if t)
                missing = [k for k in IDENTITY_KEYS + ["ALPH", "RF", "MM", "CONS", "CS", "MAP", "EFFN", "STATS", "HMM", "COMPO"] if k not in present]
                if missing:
                    ok = False
                    msgs.append("missing required header keys: %s" % ", ".join(missing))
            # native-reader validation (HMMER3 plan7 ASCII reader)
            parse_ok, parse_msg = True, ""
            try:
                import pyhmmer
                with pyhmmer.plan7.HMMFile(sub_hmm_path) as hf:
                    hmm_obj = hf.read()
                if hmm_obj.M != ref_n_positions:
                    parse_ok, parse_msg = False, "native reader reports %d model positions" % hmm_obj.M
                if hmm_obj.alphabet != pyhmmer.easel.Alphabet.amino():
                    parse_ok, parse_msg = False, "native reader reports a non-amino-acid alphabet"
            except Exception as exc:
                parse_ok = False
                parse_msg = "not readable as a valid HMMER3 ASCII profile HMM (%s)" % exc
            if not parse_ok:
                ok = False
                msgs.append(parse_msg)
        registry.record(check_id, ok, "; ".join(msgs) if msgs else
                        "LuxC.hmm is a structurally valid HMMER3 ASCII amino-acid profile HMM with %d match positions" % ref_n_positions)

    # ---- check: hmm_model_annotation ---------------------------------------
    check_id = "hmm_model_annotation"
    if not os.path.isfile(sub_hmm_path):
        registry.record(check_id, False, "required output %s is missing" % HMM_REL)
    else:
        try:
            sub_hmm_tokens = load_hmm_tokens(sub_hmm_path)
            sub_annotation, _sub_data = split_hmm_rows(sub_hmm_tokens)
            ok, msg = compare_hmm_annotation(sub_annotation, ref_annotation, TOL_HMM)
            registry.record(check_id, ok, msg if msg else
                            "NAME/ACC/DESC/LENG/NSEQ/CKSUM and GA/TC/NC cutoff lines match the reference model")
        except Exception as exc:
            registry.record(check_id, False, "could not compare model header: %s" % exc)

    # ---- check: hmm_model_parameters ---------------------------------------
    check_id = "hmm_model_parameters"
    if not os.path.isfile(sub_hmm_path):
        registry.record(check_id, False, "required output %s is missing" % HMM_REL)
    else:
        try:
            sub_hmm_tokens = load_hmm_tokens(sub_hmm_path)
            _sub_annotation, sub_data = split_hmm_rows(sub_hmm_tokens)
            # The model parameters: EFFN / calibration STATS lines, HMM column
            # header, COMPO block and every per-position block (emissions,
            # insert emissions, transitions and consensus/map characters).
            ok, msg = compare_hmm_token_rows(sub_data, ref_data, TOL_HMM, "model body")
            if ok:
                registry.record(check_id, True, "effective sequence number, MSV/VITERBI/FORWARD calibration "
                                "statistics, COMPO block and all %d per-position emission/insert/transition "
                                "parameters match the reference model" % ref_n_positions)
            else:
                registry.record(check_id, False, msg)
        except Exception as exc:
            registry.record(check_id, False, "could not compare model parameters: %s" % exc)

    # ---- check: domtbl_structure -------------------------------------------
    check_id = "domtbl_structure"
    if not os.path.isfile(sub_dom_path):
        registry.record(check_id, False, "required output %s is missing" % DOMTBL_REL)
    else:
        ok = True
        msgs = []
        sub_dom_rows = None
        try:
            sub_dom_rows = load_domtbl_rows(sub_dom_path)
        except Exception as exc:
            ok = False
            msgs.append("domain table is malformed: %s" % exc)
        if sub_dom_rows is not None:
            if not sub_dom_rows:
                ok = False
                msgs.append("domain table contains no data rows")
            for i, fields in enumerate(sub_dom_rows):
                valid, why = domtbl_row_is_structurally_valid(fields)
                if not valid:
                    ok = False
                    msgs.append("row %d: %s" % (i + 1, why))
                    break
        registry.record(check_id, ok, "; ".join(msgs) if msgs else
                        "LuxC.domtbl is a well-formed hmmsearch domain table with %d data rows" % len(sub_dom_rows or []))

    # ---- check: domtbl_hits -------------------------------------------------
    check_id = "domtbl_hits"
    if not os.path.isfile(sub_dom_path):
        registry.record(check_id, False, "required output %s is missing" % DOMTBL_REL)
    else:
        ok, msg = True, ""
        try:
            sub_dom_rows = load_domtbl_rows(sub_dom_path)
        except Exception as exc:
            sub_dom_rows = None
            ok, msg = False, "domain table is malformed: %s" % exc
        if sub_dom_rows is not None:
            if len(sub_dom_rows) != len(ref_dom_rows):
                ok, msg = False, ("domain table has %d rows, expected %d (reported targets and domains per "
                                  "target are requested scientific content; do not pad or prune)" % (len(sub_dom_rows), len(ref_dom_rows)))
            else:
                reasons = []
                for i, (sub_row, ref_row) in enumerate(zip(sub_dom_rows, ref_dom_rows)):
                    row_ok, why = compare_domtbl_row(sub_row, ref_row, i)
                    if not row_ok:
                        reasons.append(why)
                if reasons:
                    ok, msg = False, "row-by-row comparison failed (order-sensitive, best full-sequence E-value first): " + "; ".join(reasons[:5])
                else:
                    ok, msg = True, ("all %d reported domains match the reference in order: target identity, scores, "
                                    "E-values, coordinates and descriptions" % len(ref_dom_rows))
        registry.record(check_id, ok, msg if msg else "domain table matches")

    # ---- check: hmm_domtbl_query_consistency --------------------------------
    check_id = "hmm_domtbl_query_consistency"
    both = os.path.isfile(sub_hmm_path) and os.path.isfile(sub_dom_path)
    if not both:
        registry.record(check_id, False, "one or both of %s / %s is missing" % (HMM_REL, DOMTBL_REL))
    else:
        ok = True
        msgs = []
        try:
            sub_hmm_tokens = load_hmm_tokens(sub_hmm_path)
            sub_dom_rows = load_domtbl_rows(sub_dom_path)
            sub_name = annotation_value(sub_hmm_tokens, "NAME")
            sub_acc = annotation_value(sub_hmm_tokens, "ACC")
            sub_leng = try_float(annotation_value(sub_hmm_tokens, "LENG"))
            # the domtbl query columns must describe the model in LuxC.hmm,
            # which by the other checks must equal the reference model.
            for i, fields in enumerate(sub_dom_rows):
                qname = fields[3]
                qacc = fields[4]
                qlen = try_float(fields[5])
                if qname != sub_name or qacc != sub_acc or qlen is None or sub_leng is None or abs(qlen - sub_leng) > TOL_INT_FIELD:
                    ok = False
                    msgs.append("row %d: query %s/%s/%s does not match the model %s/%s/%s" %
                                (i + 1, qname, qacc, fields[5], sub_name, sub_acc, annotation_value(sub_hmm_tokens, "LENG")))
                    break
        except Exception as exc:
            ok = False
            msgs.append("could not verify cross-file consistency: %s" % exc)
        registry.record(check_id, ok, "; ".join(msgs) if msgs else
                        "every domain-table row reports the query name/accession/length of the profile HMM in %s" % HMM_REL)

    return {"passed": all(c["passed"] for c in registry.checks), "checks": registry.checks}


def main():
    parser = argparse.ArgumentParser(description="Grade the LuxC profile HMM task outputs")
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    report = grade(args.reference_dir, args.submission_dir)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

