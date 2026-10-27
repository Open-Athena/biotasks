#!/usr/bin/env python
"""Acceptance grader for the AdK RMSD task.

Usage: python grade.py --reference-dir PATH --submission-dir PATH --report PATH
"""
import argparse
import csv
import json
import math
import os

# Numeric acceptance limits (public): an RMSD value x is accepted against the
# reference value r when |x - r| <= ATOL + RTOL * |r|.
RTOL = 1e-6
ATOL = 1e-6
# time_ps convention tolerance (absolute, in ps): covers both the DCD-reader
# reported time and the (frame + 1) ps convention.
TIME_ATOL = 1e-4

CSV_SPECS = {
    'backbone_domain_rmsd.csv': [
        'frame', 'time_ps', 'backbone_rmsd_angstrom',
        'core_rmsd_angstrom', 'lid_rmsd_angstrom', 'nmp_rmsd_angstrom'],
    'ca_core_rmsd.csv': ['frame', 'time_ps', 'ca_core_rmsd_angstrom'],
    'mass_weighted_rmsd.csv': [
        'frame', 'time_ps', 'ca_mass_weighted_rmsd_angstrom',
        'core_rmsd_angstrom', 'lid_rmsd_angstrom', 'nmp_rmsd_angstrom'],
    'resid_weighted_rmsd.csv': [
        'frame', 'time_ps', 'ca_resid_weighted_rmsd_angstrom',
        'core_rmsd_angstrom', 'lid_rmsd_angstrom', 'nmp_rmsd_angstrom'],
}
ALL_CSV = ['backbone_domain_rmsd.csv', 'ca_core_rmsd.csv',
           'mass_weighted_rmsd.csv', 'resid_weighted_rmsd.csv']
JSON_PATH = 'open_closed_backbone_rmsd.json'

# Declared check inventory: id -> (kind, covered artifacts).
CHECK_META = {
    'csv_schema': ('structural', ALL_CSV),
    'json_schema': ('structural', [JSON_PATH]),
    'time_ps': ('scientific', ALL_CSV),
    'analysis_a_open_closed_rmsd': ('scientific', [JSON_PATH]),
    'analysis_b_backbone_domain_rmsd': ('scientific',
                                        ['backbone_domain_rmsd.csv']),
    'analysis_c_ca_core_rmsd': ('scientific', ['ca_core_rmsd.csv']),
    'analysis_d_mass_weighted_rmsd': ('scientific',
                                      ['mass_weighted_rmsd.csv']),
    'analysis_e_resid_weighted_rmsd': ('scientific',
                                       ['resid_weighted_rmsd.csv']),
}


def load_csv(path, expected_header):
    """Parse a required CSV. Returns (table, error) with table None on error.

    table is a list of rows; each row is a list of token strings
    (already length-validated against the header).
    """
    if not os.path.isfile(path):
        return None, 'file missing'
    try:
        with open(path, newline='', encoding='utf-8') as fh:
            rows = list(csv.reader(fh))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return None, 'unreadable or malformed CSV: %s' % exc
    if not rows:
        return None, 'file is empty (no header row)'
    if rows[0] != expected_header:
        return None, 'header mismatch: expected %r, got %r' % (
            expected_header, rows[0])
    data = rows[1:]
    ncol = len(expected_header)
    for i, row in enumerate(data):
        if len(row) != ncol:
            return None, 'data row %d has %d fields, expected %d' % (
                i, len(row), ncol)
        for j, tok in enumerate(row):
            if tok == '':
                return None, 'data row %d has an empty field (column %s)' % (
                    i, expected_header[j])
    return data, None


def to_float(tok):
    try:
        return float(tok)
    except (TypeError, ValueError):
        return None


def value_ok(x, ref):
    return x is not None and math.isfinite(x) and x >= 0.0 and \
        abs(x - ref) <= ATOL + RTOL * abs(ref)


def parse_frame_rows(table, ncols):
    """Validate frame ordering and numeric content.

    Returns (frames, numeric_rows, error). frames is the list of frame
    indices; numeric_rows is a list of per-row float lists (None where a
    token did not parse as a finite number).
    """
    frames = []
    numeric_rows = []
    for i, row in enumerate(table):
        fv = to_float(row[0])
        if fv is None or not math.isfinite(fv) or fv != int(fv) or \
                int(fv) != i:
            return None, None, 'row %d frame column must be the integer ' \
                'frame index %d, got %r' % (i, i, row[0])
        frames.append(int(fv))
        vals = [to_float(tok) for tok in row[1:ncols]]
        for v in vals:
            if v is None or not math.isfinite(v):
                return None, None, 'row %d contains a non-numeric or ' \
                    'non-finite value' % i
        numeric_rows.append(vals)
    return frames, numeric_rows, None


