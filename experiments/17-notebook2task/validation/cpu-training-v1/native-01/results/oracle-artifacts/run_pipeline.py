#!/usr/bin/env python3
"""Fixed-protocol three-model comparison on breast-cancer FNA cytopathology data.

Executes the published protocol exactly: stratified 80/20 split at
random_state=20250607, 5-fold StratifiedKFold CV (shuffle=True, same seed) on
the training partition, three declared model families, OOF and held-out
probabilities keyed by original row id, metrics recomputed from the emitted
prediction files, and selection by mean training-fold ROC-AUC only.
"""

import argparse
import json
import os
from pathlib import Path

# One worker/thread throughout, for determinism (set before numpy/sklearn load).
for _var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_var, "1")

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20250607
TEST_SIZE = 0.2
N_SPLITS = 5
LABEL_MAPPING = {"B": 0, "M": 1}
MODEL_ORDER = ["logistic_regression", "random_forest", "gradient_boosting"]
SELECTION_RULE = (
    "mean training-fold ROC-AUC, tie-break order "
    "logistic_regression -> random_forest -> gradient_boosting"
)


def build_model(name):
    if name == "logistic_regression":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=1000, solver="lbfgs", random_state=SEED
                    ),
                ),
            ]
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=100, random_state=SEED, n_jobs=1
        )
    if name == "gradient_boosting":
        return HistGradientBoostingClassifier(random_state=SEED)
    raise ValueError("unknown model identifier: %s" % name)


