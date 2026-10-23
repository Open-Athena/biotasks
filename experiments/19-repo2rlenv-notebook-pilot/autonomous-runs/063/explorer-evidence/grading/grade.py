#!/usr/bin/env python
"""Acceptance grader: RMSD analysis of the AdK closed->open transition.

Compares the five declared CSV endpoints between a reference directory and a
submission directory.  Frame-keyed files are joined on the Frame column; the
single-value endpoint is compared directly.  No submission code is executed.

Usage:
    python grade.py --reference-dir PATH --submission-dir PATH --report PATH
"""

import argparse
import csv
import json
import math
import os

TOL_ABS = 5e-6   # Angstrom, absolute allowance
TOL_REL = 1e-6   # fraction of the reference value magnitude

SINGLE_FILE = ('open_closed_backbone_rmsd.csv', ['Backbone'])
FRAME_FILES = [
    ('backbone_rmsd.csv', ['Backbone', 'CORE', 'LID', 'NMP']),
    ('ca_core_rmsd.csv', ['CORE']),
    ('mass_weighted_rmsd.csv', ['C-alphas', 'CORE', 'LID', 'NMP']),
    ('resid_weighted_rmsd.csv', ['C-alphas', 'CORE', 'LID', 'NMP']),
]

# declared emission order of the check ids
CHECK_ORDER = [
    'structural_schema',
    'analysis_a_open_closed',
    'analysis_b_backbone_groups',
    'analysis_c_ca_core',
    'analysis_d_mass_weighted',
    'analysis_e_resid_weighted',
]


def make_check(cid, passed, message):
    return {'id': cid, 'passed': bool(passed), 'message': message}


# ------------------------------------------------------------------ parsing
def read_csv_rows(path):
    """Return (header, data_rows); raise ValueError with a reason otherwise."""
    if not os.path.isfile(path):
        raise ValueError('file not found: %s' % path)
    try:
        with open(path, 'r', newline='', encoding='utf-8-sig') as fh:
            raw = [row for row in csv.reader(fh)]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ValueError('cannot read %s: %s' % (path, exc))
    rows = [r for r in raw if any((c or '').strip() != '' for c in r)]
    if not rows:
        raise ValueError('no header row in %s' % path)
    header = [c.strip() for c in rows[0]]
    data = rows[1:]
    for i, r in enumerate(data):
        if len(r) != len(header):
            raise ValueError('ragged row %d in %s: %d cells vs %d header cells'
                             % (i + 2, path, len(r), len(header)))
    return header, data


def parse_finite(text, label):
    s = (text or '').strip()
    if s == '':
        raise ValueError('%s is empty' % label)
    try:
        val = float(s)
    except ValueError:
        raise ValueError('%s is not a number: %r' % (label, s[:40]))
    if not math.isfinite(val):
        raise ValueError('%s is not a finite number: %r' % (label, s[:40]))
    return val


def _column_indices(header, value_cols, base, needs_frame):
    """Map required column name -> header position once per file."""
    errors = []
    idx = {}
    required = (['Frame'] if needs_frame else []) + list(value_cols)
    for col in required:
        positions = [i for i, h in enumerate(header) if h == col]
        if not positions:
            errors.append('%s: missing required column %r' % (base, col))
        elif len(positions) > 1:
            errors.append('%s: duplicate column %r' % (base, col))
        else:
            idx[col] = positions[0]
    return idx, errors


def parse_frame_table(path, value_cols):
    """Parse one frame-keyed table -> ({frame: {col: value}}, [errors])."""
    try:
        header, data = read_csv_rows(path)
    except ValueError as exc:
        return None, [str(exc)]
    base = os.path.basename(path)
    idx, errors = _column_indices(header, value_cols, base, needs_frame=True)
    table = {}
    if 'Frame' in idx:
        fpos = idx['Frame']
        seen = set()
        for i, r in enumerate(data):
            flabel = '%s row %d Frame' % (base, i + 2)
            try:
                fv = parse_finite(r[fpos], flabel)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if fv != int(fv):
                errors.append('%s = %s is not an integer frame index'
                              % (flabel, fv))
                continue
            frame = int(fv)
            if frame in seen:
                errors.append('%s: duplicate frame index %d' % (base, frame))
                continue
            seen.add(frame)
            rowvals = {}
            ok = True
            for col in value_cols:
                if col not in idx:
                    continue
                try:
                    rowvals[col] = parse_finite(
                        r[idx[col]],
                        '%s frame %d column %r' % (base, frame, col))
                except ValueError as exc:
                    errors.append(str(exc))
                    ok = False
            if ok:
                table[frame] = rowvals
    return table, errors


def parse_single_table(path, value_cols):
    """Parse the single-value table -> ({col: value}, [errors])."""
    try:
        header, data = read_csv_rows(path)
    except ValueError as exc:
        return None, [str(exc)]
    base = os.path.basename(path)
    idx, errors = _column_indices(header, value_cols, base, needs_frame=False)
    if len(data) != 1:
        errors.append('%s: expected exactly 1 data row, found %d'
                      % (base, len(data)))
        return None, errors
    if errors:
        return None, errors
    values = {}
    for col in value_cols:
        try:
            values[col] = parse_finite(data[0][idx[col]],
                                       '%s column %r' % (base, col))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        return None, errors
    return values, []


# --------------------------------------------------------------- comparison
def within_tolerance(sub, ref):
    return abs(sub - ref) <= TOL_ABS + TOL_REL * abs(ref)


