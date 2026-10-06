"""Independent parent controls against the generated grader; remote CPU only."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

sys.path.insert(0, '/tests')
from parent_audit import NAMES, compare_artifacts, reference

ROOT = Path('/app/results')
OUT = Path('/app/validation-results')
SAVE = Path('/app/oracle-save')
shutil.copytree(ROOT, SAVE)
report = Path('/app/report.md').read_bytes()
ref = reference()
records = []


def restore():
    shutil.rmtree(ROOT, ignore_errors=True)
    shutil.copytree(SAVE, ROOT)
    Path('/app/report.md').write_bytes(report)


def grade(label, expected_pass):
    dest = OUT / 'controls' / label
    dest.mkdir(parents=True)
    started = time.monotonic()
    with (dest / 'stdout.txt').open('w') as stdout, (dest / 'stderr.txt').open('w') as stderr:
        result = subprocess.run(['python', '-m', 'pytest', '-q', '-o', 'addopts=', '/tests/test_outputs.py',
                                 '--junitxml=' + str(dest / 'junit.xml')], stdout=stdout, stderr=stderr,
                                timeout=120, check=False)
    nodes = list(ET.parse(dest / 'junit.xml').getroot().iter('testcase'))
    failures = [n.attrib.get('name') for n in nodes if n.find('failure') is not None]
    errors = [n.attrib.get('name') for n in nodes if n.find('error') is not None]
    actual = result.returncode == 0 and bool(nodes) and not failures and not errors
    record = {'control': label, 'expected_pass': expected_pass, 'actual_pass': actual,
              'expectation_met': actual == expected_pass and bool(nodes), 'exit_code': result.returncode,
              'testcases': len(nodes), 'failed_components': failures, 'errored_components': errors,
              'seconds': round(time.monotonic() - started, 3)}
    records.append(record)
    print('CONTROL ' + json.dumps(record), flush=True)


def set_reference_outputs(changed):
    for kind in ['oof', 'test']:
        changed[kind].to_csv(ROOT / (kind + '_predictions.csv'), index=False)
    metrics = json.loads((ROOT / 'metrics.json').read_text())
    metrics['models'] = changed['models']
    metrics['selected_model'] = changed['selected_model']
    (ROOT / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    summary = json.loads((ROOT / 'selected_model_report.json').read_text())
    summary['selected_model'] = changed['selected_model']
    for key in ['cv_roc_auc_mean', 'test_roc_auc', 'test_accuracy']:
        summary[key] = changed['models'][changed['selected_model']][key]
    (ROOT / 'selected_model_report.json').write_text(json.dumps(summary, indent=2))


try:
    # Re-execute the solver's real entry point in a separate output directory.
    rerun = Path('/app/reproduction/results')
    rerun.parent.mkdir()
    with (OUT / 'reproduction.stdout.txt').open('w') as stdout, (OUT / 'reproduction.stderr.txt').open('w') as stderr:
        result = subprocess.run(['python', '/app/run_pipeline.py', '--data', '/app/data/data.csv',
                                 '--output-dir', str(rerun)], stdout=stdout, stderr=stderr, timeout=120, check=False)
    assert result.returncode == 0, 'pipeline repeat failed'
    differences = compare_artifacts(ref, rerun)
    (OUT / 'repeatability.json').write_text(json.dumps({'passed': True, 'independent_reference_max_abs_difference': differences}, indent=2))

    restore()
    grade('honest', True)
    restore()
    shutil.rmtree(ROOT)
    Path('/app/report.md').unlink()
    grade('empty', False)

    restore()
    perfect = {'oof': ref['oof'].copy(), 'test': ref['test'].copy(),
               'models': json.loads(json.dumps(ref['models'])), 'selected_model': NAMES[0]}
    for kind in ['oof', 'test']:
        perfect[kind]['y_proba'] = perfect[kind]['y_true'].astype(float)
        perfect[kind]['y_pred'] = perfect[kind]['y_true']
    for row in perfect['models'].values():
        for key, val in row.items():
            row[key] = [1.0] * 5 if isinstance(val, list) else 1.0
    set_reference_outputs(perfect)
    grade('perfect-label-predictions', False)

    restore()
    for kind in ['oof', 'test']:
        path = ROOT / (kind + '_predictions.csv')
        frame = pd.read_csv(path, dtype={'id': str})
        for name in NAMES:
            mask = frame.model == name
            frame.loc[mask, 'id'] = np.roll(frame.loc[mask, 'id'].to_numpy(), 1)
        frame.to_csv(path, index=False)
    grade('shuffled-ids', False)

    restore()
    path = ROOT / 'metrics.json'
    metric = json.loads(path.read_text())
    for row in metric['models'].values():
        row['cv_roc_auc_mean'] = 0.0
        row['cv_roc_auc_per_fold'] = [0.0] * 5
    path.write_text(json.dumps(metric))
    grade('fabricated-cv-metrics', False)

    restore()
    leak = reference(leaky=True)
    delta = float(np.max(np.abs(leak['oof'].y_proba.to_numpy() - ref['oof'].y_proba.to_numpy())))
    assert delta > 1e-6, 'leakage control is not discriminated by proposed tolerance'
    (OUT / 'leakage-difference.json').write_text(json.dumps({'oof_max_abs_difference': delta, 'tolerance': 1e-6}))
    set_reference_outputs(leak)
    grade('global-scaler-leakage', False)

    restore()
    path = ROOT / 'oof_predictions.csv'
    frame = pd.read_csv(path, dtype={'id': str})
    frame.loc[1, 'id'] = frame.loc[0, 'id']
    frame.to_csv(path, index=False)
    grade('duplicate-id', False)

    restore()
    path = ROOT / 'test_predictions.csv'
    frame = pd.read_csv(path, dtype={'id': str})
    chosen = frame.index[(frame.model == NAMES[0]) & (frame.y_proba > .01) & (frame.y_proba < .49)][0]
    frame.loc[chosen, 'y_proba'] += 1e-8
    frame.to_csv(path, index=False)
    grade('within-tolerance-probability', True)
finally:
    restore()
    (OUT / 'controls.json').write_text(json.dumps(records, indent=2) + '\n')
assert records and all(r['expectation_met'] for r in records), 'Control expectation failed'
