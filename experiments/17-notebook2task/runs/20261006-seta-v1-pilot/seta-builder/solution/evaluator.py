#!/opt/venv/bin/python
import argparse
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, float_format='%.17g')


def load_data(path, features, labeled=False):
    data = pd.read_csv(path, dtype={'id': str})
    if 'id' not in data or data.id.isna().any() or data.id.str.strip().eq('').any() or data.id.duplicated().any():
        raise ValueError('id must be present, nonempty and unique')
    if len(data) == 0:
        raise ValueError('id: no input rows')
    for f in features:
        if f not in data:
            raise ValueError(f'missing required predictor: {f}')
        try:
            data[f] = pd.to_numeric(data[f], errors='raise')
        except (TypeError, ValueError) as e:
            raise ValueError(f'malformed predictor: {f}') from e
        if not np.isfinite(data[f]).all():
            raise ValueError(f'nonfinite predictor: {f}')
    if labeled and ('diagnosis' not in data or not data.diagnosis.isin(['B', 'M']).all()):
        raise ValueError('diagnosis must contain B/M labels')
    return data


class Bank:
    def __init__(self, root):
        self.root = Path(root)
        self.catalog = json.loads((self.root / 'catalog.json').read_text())
        self.features = self.catalog['features']
        self.candidates = self.catalog['candidates']
        self.cache = {}

    def predict(self, meta, data):
        name = meta['artifact']
        if name not in self.cache:
            path = self.root / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != meta['sha256']:
                raise ValueError(f'artifact hash mismatch: {name}')
            self.cache[name] = joblib.load(path)
        bundle = self.cache[name]
        model = bundle['model']
        classes = list(model.classes_)
        if classes != meta['class_order']:
            raise ValueError('class order mismatch')
        return model.predict_proba(data[bundle['features']])[:, classes.index('M')]


def measure(y, p):
    pred = np.where(p >= .5, 'M', 'B')
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=['B', 'M']).ravel()
    return dict(n=len(y), n_malignant=int(sum(y == 'M')), tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
                auc=float(roc_auc_score(y == 'M', p)), accuracy=float(accuracy_score(y, pred)),
                precision=float(precision_score(y, pred, pos_label='M', zero_division=0)),
                recall=float(recall_score(y, pred, pos_label='M', zero_division=0)),
                f1=float(f1_score(y, pred, pos_label='M', zero_division=0)))


def predictions(data, p):
    return pd.DataFrame({'id': data.id.to_numpy(), 'p_malignant': p, 'predicted_label': np.where(p >= .5, 'M', 'B')})


def audit_data(d, features):
    summary = {}
    for f in features:
        s = d[f]; q1, q3 = s.quantile([.25, .75]); iqr = q3-q1
        summary[f] = dict(min=float(s.min()), max=float(s.max()), mean=float(s.mean()), std=float(s.std(ddof=1)),
                          extreme_count=int(((s < q1-1.5*iqr) | (s > q3+1.5*iqr)).sum()))
    corr = d[features].corr()
    redundancy = [dict(feature_a=a, feature_b=b, pearson_r=float(corr.loc[a,b]))
                  for j,a in enumerate(features) for b in features[j+1:] if abs(corr.loc[a,b]) >= .9]
    return dict(rows=len(d), columns=list(d.columns), predictors=features, class_counts=d.diagnosis.value_counts().to_dict(),
                positive_class='M', missing_counts=d.isna().sum().to_dict(), duplicate_ids=int(d.id.duplicated().sum()),
                feature_summary=summary, redundancy=redundancy,
                source_audit=dict(rounded_predictions_used_for_auc=True, lightgbm_prediction_active=False,
                                  lightgbm_metrics_reuse='GBM', xgboost_final_uses_cv_best_iteration=False,
                                  notebook_numeric_claims_independently_verified=False))