def compare_frame_file(fname, cols, ref_table, sub_table, sub_errs):
    if sub_errs:
        return False, 'submission table invalid: ' + '; '.join(sub_errs[:4])
    if not ref_table:
        return False, 'reference table %s is empty or unreadable' % fname
    if not sub_table:
        return False, '%s contains no usable rows' % fname
    problems = []
    ref_keys = set(ref_table)
    sub_keys = set(sub_table)
    if sub_keys != ref_keys:
        problems.append('Frame keys differ from the reference: %d missing, '
                        '%d extra' % (len(ref_keys - sub_keys),
                                      len(sub_keys - ref_keys)))
    n_cells = 0
    n_bad = 0
    examples = []
    for frame in sorted(ref_keys & sub_keys):
        for col in cols:
            r = ref_table[frame][col]
            s = sub_table[frame][col]
            n_cells += 1
            if not within_tolerance(s, r):
                n_bad += 1
                if len(examples) < 5:
                    examples.append('frame %d column %s' % (frame, col))
    if n_bad:
        suffix = ' ...' if n_bad > len(examples) else ''
        problems.append('%d of %d compared cells exceed the tolerance (%s%s)'
                        % (n_bad, n_cells, '; '.join(examples), suffix))
    if problems:
        return False, '; '.join(problems)
    return True, ('all %d RMSD cells over %d frames agree with the reference '
                  'within tolerance' % (n_cells, len(ref_keys & sub_keys)))


def compare_single_file(fname, cols, ref_vals, sub_vals, sub_errs):
    if sub_errs:
        return False, 'submission file invalid: ' + '; '.join(sub_errs[:4])
    if not ref_vals:
        return False, 'reference value for %s is unavailable' % fname
    if not sub_vals:
        return False, '%s contains no usable value' % fname
    bad = [col for col in cols
           if col in sub_vals and col in ref_vals
           and not within_tolerance(sub_vals[col], ref_vals[col])]
    if bad:
        return False, ('value(s) outside tolerance in column(s): %s'
                       % ', '.join(bad))
    return True, ('the reported Backbone RMSD value agrees with the '
                  'reference within tolerance')


# -------------------------------------------------------------------- graded
def grade(reference_dir, submission_dir):
    # ---- read the reference side ----
    ref_tables = {}
    for fname, cols in FRAME_FILES:
        table, errs = parse_frame_table(os.path.join(reference_dir, fname),
                                        cols)
        ref_tables[fname] = (table, errs)
    ref_single_vals, ref_single_errs = parse_single_table(
        os.path.join(reference_dir, SINGLE_FILE[0]), SINGLE_FILE[1])

    # ---- read the submission side ----
    errors = []
    sub_tables = {}
    sub_errs = {}
    for fname, cols in FRAME_FILES:
        table, errs = parse_frame_table(
            os.path.join(submission_dir, fname), cols)
        sub_tables[fname] = table
        sub_errs[fname] = errs
        errors.extend(errs)
    if all(not sub_errs[f] for f, _ in FRAME_FILES):
        base = FRAME_FILES[0][0]
        base_keys = set(sub_tables[base].keys())
        for fname, _ in FRAME_FILES[1:]:
            keys = set(sub_tables[fname].keys())
            if keys != base_keys:
                errors.append(
                    'frame keys are not identical across files 1-4: %s '
                    'disagrees with %s' % (fname, base))
    sub_single_vals, sub_single_errs = parse_single_table(
        os.path.join(submission_dir, SINGLE_FILE[0]), SINGLE_FILE[1])
    errors.extend(sub_single_errs)

    results = {}
    results['structural_schema'] = (
        not errors,
        ('all five files match the required schema (columns, frame grain, '
         'single-row endpoint, finite values)'
         if not errors else '; '.join(errors[:12])))

    # ---- scientific checks, one per analysis branch ----
    if ref_single_errs:
        results['analysis_a_open_closed'] = (
            False, 'reference value could not be parsed: '
            + '; '.join(ref_single_errs[:3]))
    else:
        results['analysis_a_open_closed'] = compare_single_file(
            SINGLE_FILE[0], SINGLE_FILE[1], ref_single_vals, sub_single_vals,
            sub_single_errs)

    for fname, cols in FRAME_FILES:
        cid = {'backbone_rmsd.csv': 'analysis_b_backbone_groups',
               'ca_core_rmsd.csv': 'analysis_c_ca_core',
               'mass_weighted_rmsd.csv': 'analysis_d_mass_weighted',
               'resid_weighted_rmsd.csv': 'analysis_e_resid_weighted'}[fname]
        ref_table, ref_errs = ref_tables[fname]
        if ref_errs:
            results[cid] = (False, 'reference table could not be parsed: '
                            + '; '.join(ref_errs[:3]))
        else:
            results[cid] = compare_frame_file(fname, cols, ref_table,
                                              sub_tables[fname],
                                              sub_errs[fname])

    return [make_check(cid, results[cid][0], results[cid][1])
            for cid in CHECK_ORDER]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reference-dir', required=True)
    ap.add_argument('--submission-dir', required=True)
    ap.add_argument('--report', required=True)
    args = ap.parse_args()

    try:
        checks = grade(args.reference_dir, args.submission_dir)
    except Exception as exc:  # never crash without a valid report
        checks = [make_check(cid, False, 'grader internal error: %r' % (exc,))
                  for cid in CHECK_ORDER]

    report = {'passed': all(c['passed'] for c in checks), 'checks': checks}
    with open(args.report, 'w', encoding='utf-8') as fh:
        json.dump(report, fh)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

