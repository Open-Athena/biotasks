#!/usr/bin/env python3
"""Acceptance grader for the LuxC profile-HMM build + database-search task.

Checks (all read values dynamically from the reference directory):
  hmm_ascii_format   -- LuxC.hmm is a single, parseable HMMER3/f ASCII model
                        with no extra content beyond provenance lines.
  hmm_model_content  -- the decoded Plan7 model equals the reference model
                        (canonical re-serialization compared exactly).
  domtbl_table_format-- LuxC.domtbl has the canonical hmmsearch --domtblout
                        preamble and 22-field rows.
  domtbl_hit_rows    -- row-by-row (canonical rank order) equality of the
                        domain hit table, with E-values within a stated
                        relative tolerance and all other columns exact.
"""
import argparse
import io
import json
import math
import os
import sys

HMM_PATH = "LuxC.hmm"
DOMTBL_PATH = "LuxC.domtbl"
EVALUE_REL_TOL = 0.10  # relative to the reference value

TRUSTED_INPUT_DIR_ENV = "BIOTASKS_TRUSTED_INPUT_DIR"
TRUSTED_MSA = os.path.join("data", "msa", "LuxC.sto")
TRUSTED_FAA = os.path.join("data", "seqs", "LuxC.faa")

# domtblout column indices (0-based, after split(None, 22)):
# 0 target,1 acc,2 tlen,3 qname,4 qacc,5 qlen,6 E-value,7 score,8 bias,
# 9 dom#,10 of,11 c-Evalue,12 i-Evalue,13 dom score,14 dom bias,
# 15 hmm from,16 hmm to,17 ali from,18 ali to,19 env from,20 env to,
# 21 acc, 22 description
STR_IDX = (0, 1, 3, 4)
INT_IDX = (2, 5, 9, 10, 15, 16, 17, 18, 19, 20)
FLOAT_EXACT_IDX = (7, 8, 13, 14, 21)
EVALUE_IDX = (6, 11, 12)


def to_text(data):
    return data.decode("utf-8")


def read_file(path):
    with open(path, "rb") as fh:
        return fh.read()


# ---------------------------------------------------------------- HMM helpers

def parse_hmm_bytes(data):
    from pyhmmer.plan7 import HMMFile

    hmm_file = HMMFile(io.BytesIO(data))
    try:
        hmm = hmm_file.read()
        extra = hmm_file.read()
    finally:
        hmm_file.close()
    return hmm, extra


def canonical_hmm(hmm):
    """Canonical (writer-normalized) form: (banner line, body lines).

    The native HMMER3 writer re-serializes the decoded model; its DATE and
    COM provenance lines carry no scientific content and are excluded.
    """
    buf = io.BytesIO()
    hmm.write(buf)
    lines = to_text(buf.getvalue()).splitlines()
    banner = lines[0]
    body = [l for l in lines[1:]
            if not (l.startswith("DATE ") or l.startswith("COM "))]
    return banner, body


def nonprovenance_lines(text):
    lines = text.splitlines()
    rest = lines[1:]
    return [l for l in rest
            if not (l.startswith("DATE ") or l.startswith("COM "))]


def hmm_str(value):
    if isinstance(value, bytes):
        return value.decode()
    return value


def stockholm_id_ac(text):
    msa_id = None
    msa_ac = None
    for line in text.splitlines():
        if line.startswith("#=GF ID"):
            parts = line.split()
            if len(parts) >= 3:
                msa_id = parts[2]
        elif line.startswith("#=GF AC"):
            parts = line.split()
            if len(parts) >= 3:
                msa_ac = parts[2]
    return msa_id, msa_ac