def evaluate(args):
    bank = Bank(args.models)
    d = load_data(args.development, bank.features, True)
    h = load_data(args.holdout, bank.features)
    folds = pd.read_csv(args.folds, dtype={'id': str})
    if set(d.id) & set(h.id):
        raise ValueError('id development/holdout overlap')
    if folds.id.duplicated().any() or set(folds.id) != set(d.id) or set(folds.fold) != set(range(5)):
        raise ValueError('id/fold membership invalid')
    if len(bank.candidates) != 4 or len({c['candidate_id'] for c in bank.candidates}) != 4:
        raise ValueError('candidate catalog invalid')
    audit = audit_data(d, bank.features)
    d = d.merge(folds, on='id', validate='one_to_one', sort=False)
    for c in bank.candidates:
        for f in range(5):
            if set(c['folds'][str(f)]['validation_ids']) != set(d.loc[d.fold == f, 'id']):
                raise ValueError('catalog fold validation IDs mismatch')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    dump(out / 'audit.json', audit)
    oof, fold_rows, comparison = [], [], []
    journal = out / 'experiments.jsonl'
    by_family = {}
    with journal.open('w') as log:
        for c in bank.candidates:
            cid = c['candidate_id']; local = []
            for f in range(5):
                data = d[d.fold == f]
                p = bank.predict(c['folds'][str(f)], data)
                pred = predictions(data, p); pred['candidate_id'] = cid; pred['fold'] = f
                oof.append(pred)
                m = measure(data.diagnosis, p); local.append(m)
                fold_rows.append(dict(candidate_id=cid, fold=f, **m))
            table = pd.DataFrame(local)
            entry = dict(candidate_id=cid, family=c['family'], strategy=c['strategy'], n=len(d), n_folds=5)
            for metric in ['auc', 'accuracy', 'precision', 'recall', 'f1']:
                entry['mean_'+metric] = float(table[metric].mean())
                entry['sd_'+metric] = float(table[metric].std(ddof=1))
            comparison.append(entry)
            if c['family'] in by_family:
                old, old_entry = by_family[c['family']]
                diff = entry['mean_auc']-old_entry['mean_auc']
                decision = f"Within {c['family']}, {cid} changes mean AUC by {diff:.8f}; select only after comparing all candidates."
                log.write(json.dumps(dict(candidate_a=old['candidate_id'], candidate_b=cid, metric='mean_auc',
                                         value_a=old_entry['mean_auc'], value_b=entry['mean_auc'],
                                         artifact_a=old['full']['artifact'], artifact_b=c['full']['artifact'], decision=decision))+'\n')
                log.flush()
            by_family[c['family']] = (c, entry)
    csv(out / 'oof_predictions.csv', pd.concat(oof, ignore_index=True))
    csv(out / 'fold_metrics.csv', fold_rows); csv(out / 'comparison.csv', comparison)
    best = sorted(comparison, key=lambda x: (-x['mean_auc'], x['candidate_id']))[0]
    candidate = next(c for c in bank.candidates if c['candidate_id'] == best['candidate_id'])
    dump(out / 'selection.json', dict(candidate_id=best['candidate_id'], rule='max_mean_fold_auc_then_lexicographic_id', mean_auc=best['mean_auc']))
    effects = []
    for f in range(5):
        data = d[d.fold == f].copy(); meta = candidate['folds'][str(f)]
        baseline = float(roc_auc_score(data.diagnosis == 'M', bank.predict(meta, data)))
        for j, feature in enumerate(bank.features):
            for repeat in range(5):
                seed = 314000 + 1000*f + 10*j + repeat
                perm = data.copy()
                perm[feature] = np.random.default_rng(seed).permutation(data[feature].to_numpy())
                score = float(roc_auc_score(data.diagnosis == 'M', bank.predict(meta, perm)))
                effects.append(dict(feature=feature, fold=f, repeat=repeat, seed=seed, baseline_auc=baseline, permuted_auc=score, delta=baseline-score))
    csv(out / 'feature_effects.csv', effects)
    ranking = pd.DataFrame(effects).groupby('feature', as_index=False).delta.mean().rename(columns={'delta': 'mean_delta'})
    ranking = ranking.sort_values(['mean_delta', 'feature'], ascending=[False, True])
    csv(out / 'feature_ranking.csv', ranking)
    csv(out / 'holdout_predictions.csv', predictions(h, bank.predict(candidate['full'], h)))
    report = [
        '# Frozen cytopathology benchmark',
        f"Development contains {len(d)} observations: {audit['class_counts']}. M is positive. Holdout contains {len(h)} disjoint identities; labels are unavailable, so holdout performance is not asserted here.",
        'ID identifies observations and diagnosis is the target; neither is a predictor. The empty final source field is unused. All 30 observed numeric predictors are retained in the input contract. No observations are removed. See audit.json for missingness and per-feature scales and IQR extremes.',
        'Extremes are descriptive flags, not evidence of erroneous specimens. Mean, standard-error and worst measurements have different units and scales. Logistic pipelines standardize on training partitions; forests split original values. Pruning is learned separately on each training partition and may remove interchangeable morphology measurements.',
        'Strong measured correlations: ' + '; '.join(f"{r['feature_a']} / {r['feature_b']}: r={r['pearson_r']:.5f}" for r in audit['redundancy'][:4]),
        'Candidate comparison (unweighted fold means and sample SD):',
        pd.DataFrame(comparison).to_string(index=False),
        f"Selected {best['candidate_id']} with mean fold AUC {best['mean_auc']:.8f}, SD {best['sd_auc']:.8f}. Selection obeys descending mean AUC and lexicographic exact ties. This same development estimate has selection optimism; five overlapping training samples do not yield an independent uncertainty interval.",
        f"Malignant recall is {best['mean_recall']:.6f} averaged over folds at threshold 0.5. False negatives represent missed malignancies in this retrospective benchmark. AUC measures ranking rather than this threshold's sensitivity; no clinical utility is established.",
        'The journal records measured within-family processing comparisons. The complete table also supports model-family comparison; variability and paired folds constrain interpretation of small differences.',
        'Leading permutation effects (mean validation AUC decrease): ' + '; '.join(f"{r.feature}: {r.mean_delta:.8f}" for r in ranking.head(3).itertuples()),
        'These measurements describe nucleus morphology and its association with classification. Correlated predictors can substitute for each other, masking individual effects; independent permutation can also create unusual combinations. Importance is not causal. Removed features legitimately have zero effect. Seeds and all repeats are in feature_effects.csv.',
        'Notebook audit: random_forest_prediction rounds predict(trainset.rf, testset), and the subsequent auc call uses testset$predicted. GBM likewise rounds gbmTest. The LightGBM prediction assignment is commented out, so its following confusion matrix and AUC still consume the preceding GBM prediction variable. Numeric diagnosis makes the notebook RF a regression fit. The XGBoost final fit uses nRounds rather than the chosen CV iteration. Notebook AUC statements, including the high CV claim, are unverified numerical claims, not held-out accuracy evidence.',
        'Repeat with /workspace/evaluator evaluate --development /workspace/data/development.csv --holdout /workspace/data/holdout_features.csv --folds /workspace/data/folds.csv --models /workspace/models --output a fresh directory. Predict accepts --input, --output, --models and --selection. Numeric results use absolute tolerance 1e-8 with fixed packages and one thread.'
    ]
    (out / 'report.md').write_text('\n\n'.join(report)+'\n')


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    e = subs.add_parser('evaluate')
    for name in ['development', 'holdout', 'folds', 'models', 'output']:
        e.add_argument('--'+name, required=True)
    p = subs.add_parser('predict')
    for name in ['input', 'output', 'models', 'selection']:
        p.add_argument('--'+name, required=True)
    args = parser.parse_args()
    if args.command == 'evaluate':
        evaluate(args)
    else:
        bank = Bank(args.models)
        data = load_data(args.input, bank.features)
        selection = json.loads(Path(args.selection).read_text())
        candidate = next(c for c in bank.candidates if c['candidate_id'] == selection['candidate_id'])
        csv(Path(args.output), predictions(data, bank.predict(candidate['full'], data)))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'evaluation error: {error}', file=sys.stderr)
        sys.exit(1)
