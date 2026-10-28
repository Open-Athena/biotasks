#!/usr/bin/env python3
"""Acceptance grader: LuxC profile HMM build + hmmsearch domain table.

Compares the submitted HMMER3/f profile (LuxC.hmm) and hmmsearch domain
table (LuxC.domtbl) against the reference computation, field by field,
using token-level parsing with a printed-precision numeric tolerance.

The model block of the profile is compared state by state over the common
prefix of reference and submission even when the block's line count or
layout disagrees with its declared LENG; the count/layout mismatch is
then reported as an additional message, so wrong values inside a
mis-sized block are rejected on their values instead of being hidden
behind a structural abort.
"""

import argparse
import json
import math
import os
import re
import sys

HMM_PATH = "LuxC.hmm"
DOMTBL_PATH = "LuxC.domtbl"

FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
EXP_RE = re.compile(r"([eE])([+-]?\d+)$")
TRANS_HEADER = ["m->m", "m->i", "m->d", "i->m", "i->i", "d->m", "d->d"]
DATA_LINE_MIN_FIELDS = 23  # 22 fixed-width fields + free-text description


class CheckFailure(Exception):
    pass


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------

def read_text(path):
    if not os.path.isfile(path):
        raise CheckFailure("missing file: %s" % path)
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise CheckFailure("cannot read %s: %s" % (path, exc))
    if not data:
        raise CheckFailure("empty file: %s" % path)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CheckFailure("file is not UTF-8 text: %s" % exc)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_lines(text):
    lines = text.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    if not lines:
        raise CheckFailure("file has no content lines")
    return lines