def check_hmm_format(sub_bytes):
    """Structural: single parseable HMMER3/f model, no extra content."""
    try:
        text = to_text(sub_bytes)
    except UnicodeDecodeError as exc:
        return False, "file is not decodable text: %s" % exc, None
    lines = text.splitlines()
    if not lines or not lines[0].startswith("HMMER3/f"):
        return False, "first line is not a HMMER3/f format declaration", None
    try:
        hmm, extra = parse_hmm_bytes(sub_bytes)
    except Exception as exc:  # parser refusal of malformed content
        return False, "native HMMER3 reader rejected the file (%s: %s)" % (
            type(exc).__name__, exc), None
    if hmm is None:
        return False, "native HMMER3 reader found no model", None
    if extra is not None:
        return False, "file contains more than one HMM model", hmm
    try:
        banner, canon = canonical_hmm(hmm)
    except Exception as exc:
        return False, ("parsed model could not be re-serialized (%s: %s)" %
                       (type(exc).__name__, exc)), hmm
    sub_body = nonprovenance_lines(text)
    if len(sub_body) != len(canon):
        return False, ("file has %d non-provenance lines but the parsed "
                       "model canonically serializes to %d") % (
            len(sub_body), len(canon)), hmm
    sub_tokens = [len(l.split()) for l in sub_body]
    canon_tokens = [len(l.split()) for l in canon]
    if sub_tokens != canon_tokens:
        return False, ("non-provenance line structure does not match the "
                       "parsed model (unexpected, extra or missing "
                       "content)"), hmm
    return True, ("single HMMER3/f model; content outside the banner/DATE/COM "
                  "provenance lines matches the decoded model structure"), hmm


def check_hmm_content(sub_hmm, ref_hmm, trusted_dir):
    """Scientific: decoded Plan7 model equals the reference model."""
    try:
        _, sub_canon = canonical_hmm(sub_hmm)
        _, ref_canon = canonical_hmm(ref_hmm)
    except Exception as exc:
        return False, "could not canonicalize model (%s: %s)" % (
            type(exc).__name__, exc)
    if sub_canon != ref_canon:
        # locate first mismatch for the message only
        detail = "model body differs from reference"
        for i, (a, b) in enumerate(zip(ref_canon, sub_canon)):
            if a != b:
                detail = ("model body differs from reference (first "
                          "difference at body line %d)" % (i + 1))
                break
        if len(ref_canon) != len(sub_canon):
            detail += "; canonical line counts %d vs %d" % (
                len(ref_canon), len(sub_canon))
        return False, detail
    if trusted_dir is not None:
        try:
            sto = to_text(read_file(os.path.join(trusted_dir, TRUSTED_MSA)))
        except OSError as exc:
            return False, "cannot read trusted Stockholm input: %s" % exc
        msa_id, msa_ac = stockholm_id_ac(sto)
        name = hmm_str(sub_hmm.name)
        acc = hmm_str(sub_hmm.accession)
        if msa_id is not None and name != msa_id:
            return False, ("model NAME %r does not match the alignment name "
                           "%r" % (name, msa_id))
        if msa_ac is not None and acc != msa_ac:
            return False, ("model ACC %r does not match the alignment "
                           "accession %r" % (acc, msa_ac))
    return True, ("decoded Plan7 model matches the reference exactly "
                  "(NAME/ACC/DESC, architecture flags, NSEQ/EFFN/CKSUM, "
                  "GA/TC/NC cutoffs, STATS calibration and all per-position "
                  "emission/transition parameters)")


# ------------------------------------------------------------- domtbl helpers

def parse_domtbl(data):
    text = to_text(data)
    lines = text.splitlines()
    preamble = []
    rows = []
    in_body = False
    for line in lines:
        if line.startswith("#"):
            if in_body:
                raise ValueError("comment line after the data rows")
            preamble.append(line)
        else:
            in_body = True
            rows.append(line)
    return preamble, rows


def split_row(row):
    parts = row.split(None, 22)
    if len(parts) < 22:
        raise ValueError("row does not have the 22 fixed domtblout fields: %r"
                         % row[:80])
    return parts


def parse_row_typed(row):
    """Parse a row into typed values; raises on malformed content."""
    parts = split_row(row)
    vals = {}
    for j in INT_IDX:
        vals[j] = int(parts[j])
    for j in FLOAT_EXACT_IDX:
        v = float(parts[j])
        if not math.isfinite(v):
            raise ValueError("nonfinite value in column %d" % (j + 1))
        vals[j] = v
    for j in EVALUE_IDX:
        v = float(parts[j])
        if not math.isfinite(v):
            raise ValueError("nonfinite E-value in column %d" % (j + 1))
        if v < 0:
            raise ValueError("negative E-value in column %d" % (j + 1))
        vals[j] = v
    return parts, vals


def parse_fasta_records(text):
    records = {}
    duplicates = set()
    name = None
    desc = None
    length = 0
    for line in text.splitlines():
        if line.startswith(">"):
            if name is not None and name not in duplicates:
                records[name] = (name, desc, length)
            header = line[1:].strip()
            toks = header.split(None, 1)
            name = toks[0] if toks else ""
            desc = toks[1] if len(toks) > 1 else ""
            length = 0
            if name in records or name in duplicates:
                duplicates.add(name)
        elif name is not None:
            length += len(line.strip())
    if name is not None and name not in duplicates:
        records[name] = (name, desc, length)
    return records