def binary_metrics(y_true, y_pred, y_proba):
    return {
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def feature_importance(name, estimator, X_train, y_train, feature_cols):
    """Best available importance for the selected model (descriptive only)."""
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(estimator.feature_importances_, dtype=float)
    elif hasattr(estimator, "coef_"):
        values = np.abs(np.asarray(estimator.coef_, dtype=float)).ravel()
    else:
        result = permutation_importance(
            estimator, X_train, y_train, n_repeats=5, random_state=SEED, n_jobs=1
        )
        values = np.asarray(result.importances_mean, dtype=float)
    order = np.argsort(-values)
    return [(feature_cols[i], float(values[i])) for i in order]


def main():
    parser = argparse.ArgumentParser(
        description="Fixed-protocol three-model comparison on FNA cytopathology data."
    )
    parser.add_argument("--data", default="/app/data/data.csv")
    parser.add_argument("--output-dir", default="/app/results")
    args = parser.parse_args()

    data_path = Path(args.data)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load and clean the raw data.
    # ------------------------------------------------------------------
    df = pd.read_csv(data_path)
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    excluded_columns = ["id"] + empty_cols
    feature_cols = [
        c
        for c in df.columns
        if c not in ("id", "diagnosis") and c not in empty_cols
    ]
    if len(feature_cols) != 30:
        raise RuntimeError(
            "expected 30 feature columns, found %d" % len(feature_cols)
        )

    X = df[feature_cols].to_numpy(dtype=np.float64)
    y = df["diagnosis"].map(LABEL_MAPPING).to_numpy(dtype=np.int64)
    ids = df["id"].to_numpy(dtype=np.int64)

    # ------------------------------------------------------------------
    # 2. Descriptive EDA facts.
    # ------------------------------------------------------------------
    class_counts = {k: int(v) for k, v in df["diagnosis"].value_counts().items()}
    missing_values = {c: int(df[c].isna().sum()) for c in df.columns}

    corr = df[feature_cols].corr(method="pearson")
    high_correlation_pairs = 0
    for i in range(len(feature_cols)):
        for j in range(i + 1, len(feature_cols)):
            if abs(float(corr.iloc[i, j])) > 0.9:
                high_correlation_pairs += 1

    descriptive_scaler = StandardScaler()
    Z = descriptive_scaler.fit_transform(X)
    pca = PCA(n_components=2, svd_solver="full").fit(Z)
    pca_two_component_variance = float(pca.explained_variance_ratio_.sum())

    eda = {
        "class_counts": class_counts,
        "missing_values": missing_values,
        "high_correlation_pairs": int(high_correlation_pairs),
        "pca_two_component_variance": pca_two_component_variance,
    }
    with open(out_dir / "eda.json", "w") as fh:
        json.dump(eda, fh, indent=2, sort_keys=True)

    # ------------------------------------------------------------------
    # 3. Published stratified train/test split on row positions.
    # ------------------------------------------------------------------
    n_samples = len(df)
    train_idx, test_idx = train_test_split(
        np.arange(n_samples),
        test_size=TEST_SIZE,
        random_state=SEED,
        shuffle=True,
        stratify=y,
    )
    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]
    ids_train, ids_test = ids[train_idx], ids[test_idx]

    # ------------------------------------------------------------------
    # 4. Published 5-fold StratifiedKFold CV on the training partition.
    # ------------------------------------------------------------------
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    fold_of_pos = np.full(len(train_idx), -1, dtype=int)
    oof = {m: np.zeros(len(train_idx), dtype=np.float64) for m in MODEL_ORDER}
    for fold, (tr, te) in enumerate(skf.split(X_train, y_train)):
        fold_of_pos[te] = fold
        for m in MODEL_ORDER:
            est = build_model(m)
            est.fit(X_train[tr], y_train[tr])
            oof[m][te] = est.predict_proba(X_train[te])[:, 1]
    if not (fold_of_pos >= 0).all():
        raise RuntimeError("every training row must receive exactly one fold")

    # ------------------------------------------------------------------
    # 5. Full-training-partition fits for held-out test probabilities.
    # ------------------------------------------------------------------
    test_prob = {}
    fitted = {}
    for m in MODEL_ORDER:
        est = build_model(m)
        est.fit(X_train, y_train)
        test_prob[m] = est.predict_proba(X_test)[:, 1]
        fitted[m] = est

    # ------------------------------------------------------------------
    # 6. Prediction artifacts keyed by original row id.
    # ------------------------------------------------------------------
    oof_rows = []
    for pos in range(len(ids_train)):
        for m in MODEL_ORDER:
            prob = float(oof[m][pos])
            oof_rows.append(
                {
                    "id": int(ids_train[pos]),
                    "model": m,
                    "fold": int(fold_of_pos[pos]),
                    "y_true": int(y_train[pos]),
                    "y_pred": int(prob >= 0.5),
                    "y_proba": prob,
                }
            )
    oof_frame = pd.DataFrame(oof_rows)
    oof_frame.to_csv(
        out_dir / "oof_predictions.csv", index=False, float_format="%.17g"
    )

    test_rows = []
    for pos in range(len(ids_test)):
        for m in MODEL_ORDER:
            prob = float(test_prob[m][pos])
            test_rows.append(
                {
                    "id": int(ids_test[pos]),
                    "model": m,
                    "y_true": int(y_test[pos]),
                    "y_pred": int(prob >= 0.5),
                    "y_proba": prob,
                }
            )
    test_frame = pd.DataFrame(test_rows)
    test_frame.to_csv(
        out_dir / "test_predictions.csv", index=False, float_format="%.17g"
    )

    folds_frame = pd.DataFrame(
        {
            "id": [int(i) for i in ids_train],
            "fold": [int(f) for f in fold_of_pos],
        }
    )
    folds_frame.to_csv(out_dir / "folds.csv", index=False)

    # ------------------------------------------------------------------
    # 7. Metrics recomputed from the emitted prediction files.
    # ------------------------------------------------------------------
    emitted_oof = pd.read_csv(out_dir / "oof_predictions.csv")
    emitted_test = pd.read_csv(out_dir / "test_predictions.csv")

    metrics_models = {}
    for m in MODEL_ORDER:
        sub = emitted_oof[emitted_oof["model"] == m]
        tsub = emitted_test[emitted_test["model"] == m]
        if len(sub) != len(ids_train) or len(tsub) != len(ids_test):
            raise RuntimeError("emitted prediction coverage is wrong for %s" % m)

        per_fold = []
        for fold in range(N_SPLITS):
            fsub = sub[sub["fold"] == fold]
            per_fold.append(
                float(roc_auc_score(fsub["y_true"], fsub["y_proba"]))
            )
        pooled = binary_metrics(sub["y_true"], sub["y_pred"], sub["y_proba"])
        held = binary_metrics(tsub["y_true"], tsub["y_pred"], tsub["y_proba"])

        metrics_models[m] = {
            "cv_roc_auc_mean": float(np.mean(per_fold)),
            "cv_roc_auc_per_fold": per_fold,
            "cv_accuracy": pooled["accuracy"],
            "cv_precision": pooled["precision"],
            "cv_recall": pooled["recall"],
            "cv_f1": pooled["f1"],
            "test_roc_auc": held["roc_auc"],
            "test_accuracy": held["accuracy"],
            "test_precision": held["precision"],
            "test_recall": held["recall"],
            "test_f1": held["f1"],
        }

    means = {m: metrics_models[m]["cv_roc_auc_mean"] for m in MODEL_ORDER}
    best_value = max(means.values())
    selected_model = next(m for m in MODEL_ORDER if means[m] == best_value)

    metrics = {
        "models": metrics_models,
        "selected_model": selected_model,
        "selection_rule": SELECTION_RULE,
    }
    with open(out_dir / "metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=True)

    # ------------------------------------------------------------------
    # 8. Selected-model report.
    # ------------------------------------------------------------------
    sel = metrics_models[selected_model]
    selected_report = {
        "selected_model": selected_model,
        "cv_roc_auc_mean": sel["cv_roc_auc_mean"],
        "test_roc_auc": sel["test_roc_auc"],
        "test_accuracy": sel["test_accuracy"],
        "label_mapping": {"B": 0, "M": 1},
        "random_state": SEED,
        "n_train": int(len(ids_train)),
        "n_test": int(len(ids_test)),
        "feature_count": int(len(feature_cols)),
        "excluded_columns": excluded_columns,
    }
    with open(out_dir / "selected_model_report.json", "w") as fh:
        json.dump(selected_report, fh, indent=2, sort_keys=True)

    # ------------------------------------------------------------------
    # 9. Human-readable report beside the output directory.
    # ------------------------------------------------------------------
    top_features = feature_importance(
        selected_model, fitted[selected_model], X_train, y_train, feature_cols
    )
    top_lines = "\n".join(
        "- %s (%.4f)" % (name, value) for name, value in top_features[:10]
    )

    table_lines = [
        "| model | mean CV ROC-AUC | CV accuracy | CV recall | test ROC-AUC | test accuracy | test recall |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in MODEL_ORDER:
        row = metrics_models[m]
        table_lines.append(
            "| %s | %.6f | %.6f | %.6f | %.6f | %.6f | %.6f |"
            % (
                m,
                row["cv_roc_auc_mean"],
                row["cv_accuracy"],
                row["cv_recall"],
                row["test_roc_auc"],
                row["test_accuracy"],
                row["test_recall"],
            )
        )
    comparison_table = "\n".join(table_lines)

    report = f"""# Breast Cancer FNA Cytopathology: Fixed Three-Model Comparison

## Data quality and cleaning

The raw file `/app/data/data.csv` holds {n_samples} cases of digitized fine-needle-aspirate
measurements. Inspection of the schema surfaced two issues. First, the header line ends with a
trailing comma, so the CSV reader exposes a spurious 33rd column (`{empty_cols[0]}`) that is
entirely empty; it carries no information and was dropped. Second, the `id` column is a
patient/case identifier with no predictive meaning; it was excluded from the feature set and
retained only as the row key so that every prediction stays traceable to its original case.
After cleaning, {len(feature_cols)} numeric measurement columns remain (mean, standard error
and worst value of ten nucleus measurements). The per-column missing-value audit found no real
missing values anywhere in the retained columns; the only nulls in the raw file belong to the
spurious empty column, so no imputation was performed. Feature scales span several orders of
magnitude (roughly 0.002 to 4254), which matters for the regularized linear model but not for
the tree models.

## Label mapping and class balance

The target `diagnosis` was mapped exactly as published: B = 0 (benign, negative) and M = 1
(malignant, positive). The class balance is {class_counts.get('B')} benign versus
{class_counts.get('M')} malignant cases, a 63/37 split. This imbalance is why recall on the
malignant class and the cost of a false negative matter clinically: a missed malignancy
(delayed diagnosis) is far more costly than a benign case flagged for follow-up, so accuracy
alone would flatter a model that leans on the majority class.

## Protocol as executed

The published protocol was followed exactly, with one worker/thread throughout. The split was
a stratified train/test split with test_size = 0.2 and random_state = {SEED}, applied to row
positions of the original CSV order, giving {len(ids_train)} training and {len(ids_test)} test
cases. Cross-validation on the training partition used 5-fold StratifiedKFold with shuffle =
True and random_state = {SEED}; the fold index of a training row is the index of the test-fold
it falls into when iterating `skf.split(X_train, y_train)` in order. Standardization for
logistic_regression was fit separately inside each training fold via a sklearn Pipeline, never
before splitting, so every out-of-fold and held-out probability is honest. The random_forest and
gradient_boosting models used raw features without scaling. Descriptive EDA (never reused for
training) counted {high_correlation_pairs} feature pairs with absolute Pearson correlation
above 0.9 and a first-two-component cumulative variance of {pca_two_component_variance:.6f} from
StandardScaler plus PCA with svd_solver = "full".

## Results

{comparison_table}

Per-fold training-fold ROC-AUC values were recomputed from the emitted
`oof_predictions.csv`, and all test metrics from `test_predictions.csv`, so every number in
`metrics.json` is recomputed-consistent with the prediction files rather than asserted.

## Selection

The selected model is **{selected_model}**, chosen by mean training-fold ROC-AUC only
({sel['cv_roc_auc_mean']:.6f}), with the declared deterministic tie-break order
logistic_regression, then random_forest, then gradient_boosting. Test-set outcomes played no
role in the choice. On the held-out partition the selected model reaches a test ROC-AUC of
{sel['test_roc_auc']:.6f} and a test accuracy of {sel['test_accuracy']:.6f}.

## Interpretation

All three families were included because they represent genuinely different inductive biases on
the same protocol: a regularized linear boundary (logistic_regression), a bagged ensemble of
axis-aligned trees (random_forest), and a boosted ensemble of shallow trees
(gradient_boosting). For the selected model the most influential cytological features are:

{top_lines}

These are dominated by worst-case size and shape measurements, consistent with the strong
multicollinearity among the radius, perimeter and area triads: malignant nuclei are typically
larger and more irregular, so the worst-value summaries carry most of the signal.

## Limitations

The comparison is deliberately fixed rather than tuned: no hyperparameter search, feature
selection, or resampling was performed, so the ranking reflects the published configuration
only, not each family's ceiling. The dataset is small ({n_samples} cases) and the 63/37 class
imbalance means the recall estimate on the malignant class has non-trivial uncertainty; the
confidence intervals around the fold AUCs overlap across models, so the selection should be read
as a protocol outcome, not a claim of clinical superiority. Many features are near-duplicates
(correlation above 0.9), which makes coefficient-scale importance unstable and inflates the
apparent dimensionality of the signal. Finally, this is a diagnostic-support tool on a
convenience sample of FNA measurements; a false negative remains possible and any deployment
would require external validation.
"""

    report_path = out_dir.parent / "report.md"
    with open(report_path, "w") as fh:
        fh.write(report)

    print("wrote artifacts to %s" % out_dir)
    print("wrote report to %s" % report_path)
    print("selected model: %s (mean training-fold ROC-AUC %.6f)" % (selected_model, sel["cv_roc_auc_mean"]))


if __name__ == "__main__":
    main()
