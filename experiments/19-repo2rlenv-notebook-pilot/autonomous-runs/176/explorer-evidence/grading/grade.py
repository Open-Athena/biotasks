#!/usr/bin/env python3
"""Acceptance grader: HRV indices for a 5-minute resting ECG recording.

Compares the four declared CSV outputs (hrv_time.csv, hrv_freq.csv,
hrv_nonlinear.csv, hrv_indices.csv) between a reference directory and a
submission directory, on parsed scientific content (not bytes):

  * each file at its declared path, relative to the given root;
  * CSV format: header row + exactly one data row, unique header names;
  * exact column-name sets per file (no missing, no extra, no index column);
  * empty fields exactly where the reference is undefined;
  * numeric agreement |s - r| <= 1e-9 + 1e-9 * |r| with reference value r;
  * nonnumeric, nonfinite, or malformed content fails;
  * cross-file: hrv_indices.csv is the column union of the three domain
    files, with matching values.
"""
import argparse
import csv
import json
import math
import os

FILES = ["hrv_time.csv", "hrv_freq.csv", "hrv_nonlinear.csv", "hrv_indices.csv"]
DOMAINS = ["hrv_time.csv", "hrv_freq.csv", "hrv_nonlinear.csv"]
ABS_TOL = 1e-9
REL_TOL = 1e-9
MAX_EXAMPLES = 8


class ParseError(Exception):
    pass


def parse_table(path):
    if not os.path.isfile(path):
        raise ParseError("file not found")
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
    except Exception as exc:  # unreadable / not valid UTF-8 / broken CSV
        raise ParseError("not readable as UTF-8 CSV (%s)" % exc)
    if not rows:
        raise ParseError("no header row")
    if len(rows) != 2:
        raise ParseError("expected header plus exactly one data row, found %d "
                          "CSV records" % len(rows))
    header = list(rows[0])
    data = rows[1]
    if not header or any(h.strip() == "" for h in header):
        raise ParseError("empty header name")
    if len(set(header)) != len(header):
        raise ParseError("duplicate header names")
    if len(data) != len(header):
        raise ParseError("data row has %d fields but header has %d"
                         % (len(data), len(header)))
    values = []
    for i, tok in enumerate(data):
        t = tok.strip()
        if t == "":
            values.append(None)  # undefined index: empty field
            continue
        try:
            v = float(t)
        except ValueError:
            raise ParseError("field '%s' is not numeric" % header[i])
        if not math.isfinite(v):
            raise ParseError("field '%s' is not finite" % header[i])
        values.append(v)
    return header, values


def load_csv(root, name):
    path = os.path.join(root, name)
    try:
        header, values = parse_table(path)
    except ParseError as exc:
        return {"ok": False, "error": "%s: %s" % (name, exc)}
    return {"ok": True, "name": name, "header": header,
            "map": dict(zip(header, values))}


def values_agree(s, r):
    """Submission value s vs reference value r (None = empty field)."""
    if s is None or r is None:
        return s is None and r is None
    return abs(s - r) <= ABS_TOL + REL_TOL * abs(r)


def fmt_names(names):
    names = sorted(names)
    if not names:
        return "none"
    shown = ", ".join(names[:MAX_EXAMPLES])
    if len(names) > MAX_EXAMPLES:
        shown += ", ... (total %d)" % len(names)
    return shown