def check_csv_content(sub_path, ref_path, spec, ncols):
    """Shared CSV comparison. Returns (rows_ok, message)."""
    sub_tab, err = load_csv(sub_path, spec['header'])
    if err:
        return False, '%s: %s' % (spec['name'], err)
    if len(sub_tab) != spec['nrows']:
        return False, '%s: expected %d data rows, found %d' % (
            spec['name'], spec['nrows'], len(sub_tab))
    sub_frames, sub_vals, err = parse_frame_rows(sub_tab, ncols)
    if err:
        return False, '%s: %s' % (spec['name'], err)
    if sub_frames != list(range(spec['nrows'])):
        return False, '%s: frame indices are not 0..%d in order' % (
            spec['name'], spec['nrows'] - 1)
    ref_tab, ref_err = load_csv(ref_path, spec['header'])
    if ref_err:
        return False, '%s: reference unreadable (%s)' % (spec['name'],
                                                          ref_err)
    ref_frames, ref_vals, ref_err2 = parse_frame_rows(ref_tab, ncols)
    if ref_err2 or ref_frames != list(range(spec['nrows'])):
        return False, '%s: reference malformed' % spec['name']
    for i in range(spec['nrows']):
        for j in range(ncols - 1):
            x = sub_vals[i][j]
            r = ref_vals[i][j]
            if not value_ok(x, r):
                return False, '%s: row %d column %s: submitted value %r ' \
                    'not within tolerance of reference' % (
                        spec['name'], i, spec['header'][j + 1], x)
    return True, '%s: %d rows match within tolerance' % (spec['name'],
                                                          spec['nrows'])


