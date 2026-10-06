import hashlib
import json
import os
from pathlib import Path
import subprocess

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

ROOT = Path('/workspace')
OUT = ROOT / 'output'
PRIVATE = Path('/tests/private')
ENV = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')


def read(name, root=OUT):
    return pd.read_csv(root / name, dtype={'id': str})


def context():
    c = json.loads((PRIVATE / 'models/catalog.json').read_text())
    d = read('development.csv', PRIVATE / 'data')
    folds = read('folds.csv', PRIVATE / 'data')
    return c, d.merge(folds, on='id', validate='one_to_one', sort=False)


def infer(meta, data):
    path = PRIVATE / 'models' / meta['artifact']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == meta['sha256']
    bundle = joblib.load(path)
    model = bundle['model']
    return model.predict_proba(data[bundle['features']])[:, list(model.classes_).index('M')]


def metrics(y, p):
    pred = np.where(np.asarray(p) >= .5, 'M', 'B')
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=['B', 'M']).ravel()
    return dict(n=len(y), n_malignant=int(sum(y == 'M')), tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
                auc=roc_auc_score(y == 'M', p), accuracy=accuracy_score(y, pred),
                precision=precision_score(y, pred, pos_label='M', zero_division=0),
                recall=recall_score(y, pred, pos_label='M', zero_division=0),
                f1=f1_score(y, pred, pos_label='M', zero_division=0))


def close(a, b):
    np.testing.assert_allclose(a, b, atol=1e-8, rtol=0)


def winner():
    c, d = context()
    scores = {}
    for candidate in c['candidates']:
        scores[candidate['candidate_id']] = np.mean([
            metrics(d.loc[d.fold == f, 'diagnosis'], infer(candidate['folds'][str(f)], d[d.fold == f]))['auc']
            for f in range(5)])
    return min(scores, key=lambda k: (-scores[k], k))


def selected():
    c, _ = context()
    return next(x for x in c['candidates'] if x['candidate_id'] == winner())


def run_cli(*args):
    return subprocess.run([str(ROOT / 'evaluator'), *map(str, args)], cwd=ROOT, env=ENV,
                          capture_output=True, text=True, timeout=900)


def test_dataset_audit():
    c, d = context()
    a = json.loads((OUT / 'audit.json').read_text())
    assert a['rows'] == len(d) == 455
    assert a['columns'] == list(d.drop(columns='fold').columns)
    assert a['class_counts'] == d.diagnosis.value_counts().to_dict()
    assert a['missing_counts'] == d.drop(columns='fold').isna().sum().to_dict()
    assert a['duplicate_ids'] == int(d.id.duplicated().sum()) == 0
    assert a['predictors'] == c['features'] and a['positive_class'] == 'M'
    assert set(a['feature_summary']) == set(c['features'])
    for feature in c['features']:
        s = d[feature]
        q1, q3 = s.quantile([.25, .75])
        expected = dict(min=s.min(), max=s.max(), mean=s.mean(), std=s.std(ddof=1),
                        extreme_count=int(((s < q1 - 1.5*(q3-q1)) | (s > q3 + 1.5*(q3-q1))).sum()))
        for k, v in expected.items():
            close(a['feature_summary'][feature][k], v)
    assert len(a['redundancy']) >= 3
    pairs = set()
    for r in a['redundancy']:
        assert r['feature_a'] != r['feature_b']
        pairs.add(tuple(sorted([r['feature_a'], r['feature_b']])))
        corr = d[[r['feature_a'], r['feature_b']]].corr().iloc[0, 1]
        close(r['pearson_r'], corr)
        assert abs(corr) >= .9
    assert len(pairs) >= 3


def test_oof_inference():
    c, d = context()
    p = read('oof_predictions.csv')
    assert len(p) == 455 * 4
    assert set(p.candidate_id) == {x['candidate_id'] for x in c['candidates']}
    for candidate in c['candidates']:
        part = p[p.candidate_id == candidate['candidate_id']]
        assert not part.id.duplicated().any() and set(part.id) == set(d.id)
        part = d[['id', 'fold']].merge(part, on='id', validate='one_to_one', suffixes=('_true', ''))
        assert (part.fold_true == part.fold).all()
        assert np.isfinite(part.p_malignant).all() and part.p_malignant.between(0, 1).all()
        assert (part.predicted_label == np.where(part.p_malignant >= .5, 'M', 'B')).all()
        for f in range(5):
            rows = d[d.fold == f]
            got = part.set_index('id').loc[rows.id, 'p_malignant']
            close(got, infer(candidate['folds'][str(f)], rows))


