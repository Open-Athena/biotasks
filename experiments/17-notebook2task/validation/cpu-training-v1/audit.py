"""Parent-authored independent native reference; execute on remote CPU only."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20250607
NAMES = ['logistic_regression', 'random_forest', 'gradient_boosting']
ATOL = 1e-6


def reference(leaky=False):
    raw = pd.read_csv('/tests/data.csv')
    blank = [c for c in raw if raw[c].isna().all()]
    features = [c for c in raw if c not in ['id', 'diagnosis', *blank]]
    x = raw[features].to_numpy(dtype=np.float64)
    y = raw.diagnosis.map({'B': 0, 'M': 1}).to_numpy()
    ids = raw.id.astype(str).to_numpy()
    tr, te = train_test_split(np.arange(len(raw)), test_size=.2, random_state=SEED, shuffle=True, stratify=y)
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(x[tr], y[tr]))
    models = [make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, solver='lbfgs', random_state=SEED)),
              RandomForestClassifier(n_estimators=100, random_state=SEED, n_jobs=1),
              HistGradientBoostingClassifier(random_state=SEED)]
    oof, test, metrics = [], [], {}
    for name, estimator in zip(NAMES, models, strict=True):
        design = x
        if leaky and name == 'logistic_regression':
            design = StandardScaler().fit_transform(x)
            estimator = LogisticRegression(max_iter=1000, solver='lbfgs', random_state=SEED)
        probs = np.full(len(tr), np.nan)
        fold_id = np.full(len(tr), -1)
        fold_aucs = []
        for k, (fit, val) in enumerate(folds):
            fitted = clone(estimator).fit(design[tr[fit]], y[tr[fit]])
            probs[val] = fitted.predict_proba(design[tr[val]])[:, 1]
            fold_id[val] = k
            fold_aucs.append(float(roc_auc_score(y[tr[val]], probs[val])))
        held = clone(estimator).fit(design[tr], y[tr]).predict_proba(design[te])[:, 1]
        oof.append(pd.DataFrame({'id': ids[tr], 'model': name, 'fold': fold_id,
                                 'y_true': y[tr], 'y_pred': (probs >= .5).astype(int), 'y_proba': probs}))
        test.append(pd.DataFrame({'id': ids[te], 'model': name,
                                  'y_true': y[te], 'y_pred': (held >= .5).astype(int), 'y_proba': held}))
        row = {'cv_roc_auc_mean': float(np.mean(fold_aucs)), 'cv_roc_auc_per_fold': fold_aucs,
               'test_roc_auc': float(roc_auc_score(y[te], held))}
        for prefix, truth, p in [('cv', y[tr], probs), ('test', y[te], held)]:
            pred = (p >= .5).astype(int)
            row[prefix + '_accuracy'] = float(accuracy_score(truth, pred))
            row[prefix + '_precision'] = float(precision_score(truth, pred, zero_division=0))
            row[prefix + '_recall'] = float(recall_score(truth, pred, zero_division=0))
            row[prefix + '_f1'] = float(f1_score(truth, pred, zero_division=0))
        metrics[name] = row
    selected = max(NAMES, key=lambda name: metrics[name]['cv_roc_auc_mean'])
    correlations = np.corrcoef(x, rowvar=False)
    eda = {'class_counts': {k: int(v) for k, v in raw.diagnosis.value_counts().items()},
           'missing_values': {k: int(v) for k, v in raw.isna().sum().items()},
           'high_correlation_pairs': int(np.count_nonzero(np.triu(np.abs(correlations) > .9, 1))),
           'pca_two_component_variance': float(PCA(svd_solver='full').fit(StandardScaler().fit_transform(x)).explained_variance_ratio_[:2].sum())}
    return {'oof': pd.concat(oof, ignore_index=True), 'test': pd.concat(test, ignore_index=True),
            'models': metrics, 'selected_model': selected, 'eda': eda}


def compare_artifacts(ref, root):
    deltas = {}
    for kind in ['oof', 'test']:
        got = pd.read_csv(root / (kind + '_predictions.csv'), dtype={'id': str})
        assert not got.duplicated(['id', 'model']).any(), 'duplicate keys'
        expected = ref[kind].set_index(['id', 'model']).sort_index()
        got = got.set_index(['id', 'model']).sort_index()
        assert got.index.equals(expected.index), f'{kind}: row/key mismatch'
        for col in ['y_true', 'y_pred'] + (['fold'] if kind == 'oof' else []):
            np.testing.assert_array_equal(got[col], expected[col], err_msg=kind + ':' + col)
        assert np.isfinite(got.y_proba).all() and got.y_proba.between(0, 1).all()
        delta = float(np.max(np.abs(got.y_proba.to_numpy() - expected.y_proba.to_numpy())))
        deltas[kind] = delta
        np.testing.assert_allclose(got.y_proba, expected.y_proba, atol=ATOL, rtol=0)
    metrics = json.loads((root / 'metrics.json').read_text())
    assert set(metrics['models']) == set(NAMES)
    for name in NAMES:
        for key, value in ref['models'][name].items():
            np.testing.assert_allclose(metrics['models'][name][key], value, atol=ATOL, rtol=0, err_msg=name + ':' + key)
    assert metrics['selected_model'] == ref['selected_model']
    report = json.loads((root / 'selected_model_report.json').read_text())
    assert report['selected_model'] == ref['selected_model']
    assert report['label_mapping'] == {'B': 0, 'M': 1}
    assert report['random_state'] == SEED and report['n_train'] == 455 and report['n_test'] == 114 and report['feature_count'] == 30
    for key in ['cv_roc_auc_mean', 'test_roc_auc', 'test_accuracy']:
        np.testing.assert_allclose(report[key], ref['models'][ref['selected_model']][key], atol=ATOL, rtol=0)
    eda = json.loads((root / 'eda.json').read_text())
    for key in ['class_counts', 'missing_values', 'high_correlation_pairs']:
        assert eda[key] == ref['eda'][key], 'EDA:' + key
    np.testing.assert_allclose(eda['pca_two_component_variance'], ref['eda']['pca_two_component_variance'], atol=ATOL, rtol=0)
    return deltas


if __name__ == '__main__':
    out = Path('/app/validation-results')
    ref = reference()
    record = {'kind': 'independent parent native recomputation', 'probability_max_abs_difference': compare_artifacts(ref, Path('/app/results')),
              'selected_model': ref['selected_model'], 'native_metrics': ref['models'], 'native_eda': ref['eda'],
              'comparison_atol': ATOL, 'comparison_rtol': 0}
    for kind in ['oof', 'test']:
        ref[kind].to_csv(out / ('parent-reference-' + kind + '.csv'), index=False)
    (out / 'parent-audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