def check_domtbl_format(sub_bytes, ref_bytes):
    """Structural: canonical preamble and 22-field domtblout rows."""
    try:
        sub_pre, sub_rows = parse_domtbl(sub_bytes)
        ref_pre, _ = parse_domtbl(ref_bytes)
    except UnicodeDecodeError as exc:
        return False, "file is not decodable text: %s" % exc, None
    except ValueError as exc:
        return False, str(exc), None
    if sub_pre != ref_pre:
        return False, ("'#'-comment preamble does not match the canonical "
                       "hmmsearch --domtblout preamble (or comment lines "
                       "appear after the data rows)"), None
    for row in sub_rows:
        if row.strip() == "":
            return False, "blank data row present", None
        try:
            parse_row_typed(row)
        except (ValueError, IndexError) as exc:
            return False, "malformed data row (%s)" % exc, None
    return True, ("%d data rows with the canonical 22-field --domtblout "
                  "layout after the comment preamble" % len(sub_rows)), sub_rows


def check_domtbl_hits(sub_rows, ref_bytes, trusted_dir):
    """Scientific: row-by-row rank-ordered equality with the reference."""
    try:
        _, ref_rows = parse_domtbl(ref_bytes)
    except (UnicodeDecodeError, ValueError) as exc:
        return False, "reference domain table unreadable: %s" % exc
    if len(sub_rows) != len(ref_rows):
        return False, ("reported %d domain hit rows, reference reports %d" %
                       (len(sub_rows), len(ref_rows)))
    ref_typed = [parse_row_typed(r) for r in ref_rows]
    grounding = None
    if trusted_dir is not None:
        try:
            faa = to_text(read_file(os.path.join(trusted_dir, TRUSTED_FAA)))
            grounding = parse_fasta_records(faa)
        except OSError as exc:
            return False, "cannot read trusted FASTA input: %s" % exc
    for i, (sub_row, (ref_parts, ref_vals)) in enumerate(zip(sub_rows, ref_typed)):
        try:
            sub_parts, sub_vals = parse_row_typed(sub_row)
        except (ValueError, IndexError) as exc:
            return False, "row %d malformed (%s)" % (i + 1, exc)
        label = "rank %d" % (i + 1)
        # identity columns
        for j in STR_IDX:
            if sub_parts[j] != ref_parts[j]:
                return False, ("%s: column %d (%s) is %r, reference has %r" %
                               (label, j + 1,
                                ("target name", "accession", "query name",
                                 "query accession")[STR_IDX.index(j)],
                                sub_parts[j], ref_parts[j]))
        for j in INT_IDX:
            if sub_vals[j] != ref_vals[j]:
                return False, ("%s: column %d is %d, reference has %d" %
                               (label, j + 1, sub_vals[j], ref_vals[j]))
        for j in FLOAT_EXACT_IDX:
            if sub_vals[j] != ref_vals[j]:
                return False, ("%s: numeric column %d is %r, reference has %r" %
                               (label, j + 1, sub_vals[j], ref_vals[j]))
        for j in EVALUE_IDX:
            r = ref_vals[j]
            s = sub_vals[j]
            if r == 0.0:
                if s != 0.0:
                    return False, ("%s: E-value column %d is %r, reference "
                                  "has 0" % (label, j + 1, s))
            else:
                if abs(s - r) > EVALUE_REL_TOL * r:
                    return False, ("%s: E-value column %d is %r, reference "
                                   "has %r (outside the %d%% relative "
                                   "tolerance)" % (label, j + 1, s, r,
                                                   int(EVALUE_REL_TOL * 100)))
        sub_desc = sub_parts[22] if len(sub_parts) > 22 else ""
        ref_desc = ref_parts[22] if len(ref_parts) > 22 else ""
        if sub_desc != ref_desc:
            return False, ("%s: description column is %r, reference has %r" %
                          (label, sub_desc[:60], ref_desc[:60]))
        if grounding is not None:
            target = sub_parts[0]
            if target not in grounding:
                return False, ("%s: target %r is not a record of the search "
                              "database FASTA" % (label, target))
            _, fdesc, flen = grounding[target]
            if sub_vals[2] != flen:
                return False, ("%s: tlen %d does not equal the FASTA sequence "
                               "length %d" % (label, sub_vals[2], flen))
            if sub_desc != fdesc:
                return False, ("%s: description does not equal the FASTA "
                               "header remainder %r" % (label, fdesc[:60]))
    return True, ("all %d domain hits match the reference in canonical rank "
                  "order (identity, lengths, domain index/count, coordinates, "
                  "scores, bias and accuracy exact; E-values within %d%% "
                  "relative; database-grounded target identities)" %
                  (len(sub_rows), int(EVALUE_REL_TOL * 100)))