def check_json_value(ref_dir, sub_dir):
    sub_doc = None
    try:
        with open(os.path.join(sub_dir, JSON_PATH), encoding='utf-8') as fh:
            sub_doc = json.load(fh)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return False, 'missing or unreadable JSON: %s' % exc
    try:
        with open(os.path.join(ref_dir, JSON_PATH), encoding='utf-8') as fh:
            ref_doc = json.load(fh)
    except (OSError, UnicodeDecodeError, ValueError):
        return False, 'reference unreadable'
    if not isinstance(sub_doc, dict) or set(sub_doc.keys()) != \
            {'value', 'unit'}:
        return False, 'JSON object must contain exactly "value" and "unit"'
    if sub_doc.get('unit') != 'angstrom':
        return False, '"unit" must be "angstrom"'
    xv = sub_doc.get('value')
    if isinstance(xv, bool) or not isinstance(xv, (int, float)) or \
            not math.isfinite(xv) or xv < 0:
        return False, '"value" must be a finite non-negative number'
    if not value_ok(float(xv), float(ref_doc['value'])):
        return False, 'value %r not within tolerance of the reference' % xv
    return True, 'open-vs-closed backbone RMSD value matches within tolerance'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reference-dir', required=True)
    ap.add_argument('--submission-dir', required=True)
    ap.add_argument('--report', required=True)
    args = ap.parse_args()

    # (kind, artifacts, passed, message) per declared check, keyed by id.
    results = {}

    # ------------------------------------------------------------------
    # 1. structural: CSV schema / row integrity for all four CSV outputs
    # ------------------------------------------------------------------
    struct_msgs = []
    n_frames = None
    tables = {}
    for name in ALL_CSV:
        sub_path = os.path.join(args.submission_dir, name)
        ref_path = os.path.join(args.reference_dir, name)
        header = CSV_SPECS[name]
        sub_tab, err = load_csv(sub_path, header)
        if err:
            struct_msgs.append('%s: %s' % (name, err))
            tables[name] = None
            continue
        ref_tab, ref_err = load_csv(ref_path, header)
        if ref_err:
            struct_msgs.append('%s: reference unreadable (%s)' % (name,
                                                                  ref_err))
            tables[name] = None
            continue
        if n_frames is None:
            n_frames = len(ref_tab)
        if len(sub_tab) != n_frames:
            struct_msgs.append('%s: expected %d data rows, found %d' % (
                name, n_frames, len(sub_tab)))
            tables[name] = None
            continue
        ok_rows = True
        for i, row in enumerate(sub_tab):
            fv = to_float(row[0])
            if fv is None or not math.isfinite(fv) or fv != int(fv) or \
                    int(fv) != i:
                ok_rows = False
                break
            for tok in row[1:]:
                v = to_float(tok)
                if v is None or not math.isfinite(v):
                    ok_rows = False
                    break
            if not ok_rows:
                break
        if not ok_rows:
            struct_msgs.append('%s: frame column must be the ordered 0-based'
                               ' frame index and all values numeric/finite'
                               % name)
            tables[name] = None
        else:
            tables[name] = sub_tab
    if struct_msgs:
        results['csv_schema'] = (False, '; '.join(struct_msgs))
    else:
        results['csv_schema'] = (
            True,
            'all four CSV outputs have the exact required headers, one '
            'data row per trajectory frame in frame order, and no '
            'malformed, ragged, empty, duplicate or non-finite entries')

    # ------------------------------------------------------------------
    # 2. structural: JSON schema for the single-value endpoint
    # ------------------------------------------------------------------
    json_path = os.path.join(args.submission_dir, JSON_PATH)
    json_doc = None
    json_err = None
    if not os.path.isfile(json_path):
        json_err = 'file missing'
    else:
        try:
            with open(json_path, encoding='utf-8') as fh:
                json_doc = json.load(fh)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            json_err = 'unreadable or malformed JSON: %s' % exc
    if json_err is not None:
        results['json_schema'] = (False, json_err)
    elif not isinstance(json_doc, dict):
        results['json_schema'] = (False,
                                  'top-level value is not a JSON object')
    elif set(json_doc.keys()) != {'value', 'unit'}:
        results['json_schema'] = (
            False,
            'JSON object must contain exactly the keys "value" and '
            '"unit"; found keys %r' % sorted(json_doc.keys()))
    elif not isinstance(json_doc['unit'], str) or \
            json_doc['unit'] != 'angstrom':
        results['json_schema'] = (False,
                                  '"unit" must be the string "angstrom"')
    elif isinstance(json_doc['value'], bool) or \
            not isinstance(json_doc['value'], (int, float)) or \
            not math.isfinite(json_doc['value']) or \
            json_doc['value'] < 0:
        results['json_schema'] = (False,
                                  '"value" must be a finite non-negative '
                                  'number')
    else:
        results['json_schema'] = (
            True,
            'JSON object has exactly the required keys, unit "angstrom" '
            'and a finite non-negative numeric value')

    # ------------------------------------------------------------------
    # 3. time_ps convention across all four CSVs (scientific)
    # ------------------------------------------------------------------
    time_msgs = []
    for name in ALL_CSV:
        sub_tab = tables.get(name)
        ref_path = os.path.join(args.reference_dir, name)
        ref_tab, ref_err = load_csv(ref_path, CSV_SPECS[name])
        if sub_tab is None:
            time_msgs.append('%s: table unavailable' % name)
            continue
        if ref_err:
            time_msgs.append('%s: reference unreadable' % name)
            continue
        for i, (srow, rrow) in enumerate(zip(sub_tab, ref_tab)):
            t_sub = to_float(srow[1])
            t_ref = to_float(rrow[1])
            if t_sub is None or not math.isfinite(t_sub):
                time_msgs.append('%s row %d: time_ps not numeric/finite'
                                 % (name, i))
                continue
            ok_ref = abs(t_sub - t_ref) <= TIME_ATOL
            ok_conv = abs(t_sub - (i + 1)) <= TIME_ATOL
            if not (ok_ref or ok_conv):
                time_msgs.append('%s row %d: time_ps %r not within %g ps of '
                                 'the reference time or the (frame+1) ps '
                                 'convention' % (name, i, t_sub, TIME_ATOL))
    if time_msgs:
        results['time_ps'] = (False, '; '.join(time_msgs[:5]))
    else:
        results['time_ps'] = (
            True,
            'every time_ps value matches the reference within the stated '
            'tolerance (the (frame+1) ps convention is accepted)')

    # ------------------------------------------------------------------
    # 4-8. scientific: per-analysis RMSD column comparisons
    # ------------------------------------------------------------------
    if n_frames is None:
        n_frames = 0
    results['analysis_a_open_closed_rmsd'] = check_json_value(
        args.reference_dir, args.submission_dir)
    for cid, name in [
            ('analysis_b_backbone_domain_rmsd', 'backbone_domain_rmsd.csv'),
            ('analysis_c_ca_core_rmsd', 'ca_core_rmsd.csv'),
            ('analysis_d_mass_weighted_rmsd', 'mass_weighted_rmsd.csv'),
            ('analysis_e_resid_weighted_rmsd', 'resid_weighted_rmsd.csv')]:
        ncols = len(CSV_SPECS[name])
        spec = {'name': name, 'header': CSV_SPECS[name],
                'nrows': n_frames}
        results[cid] = check_csv_content(
            os.path.join(args.submission_dir, name),
            os.path.join(args.reference_dir, name), spec, ncols)

    # ------------------------------------------------------------------
    # Emit the report: each check exactly once, with exactly the keys
    # id / passed / message, in the declared inventory order.
    # ------------------------------------------------------------------
    checks = []
    for cid in CHECK_META:
        passed, msg = results[cid]
        checks.append({'id': cid, 'passed': bool(passed), 'message': msg})
    report = {'passed': all(c['passed'] for c in checks),
              'checks': checks}
    with open(args.report, 'w', encoding='utf-8') as fh:
        json.dump(report, fh)
        fh.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