def test_metrics():
    c, d = context()
    table = read('fold_metrics.csv')
    assert len(table) == 20 and not table.duplicated(['candidate_id', 'fold']).any()
    for candidate in c['candidates']:
        for f in range(5):
            rows = d[d.fold == f]
            expected = metrics(rows.diagnosis, infer(candidate['folds'][str(f)], rows))
            got = table[(table.candidate_id == candidate['candidate_id']) & (table.fold == f)]
            assert len(got) == 1
            for k, v in expected.items():
                close(got.iloc[0][k], v)


def test_comparison_selection():
    c, d = context()
    t = read('comparison.csv').set_index('candidate_id')
    assert len(t) == 4 and t.index.is_unique
    assert set(t.index) == {x['candidate_id'] for x in c['candidates']}
    assert set(t.family) == {'logistic', 'forest'} and set(t.strategy) == {'all', 'pruned'}
    for candidate in c['candidates']:
        ms = pd.DataFrame([metrics(d.loc[d.fold == f, 'diagnosis'], infer(candidate['folds'][str(f)], d[d.fold == f])) for f in range(5)])
        r = t.loc[candidate['candidate_id']]
        assert r['n'] == 455 and r['n_folds'] == 5
        assert r['family'] == candidate['family'] and r['strategy'] == candidate['strategy']
        for k in ['auc', 'accuracy', 'precision', 'recall', 'f1']:
            close(r['mean_' + k], ms[k].mean())
            close(r['sd_' + k], ms[k].std(ddof=1))
    s = json.loads((OUT / 'selection.json').read_text())
    assert s['candidate_id'] == winner()
    assert s['rule'] == 'max_mean_fold_auc_then_lexicographic_id'
    close(s['mean_auc'], t.loc[winner(), 'mean_auc'])


def test_holdout():
    _, d = context()
    h = read('holdout_features.csv', PRIVATE / 'data')
    labels = read('holdout_labels.csv', PRIVATE)
    p = read('holdout_predictions.csv')
    assert len(p) == 114 and p.id.tolist() == h.id.tolist() and not p.id.duplicated().any()
    assert set(p.id).isdisjoint(d.id)
    close(p.p_malignant, infer(selected()['full'], h))
    assert (p.predicted_label == np.where(p.p_malignant >= .5, 'M', 'B')).all()
    y = labels.set_index('id').loc[p.id, 'diagnosis']
    m = metrics(y, p.p_malignant)
    assert m['auc'] >= .95 and m['recall'] >= .85


def test_permutation_effects():
    c, d = context()
    candidate = selected()
    t = read('feature_effects.csv')
    assert len(t) == 30 * 5 * 5
    assert not t.duplicated(['feature', 'fold', 'repeat']).any()
    assert set(t.feature) == set(c['features'])
    assert set(t.fold) == set(range(5)) and set(t['repeat']) == set(range(5))
    for f in range(5):
        data = d[d.fold == f].copy()
        baseline = metrics(data.diagnosis, infer(candidate['folds'][str(f)], data))['auc']
        for j, feature in enumerate(c['features']):
            for repeat in range(5):
                seed = 314000 + 1000*f + 10*j + repeat
                perm = data.copy()
                perm[feature] = np.random.default_rng(seed).permutation(data[feature].to_numpy())
                auc = metrics(data.diagnosis, infer(candidate['folds'][str(f)], perm))['auc']
                row = t[(t.feature == feature) & (t.fold == f) & (t['repeat'] == repeat)]
                assert len(row) == 1 and row.iloc[0].seed == seed
                close(row.iloc[0][['baseline_auc', 'permuted_auc', 'delta']].astype(float), [baseline, auc, baseline-auc])
    summary = read('feature_ranking.csv')
    expected = t.groupby('feature', as_index=False).delta.mean().sort_values(['delta', 'feature'], ascending=[False, True])
    assert summary.feature.tolist() == expected.feature.tolist()
    close(summary.mean_delta, expected.delta)