# --------------------------------------------------------------------- driver

def write_report(path, results):
    passed = all(r[1] for r in results)
    payload = {"passed": passed,
               "checks": [{"id": cid, "passed": ok, "message": msg}
                          for cid, ok, msg in results]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args(argv)

    ref_hmm_path = os.path.join(args.reference_dir, HMM_PATH)
    ref_dom_path = os.path.join(args.reference_dir, DOMTBL_PATH)
    sub_hmm_path = os.path.join(args.submission_dir, HMM_PATH)
    sub_dom_path = os.path.join(args.submission_dir, DOMTBL_PATH)

    trusted_dir = os.environ.get(TRUSTED_INPUT_DIR_ENV)
    if trusted_dir is not None and not os.path.isdir(trusted_dir):
        trusted_dir = None

    results = []

    # ---- LuxC.hmm -------------------------------------------------------
    try:
        ref_hmm_bytes = read_file(ref_hmm_path)
        ref_hmm, _ = parse_hmm_bytes(ref_hmm_bytes)
    except Exception as exc:
        ref_hmm = None
        results.append(("hmm_model_content", False,
                        "reference HMM unreadable (%s: %s)" %
                        (type(exc).__name__, exc)))
    try:
        sub_hmm_bytes = read_file(sub_hmm_path)
    except OSError:
        sub_hmm_bytes = None

    if sub_hmm_bytes is None:
        results.append(("hmm_ascii_format", False,
                        "required output %s is missing or unreadable" %
                        HMM_PATH))
        results.append(("hmm_model_content", False,
                        "required output %s is missing; the profile HMM "
                        "cannot be compared" % HMM_PATH))
    else:
        ok, msg, sub_hmm = check_hmm_format(sub_hmm_bytes)
        results.append(("hmm_ascii_format", ok, msg))
        if sub_hmm is not None and ref_hmm is not None:
            ok2, msg2 = check_hmm_content(sub_hmm, ref_hmm, trusted_dir)
            results.append(("hmm_model_content", ok2, msg2))
        else:
            results.append(("hmm_model_content", False,
                            "the profile HMM could not be parsed for "
                            "content comparison"))

    # ---- LuxC.domtbl ----------------------------------------------------
    try:
        ref_dom_bytes = read_file(ref_dom_path)
    except OSError:
        ref_dom_bytes = None
    try:
        sub_dom_bytes = read_file(sub_dom_path)
    except OSError:
        sub_dom_bytes = None

    if sub_dom_bytes is not None and ref_dom_bytes is not None:
        ok, msg, sub_rows = check_domtbl_format(sub_dom_bytes, ref_dom_bytes)
        results.append(("domtbl_table_format", ok, msg))
        if sub_rows is not None:
            ok2, msg2 = check_domtbl_hits(sub_rows, ref_dom_bytes, trusted_dir)
            results.append(("domtbl_hit_rows", ok2, msg2))
        else:
            results.append(("domtbl_hit_rows", False,
                            "domain hit rows could not be parsed"))
    else:
        missing = (DOMTBL_PATH if sub_dom_bytes is None else
                   "reference " + DOMTBL_PATH)
        results.append(("domtbl_table_format", False,
                        "required output %s is missing or unreadable" %
                        missing))
        results.append(("domtbl_hit_rows", False,
                        "required output %s is missing or unreadable" %
                        missing))

    order = ["hmm_ascii_format", "hmm_model_content",
             "domtbl_table_format", "domtbl_hit_rows"]
    by_id = {}
    for cid, ok, msg in results:
        by_id.setdefault(cid, (ok, msg))
    final = [(cid,) + by_id[cid] for cid in order if cid in by_id]

    write_report(args.report, final)
    return 0


if __name__ == "__main__":
    sys.exit(main())