def compare_file(sub_rec, ref_rec):
    if not ref_rec["ok"]:
        return False, ("reference artifact could not be read (%s)"
                      % ref_rec["error"])
    if not sub_rec["ok"]:
        return False, sub_rec["error"]
    ref_map = ref_rec["map"]
    sub_map = sub_rec["map"]
    missing = set(ref_map) - set(sub_map)
    extra = set(sub_map) - set(ref_map)
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing index columns: %s" % fmt_names(missing))
        if extra:
            parts.append("unexpected index columns: %s" % fmt_names(extra))
        parts.append("the column set must match the reference index names "
                     "exactly")
        return False, "; ".join(parts)
    bad = []
    for name in ref_map:
        r = ref_map[name]
        s = sub_map[name]
        if r is None:
            if s is None:
                continue
            bad.append("%s must be an empty field (undefined index)" % name)
        elif s is None:
            bad.append("%s is empty but must report a value" % name)
        else:
            d = abs(s - r)
            if d > ABS_TOL + REL_TOL * abs(r):
                bad.append("%s deviates by %.3e (tolerance %.3e)"
                           % (name, d, ABS_TOL + REL_TOL * abs(r)))
        if len(bad) >= MAX_EXAMPLES:
            break
    if bad:
        return False, ("%d mismatching column(s): %s"
                       % (len(bad), "; ".join(bad)))
    n_empty = sum(1 for v in ref_map.values() if v is None)
    return True, ("all %d value column(s) and %d undefined/empty column(s) "
                  "match within |s-r| <= %.0e + %.0e*|r|"
                  % (len(ref_map) - n_empty, n_empty, ABS_TOL, REL_TOL))


def combined_consistency(sub):
    for name in FILES:
        if not sub[name]["ok"]:
            return False, sub[name]["error"]
    union = {}
    for dn in DOMAINS:
        for k, v in sub[dn]["map"].items():
            if k in union and not values_agree(union[k], v):
                return False, ("the domain files disagree with each other on "
                               "column %s" % k)
            union[k] = v
    idx = sub["hrv_indices.csv"]["map"]
    missing = set(union) - set(idx)
    extra = set(idx) - set(union)
    if missing or extra:
        parts = []
        if missing:
            parts.append("combined table lacks: %s" % fmt_names(missing))
        if extra:
            parts.append("combined table has extra: %s" % fmt_names(extra))
        parts.append("the combined table must contain exactly the index "
                     "columns of the three domain files")
        return False, "; ".join(parts)
    bad = []
    for name in sorted(union):
        if not values_agree(idx.get(name), union[name]):
            r = union[name]
            if r is None or idx.get(name) is None:
                bad.append("%s: empty/value mismatch between domain file and "
                           "combined table" % name)
            else:
                bad.append("%s: combined value deviates from the domain file "
                           "by %.3e" % (name, abs(idx[name] - r)))
        if len(bad) >= MAX_EXAMPLES:
            break
    if bad:
        return False, ("%d mismatching column(s): %s"
                       % (len(bad), "; ".join(bad)))
    return True, ("combined table contains exactly the union of the %d domain "
                  "index columns with matching values and empty-field "
                  "statuses" % len(union))


CHECK_IDS = ["structure", "hrv_time_values", "hrv_freq_values",
             "hrv_nonlinear_values", "hrv_indices_values",
             "combined_consistency"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True)
    parser.add_argument("--submission-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    results = {cid: (False, "check not evaluated") for cid in CHECK_IDS}

    def run(cid, fn):
        try:
            results[cid] = fn()
        except Exception as exc:  # a malformed submission never crashes grading
            results[cid] = (False, "evaluation error: %r" % (exc,))

    sub = {n: load_csv(args.submission_dir, n) for n in FILES}
    ref = {n: load_csv(args.reference_dir, n) for n in FILES}

    def structure():
        bad = [sub[n]["error"] for n in FILES if not sub[n]["ok"]]
        if bad:
            return False, "; ".join(bad)
        desc = ", ".join("%s: %d columns" % (n, len(sub[n]["header"]))
                         for n in sorted(FILES))
        return True, ("all four files are readable single-row CSVs with "
                      "unique non-empty header names and finite-or-empty "
                      "numeric fields (%s)" % desc)

    run("structure", structure)
    for cid, fname in [("hrv_time_values", "hrv_time.csv"),
                       ("hrv_freq_values", "hrv_freq.csv"),
                       ("hrv_nonlinear_values", "hrv_nonlinear.csv"),
                       ("hrv_indices_values", "hrv_indices.csv")]:
        run(cid, (lambda f=fname: compare_file(sub[f], ref[f])))
    run("combined_consistency", lambda: combined_consistency(sub))

    checks = []
    for cid in CHECK_IDS:
        ok, msg = results[cid]
        checks.append({"id": cid, "passed": bool(ok), "message": msg})
    report = {"passed": all(c["passed"] for c in checks), "checks": checks}
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