def test_input_validation(tmp_path):
    h = read('holdout_features.csv', PRIVATE / 'data').iloc[:9].copy()
    expected = infer(selected()['full'], h)
    h = h.iloc[::-1, ::-1]
    h['diagnosis'] = 'unused'
    h['Unnamed: 32'] = 'unused'
    source, dest = tmp_path / 'input.csv', tmp_path / 'pred.csv'
    h.to_csv(source, index=False)
    proc = run_cli('predict', '--input', source, '--output', dest, '--models', ROOT / 'models', '--selection', OUT / 'selection.json')
    assert proc.returncode == 0, proc.stderr
    got = read('pred.csv', tmp_path)
    assert got.id.tolist() == h.id.tolist()
    close(got.p_malignant, expected[::-1])
    c, _ = context()
    feature = c['features'][0]
    cases = []
    cases.append((h.drop(columns=feature), feature))
    duplicate = h.copy(); duplicate.iloc[1, duplicate.columns.get_loc('id')] = duplicate.iloc[0]['id']
    cases.append((duplicate, 'id'))
    for value in ['invalid', 'inf', 'NaN']:
        bad = h.copy(); bad[feature] = bad[feature].astype(object); bad.iloc[0, bad.columns.get_loc(feature)] = value
        cases.append((bad, feature))
    for i, (bad, diagnostic) in enumerate(cases):
        path = tmp_path / f'bad{i}.csv'; output = tmp_path / f'bad{i}_out.csv'
        bad.to_csv(path, index=False)
        proc = run_cli('predict', '--input', path, '--output', output, '--models', ROOT / 'models', '--selection', OUT / 'selection.json')
        assert proc.returncode != 0 and diagnostic.lower() in proc.stderr.lower()
        assert not output.exists()


def test_reproducibility(tmp_path):
    dirs = [tmp_path / 'a', tmp_path / 'b']
    for out in dirs:
        proc = run_cli('evaluate', '--development', ROOT / 'data/development.csv', '--holdout', ROOT / 'data/holdout_features.csv',
                       '--folds', ROOT / 'data/folds.csv', '--models', ROOT / 'models', '--output', out)
        assert proc.returncode == 0, proc.stderr
    for name in ['oof_predictions.csv', 'fold_metrics.csv', 'comparison.csv', 'feature_effects.csv', 'feature_ranking.csv', 'holdout_predictions.csv']:
        a, b = [read(name, folder) for folder in dirs]
        pd.testing.assert_frame_equal(a, b, check_exact=False, atol=1e-8, rtol=0)
        pd.testing.assert_frame_equal(a, read(name), check_exact=False, atol=1e-8, rtol=0)
    assert json.loads((dirs[0] / 'selection.json').read_text()) == json.loads((dirs[1] / 'selection.json').read_text())
    h = read('holdout_features.csv', PRIVATE / 'data').iloc[[8, 2, 41]]
    source = tmp_path / 'subset.csv'; h.to_csv(source, index=False)
    target = tmp_path / 'subset_predictions.csv'
    proc = run_cli('predict', '--input', source, '--output', target, '--models', ROOT / 'models', '--selection', dirs[0] / 'selection.json')
    assert proc.returncode == 0, proc.stderr
    p = read(target.name, tmp_path)
    assert p.id.tolist() == h.id.tolist()
    close(p.p_malignant, read('holdout_predictions.csv', dirs[0]).set_index('id').loc[h.id, 'p_malignant'])


def test_evidence_integration():
    c, _ = context()
    entries = [json.loads(line) for line in (OUT / 'experiments.jsonl').read_text().splitlines() if line.strip()]
    assert len(entries) >= 2
    comp = read('comparison.csv').set_index('candidate_id')
    catalog = {x['candidate_id']: x for x in c['candidates']}
    pairs = set()
    for e in entries:
        a, b = e['candidate_a'], e['candidate_b']
        assert a in catalog and b in catalog and a != b
        pairs.add(tuple(sorted([a,b])))
        assert e['metric'] == 'mean_auc'
        close(e['value_a'], comp.loc[a, 'mean_auc']); close(e['value_b'], comp.loc[b, 'mean_auc'])
        assert e['artifact_a'] == catalog[a]['full']['artifact'] and e['artifact_b'] == catalog[b]['full']['artifact']
        assert len(e['decision'].strip()) > 0
    assert len(pairs) >= 2
    a = json.loads((OUT / 'audit.json').read_text())['source_audit']
    assert a['rounded_predictions_used_for_auc'] is True
    assert a['lightgbm_prediction_active'] is False
    assert a['lightgbm_metrics_reuse'] == 'GBM'
    assert a['xgboost_final_uses_cv_best_iteration'] is False
    assert a['notebook_numeric_claims_independently_verified'] is False
    report = (OUT / 'report.md').read_text().strip()
    assert len(report) >= 100