def decode_number(tok):
    """Decode a decimal / scientific literal.

    Returns (value, tol_half_last_place, is_plain_integer), or None when the
    token is not a finite decimal literal.
    """
    if not FLOAT_RE.match(tok):
        return None
    m = EXP_RE.search(tok)
    if m:
        exp = int(m.group(2))
        mant = tok[: m.start()]
        has_exp = True
    else:
        exp = 0
        mant = tok
        has_exp = False
    dec = len(mant.split(".", 1)[1]) if "." in mant else 0
    try:
        value = float(tok)
    except (ValueError, OverflowError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    tol = 0.5 * (10.0 ** (exp - dec)) * (1.0 + 1e-9)
    return (value, tol, (not has_exp) and dec == 0)


def compare_tokens(ref_tok, sub_tok):
    """Compare one field token against the reference token, or return why not."""
    if ref_tok == sub_tok:
        return None
    ref = decode_number(ref_tok)
    if ref is None:  # non-numeric reference token: exact string identity
        return "token %r != reference %r" % (sub_tok, ref_tok)
    if ref[2]:  # integer-valued reference token requires exact equality
        return "integer value %r != reference %r" % (sub_tok, ref_tok)
    sub = decode_number(sub_tok)
    if sub is None:
        return "value %r for reference %r is not a finite number" % (sub_tok, ref_tok)
    if abs(ref[0] - sub[0]) > ref[1]:
        return ("value %r differs from reference %r by more than half a unit "
                "in the reference's last printed place" % (sub_tok, ref_tok))
    return None


def compare_token_lists(ref_list, sub_list, what):
    if len(ref_list) != len(sub_list):
        return "%s: %d tokens, reference has %d" % (what, len(sub_list), len(ref_list))
    for i, (rt, st) in enumerate(zip(ref_list, sub_list)):
        err = compare_tokens(rt, st)
        if err is not None:
            return "%s token %d: %s" % (what, i + 1, err)
    return None


# ----------------------------------------------------------------------------
# HMMER3/f profile parsing
# ----------------------------------------------------------------------------

def parse_hmm(text):
    lines = split_lines(text)
    magic = lines[0].split()
    if not magic or magic[0] != "HMMER3/f":
        raise CheckFailure("first line is not an HMMER3/f ASCII header")
    header = []
    i = 1
    while i < len(lines):
        tok = lines[i].split()
        if not tok:
            raise CheckFailure("blank line %d inside the header" % (i + 1))
        if tok[0] == "HMM":
            break
        if tok[0] in ("DATE", "COM"):  # runtime provenance, not compared
            i += 1
            continue
        header.append(tok)
        i += 1
    else:
        raise CheckFailure("no HMM annotation block found")
    letters = lines[i].split()
    if len(letters) != 21 or letters[0] != "HMM":
        raise CheckFailure("malformed amino-acid alphabet line")
    if i + 1 >= len(lines):
        raise CheckFailure("truncated HMM file (no transition header)")
    if lines[i + 1].split() != TRANS_HEADER:
        raise CheckFailure("malformed transition order header line")
    body = []
    for j in range(i + 2, len(lines)):
        tok = lines[j].split()
        if not tok:
            raise CheckFailure("blank line %d inside the model block" % (j + 1))
        body.append(tok)
    if not body or body[-1] != ["//"]:
        raise CheckFailure("model block does not end with //")
    body = body[:-1]

    header_map = {}
    seen_stats = set()
    for tok in header:
        key = tok[0]
        if key == "STATS":
            if len(tok) != 5:
                raise CheckFailure("malformed STATS line")
            if tok[2] in seen_stats:
                raise CheckFailure("duplicate STATS LOCAL %s line" % tok[2])
            seen_stats.add(tok[2])
            continue
        if key in header_map:
            raise CheckFailure("duplicate header field %s" % key)
        header_map[key] = tok[1:]
    for req in ("NAME", "ACC", "DESC", "LENG", "ALPH", "RF", "MM", "CONS",
                "CS", "MAP", "NSEQ", "EFFN", "CKSUM"):
        if req not in header_map:
            raise CheckFailure("missing required header field %s" % req)
    for stat in ("MSV", "VITERBI", "FORWARD"):
        stats = [t for t in header if t[:3] == ["STATS", "LOCAL", stat]]
        if len(stats) != 1:
            raise CheckFailure("missing/malformed STATS LOCAL %s line" % stat)

    def as_int(key):
        val = header_map[key]
        if len(val) != 1 or not val[0].isdigit():
            raise CheckFailure("header field %s is not a positive integer" % key)
        return int(val[0])

    m_len, nseq, cksum = as_int("LENG"), as_int("NSEQ"), as_int("CKSUM")
    if m_len <= 0 or nseq <= 0:
        raise CheckFailure("non-positive LENG or NSEQ")

    expected_lines = 3 + 3 * m_len
    line_count_mismatch = (len(body) != expected_lines)
    if len(body) < 3:
        raise CheckFailure("model block has %d lines, expected %d "
                           "(3 null-model lines + 3 per match state)"
                           % (len(body), expected_lines))
    if body[0][0] != "COMPO" or len(body[0]) != 21:
        raise CheckFailure("malformed COMPO null-model line")
    if len(body[1]) != 20 or len(body[2]) != 7:
        raise CheckFailure("malformed null-model insert/transition line")
    # Structure-validate every complete state triple present, even when the
    # body line count disagrees with LENG: wrong values inside a mis-sized
    # block must still be token-compared, not hidden behind a count abort.
    states_present = (len(body) - 3) // 3
    for k in range(1, min(m_len, states_present) + 1):
        mline, iline, tline = body[3 * k], body[3 * k + 1], body[3 * k + 2]
        if len(mline) != 26 or not mline[0].isdigit() or int(mline[0]) != k:
            raise CheckFailure("malformed match-state line %d" % k)
        if len(iline) != 20:
            raise CheckFailure("malformed insert emission line for state %d" % k)
        if len(tline) != 7:
            raise CheckFailure("malformed transition line for state %d" % k)
    return {"magic": magic[0], "header": header, "header_map": header_map,
            "letters": letters, "body": body, "M": m_len, "NSEQ": nseq,
            "CKSUM": cksum, "line_count_mismatch": line_count_mismatch,
            "body_line_count": len(body), "expected_lines": expected_lines}


def parse_hmm_file(path):
    return parse_hmm(read_text(path))


def line_count_message(parsed_hmm):
    """Layout/count mismatch for a model block that disagrees with its LENG."""
    if parsed_hmm.get("line_count_mismatch"):
        return ("model block has %d lines, expected %d "
                "(3 null-model lines + 3 per match state)"
                % (parsed_hmm["body_line_count"], parsed_hmm["expected_lines"]))
    return None


# ----------------------------------------------------------------------------
# domtbl parsing
# ----------------------------------------------------------------------------

def parse_domtbl(text):
    lines = split_lines(text)
    if len(lines) < 4:
        raise CheckFailure("domain table must have 3 comment lines and data rows")
    comments = []
    for idx in range(3):
        if not lines[idx].startswith("#"):
            raise CheckFailure("missing comment header line %d" % (idx + 1))
        comments.append(lines[idx].rstrip())
    rows = []
    for line in lines[3:]:
        if not line.strip():
            raise CheckFailure("blank data line in domain table")
        if line.lstrip().startswith("#"):
            raise CheckFailure("unexpected extra comment line: %r" % line[:40])
        fields = line.rstrip().split(None, DATA_LINE_MIN_FIELDS - 1)
        if len(fields) != DATA_LINE_MIN_FIELDS:
            raise CheckFailure("data row does not have 22 fixed fields followed "
                               "by a description: %r" % line[:60])
        rows.append(fields)
    return {"comments": comments, "rows": rows}


def parse_domtbl_file(path):
    return parse_domtbl(read_text(path))


def row_int(rows, i, field, name):
    tok = rows[i][field]
    if not re.match(r"^\d+$", tok):
        raise CheckFailure("row %d: field %s is not an integer: %r" % (i + 1, name, tok))
    return int(tok)


def row_float(rows, i, field, name):
    tok = rows[i][field]
    val = decode_number(tok)
    if val is None:
        raise CheckFailure("row %d: field %s is not a finite number: %r" % (i + 1, name, tok))
    return val[0]


# ----------------------------------------------------------------------------
# trusted input grounding
# ----------------------------------------------------------------------------

def trusted_file(rel):
    base = os.environ.get("BIOTASKS_TRUSTED_INPUT_DIR")
    if not base:
        return None
    path = os.path.join(base, rel)
    return path if os.path.isfile(path) else None


def load_alignment_annotations():
    path = trusted_file(os.path.join("data", "msa", "LuxC.sto"))
    if path is None:
        return None, None
    gf, names = {}, []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if line.startswith("#=GF"):
                    parts = line[4:].split(None, 1)
                    key = parts[0]
                    val = " ".join(parts[1].split()) if len(parts) > 1 else ""
                    if key not in gf:
                        gf[key] = val
                elif line.startswith("#") or not line.strip():
                    continue
                elif line.strip() == "//":
                    break
                else:
                    name = line.split()[0]
                    if name not in names:
                        names.append(name)
    except OSError:
        return None, None
    return gf, len(names)


def load_fasta_entries():
    path = trusted_file(os.path.join("data", "seqs", "LuxC.faa"))
    if path is None:
        return None
    entries, name, seq, rest = {}, None, [], None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if line.startswith(">"):
                    if name is not None:
                        entries[name] = (rest, len("".join(seq).replace("-", "")))
                    parts = line[1:].split(None, 1)
                    name = parts[0] if parts else ""
                    rest = parts[1].strip() if len(parts) > 1 else "-"
                    seq = []
                else:
                    seq.append(line.strip())
        if name is not None:
            entries[name] = (rest, len("".join(seq).replace("-", "")))
    except OSError:
        return None
    return entries


# ----------------------------------------------------------------------------
# checks
# ----------------------------------------------------------------------------

CHECKS = []


def register(check_id, kind, artifacts, requirement):
    def deco(fn):
        CHECKS.append({"id": check_id, "kind": kind, "artifacts": artifacts,
                       "requirement": requirement, "fn": fn})
        return fn
    return deco


@register("hmm_present", "structural", [HMM_PATH],
          "outputs/LuxC.hmm exists, is non-empty UTF-8 text and starts with the "
          "HMMER3/f ASCII profile header.")
def hmm_present(ref_dir, sub_dir):
    _read_reference_hmm(ref_dir)
    read_text(os.path.join(sub_dir, HMM_PATH))
    first = split_lines(read_text(os.path.join(sub_dir, HMM_PATH)))[0].split()
    if not first or first[0] != "HMMER3/f":
        raise CheckFailure("first line does not declare HMMER3/f")
    return True, "profile file present and non-empty"


@register("domtbl_present", "structural", [DOMTBL_PATH],
          "outputs/LuxC.domtbl exists, is non-empty UTF-8 text and starts with "
          "the three '#' comment header lines of the hmmsearch domain table.")
def domtbl_present(ref_dir, sub_dir):
    _read_reference_domtbl(ref_dir)
    lines = split_lines(read_text(os.path.join(sub_dir, DOMTBL_PATH)))
    if len(lines) < 4:
        raise CheckFailure("domain table must contain 3 comment lines and data rows")
    for idx in range(3):
        if not lines[idx].startswith("#"):
            raise CheckFailure("line %d is not a comment header line" % (idx + 1))
    return True, "domain table file present and non-empty"


@register("hmm_header", "scientific", [HMM_PATH],
          "Profile header scientific fields match the reference computation "
          "and, where stated, the alignment annotations carried in #=GF lines.")
def hmm_header(ref_dir, sub_dir):
    ref = _read_reference_hmm(ref_dir)
    sub = parse_hmm_file(os.path.join(sub_dir, HMM_PATH))
    msgs = []
    if len(ref["header"]) != len(sub["header"]):
        raise CheckFailure("header has %d annotation fields, reference has %d"
                           % (len(sub["header"]), len(ref["header"])))
    for rt, st in zip(ref["header"], sub["header"]):
        if rt[0] != st[0]:
            raise CheckFailure("header key mismatch: %r vs %r" % (st[0], rt[0]))
        err = compare_token_lists(rt[1:], st[1:], "header field %s" % rt[0])
        if err is not None:
            msgs.append(err)

    gf, n_seq = load_alignment_annotations()
    if gf is not None:
        def field(key):
            return sub["header_map"].get(key, [])
        for label, want in (("NAME", gf.get("ID", "")), ("ACC", gf.get("AC", "")),
                            ("DESC", gf.get("DE", ""))):
            got = " ".join(field(label))
            if " ".join(want.split()) != got:
                msgs.append("%s %r does not match alignment annotation %r"
                            % (label, got, " ".join(want.split())))
        for label in ("GA", "TC", "NC"):
            head = gf.get(label, "").split(";")[0]
            want_nums, got = head.split(), field(label)
            if len(want_nums) != 2 or len(got) != 2:
                msgs.append("%s cutoff does not carry the two annotated values" % label)
                continue
            for w, g in zip(want_nums, got):
                wn, gn = decode_number(w), decode_number(g)
                if wn is None or gn is None or abs(wn[0] - gn[0]) > 0.05:
                    msgs.append("%s cutoff %r does not match annotation %r" % (label, g, w))
        if gf.get("SQ", "").strip():
            if sub["NSEQ"] != int(gf["SQ"].strip()):
                msgs.append("NSEQ %d does not match the alignment's #=GF SQ count"
                           % sub["NSEQ"])
        elif n_seq and sub["NSEQ"] != n_seq:
            msgs.append("NSEQ %d does not match the %d sequences in the alignment"
                        % (sub["NSEQ"], n_seq))
    if msgs:
        return False, "; ".join(msgs[:5])
    note = "" if gf is not None else " (alignment grounding unavailable)"
    return True, "profile header matches the reference and input annotations" + note


@register("hmm_model", "scientific", [HMM_PATH],
          "Calibrated model block matches the reference profile state by state.")
def hmm_model(ref_dir, sub_dir):
    ref = _read_reference_hmm(ref_dir)
    sub = parse_hmm_file(os.path.join(sub_dir, HMM_PATH))
    msgs = []
    err = compare_token_lists(ref["letters"], sub["letters"], "alphabet line")
    if err is not None:
        msgs.append(err)
    # Token-compare the common prefix of the model block, so wrong values are
    # rejected on their values even when the block is also mis-sized.
    overlap = min(len(ref["body"]), len(sub["body"]))
    for i in range(overlap):
        err = compare_token_lists(ref["body"][i], sub["body"][i],
                                  "model line %d" % (i + 1))
        if err is not None:
            msgs.append(err)
            break
    count_msg = line_count_message(sub)
    if count_msg is not None:
        msgs.append(count_msg)
    if len(ref["body"]) != len(sub["body"]) and count_msg is None:
        msgs.append("model block has %d lines, reference has %d"
                    % (len(sub["body"]), len(ref["body"])))
    if msgs:
        return False, "; ".join(msgs[:3])
    return True, "all %d match states agree with the reference profile" % sub["M"]


@register("domtbl_rows", "scientific", [DOMTBL_PATH],
          "Domain table rows match the reference computation row by row.")
def domtbl_rows(ref_dir, sub_dir):
    ref = _read_reference_domtbl(ref_dir)
    sub = parse_domtbl_file(os.path.join(sub_dir, DOMTBL_PATH))
    msgs = []
    for i in range(3):
        if sub["comments"][i] != ref["comments"][i]:
            msgs.append("comment header line %d differs" % (i + 1))
    if len(sub["rows"]) != len(ref["rows"]):
        msgs.append("domain table has %d data rows, reference has %d"
                    % (len(sub["rows"]), len(ref["rows"])))
    fasta = load_fasta_entries()
    for i, (rr, sr) in enumerate(zip(ref["rows"], sub["rows"])):
        for f in range(22):
            err = compare_tokens(rr[f], sr[f])
            if err is not None:
                msgs.append("row %d field %d: %s" % (i + 1, f + 1, err))
                break
        if sr[22].rstrip() != rr[22].rstrip():
            msgs.append("row %d: target description differs from the reference"
                        % (i + 1))
        if fasta is not None:
            if sr[0] not in fasta:
                msgs.append("row %d: target %r is not a sequence in the searched "
                            "database" % (i + 1, sr[0]))
            else:
                desc, length = fasta[sr[0]]
                if row_int(sub["rows"], i, 2, "target length") != length:
                    msgs.append("row %d: target length does not match the database "
                                "sequence length" % (i + 1))
                if sr[22].rstrip() != desc.rstrip():
                    msgs.append("row %d: target description does not match the "
                                "database header" % (i + 1))
    if msgs:
        return False, "; ".join(msgs[:5])
    note = "" if fasta is not None else " (FASTA grounding unavailable)"
    return True, "all %d domain rows match the reference" % len(sub["rows"]) + note


@register("domtbl_profile_consistency", "scientific", [DOMTBL_PATH, HMM_PATH],
          "Domain table is internally consistent with the submitted profile and "
          "input database.")
def domtbl_profile_consistency(ref_dir, sub_dir):
    _read_reference_hmm(ref_dir)
    _read_reference_domtbl(ref_dir)
    sub_hmm = parse_hmm_file(os.path.join(sub_dir, HMM_PATH))
    sub = parse_domtbl_file(os.path.join(sub_dir, DOMTBL_PATH))
    rows = sub["rows"]
    if not rows:
        raise CheckFailure("domain table contains no data rows")
    msgs = []
    count_msg = line_count_message(sub_hmm)
    if count_msg is not None:
        msgs.append(count_msg)
    qname = " ".join(sub_hmm["header_map"]["NAME"])
    qacc = " ".join(sub_hmm["header_map"]["ACC"])
    qlen = sub_hmm["M"]
    prev_score = None
    per_target = {}
    for i, row in enumerate(rows):
        if row[3] != qname:
            msgs.append("row %d: query name %r != profile NAME %r" % (i + 1, row[3], qname))
        if qacc and row[4] != qacc:
            msgs.append("row %d: query accession %r != profile ACC %r" % (i + 1, row[4], qacc))
        if row_int(rows, i, 5, "query length") != qlen:
            msgs.append("row %d: query length does not equal the profile LENG" % (i + 1))
        tlen = row_int(rows, i, 2, "target length")
        try:
            hf, ht = row_int(rows, i, 15, "hmm from"), row_int(rows, i, 16, "hmm to")
            af, at = row_int(rows, i, 17, "ali from"), row_int(rows, i, 18, "ali to")
            ef, et = row_int(rows, i, 19, "env from"), row_int(rows, i, 20, "env to")
        except CheckFailure as exc:
            msgs.append(str(exc))
            continue
        if not (1 <= hf <= ht <= qlen):
            msgs.append("row %d: hmm coordinates outside 1..profile length" % (i + 1))
        if not (1 <= af <= at <= tlen):
            msgs.append("row %d: alignment coordinates outside 1..target length" % (i + 1))
        if not (1 <= ef <= et <= tlen):
            msgs.append("row %d: envelope coordinates outside 1..target length" % (i + 1))
        if row_float(rows, i, 6, "full-sequence E-value") > 10.0 + 1e-9:
            msgs.append("row %d: reported full-sequence E-value exceeds the "
                        "reporting threshold 10" % (i + 1))
        score = row_float(rows, i, 7, "full-sequence bit score")
        if prev_score is not None and score > prev_score + 1e-6:
            msgs.append("row %d: full-sequence bit score increases, breaking "
                        "rank ordering" % (i + 1))
        prev_score = score if prev_score is None else max(prev_score, score)
        dom = row_int(rows, i, 9, "domain number")
        total = row_int(rows, i, 10, "total domains")
        per_target.setdefault(row[0], []).append((dom, total))
    for target, pairs in per_target.items():
        totals = set(t for _, t in pairs)
        nums = sorted(d for d, _ in pairs)
        if len(totals) != 1:
            msgs.append("target %r: inconsistent total domain counts" % target)
        elif nums != list(range(1, totals.pop() + 1)):
            msgs.append("target %r: domain numbers are not 1..n in rank order" % target)
    if msgs:
        return False, "; ".join(msgs[:5])
    return True, "domain table is consistent with the submitted profile"


# ----------------------------------------------------------------------------
# reference loading (cached per run)
# ----------------------------------------------------------------------------

_REF_CACHE = {}


def _read_reference_hmm(ref_dir):
    key = ("hmm", ref_dir)
    if key not in _REF_CACHE:
        _REF_CACHE[key] = parse_hmm_file(os.path.join(ref_dir, HMM_PATH))
    return _REF_CACHE[key]


def _read_reference_domtbl(ref_dir):
    key = ("domtbl", ref_dir)
    if key not in _REF_CACHE:
        _REF_CACHE[key] = parse_domtbl_file(os.path.join(ref_dir, DOMTBL_PATH))
    return _REF_CACHE[key]


# ----------------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    results = []
    for check in CHECKS:
        try:
            passed, message = check["fn"](args.reference_dir, args.submission_dir)
        except CheckFailure as exc:
            passed, message = False, str(exc)
        except Exception as exc:  # defensive: never crash the grader
            passed, message = False, "grader error in %s: %s" % (type(exc).__name__, exc)
        results.append({"id": check["id"], "passed": bool(passed),
                        "message": str(message)[:1500]})

    report = {"passed": all(r["passed"] for r in results), "checks": results}
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

