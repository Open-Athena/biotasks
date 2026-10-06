# Breast Cancer Prediction from Cytopathology Data — Fixed Three-Model Comparison

## Goal

Working from a raw clinical CSV of digitized fine-needle-aspirate (FNA) measurements, run a **fixed, reproducible three-model comparison** and produce artifacts an independent verifier can regenerate exactly. This is NOT open-ended model optimization: the protocol below is mandatory and is published precisely so that results are reproducible and independently checkable. The deliverables are:

1. A clean, analysis-ready dataset derived from the raw CSV (spurious empty column removed, patient identifier excluded, decisions documented).
2. Exactly **three model families** — logistic regression, random forest, gradient boosting — trained under the published protocol.
3. Per-model **out-of-fold (OOF) probabilities** for every training row, **held-out test probabilities** for every test row, fold assignments, and recomputed CV/test metrics — all keyed by original row `id`.
4. A **selected-model report** naming the winner, chosen **by mean training-fold ROC-AUC only** (test outcomes must not decide selection), with a declared deterministic tie-break.
5. A human-readable `report.md` explaining the data cleaning, the protocol, and the comparison.

## Published protocol (mandatory — these values define reproducibility, so they are given to you explicitly)

- **Label mapping**: `diagnosis` → `B` = 0 (negative), `M` = 1 (positive). Record this mapping in your artifacts.
- **Feature set**: all 30 numeric measurement columns. **Exclude** `id` (patient/case identifier, no predictive meaning) and the spurious trailing empty-named column (the header line ends with a comma, so most CSV readers surface a 33rd all-empty column — inspect and drop it).
- **Train/test split**: stratified, `test_size = 0.2`, `random_state = 20250607`, `shuffle = True`, on the label-mapped target. Test set = the held-out rows.
- **Cross-validation on the training partition**: 5-fold `StratifiedKFold` with `shuffle = True`, `random_state = 20250607`, `n_splits = 5`. **Fold assignment rule**: the fold index for a training row is the index of the test-fold it falls into when iterating `skf.split(X_train, y_train)` in order (fold 0, 1, 2, 3, 4). Each training row gets exactly one OOF probability from the fold in which it was held out.
- **Preprocessing**: standardization (`StandardScaler`) fit **separately within each training fold** via a `sklearn.pipeline.Pipeline`, never fit before splitting. Tree models (random forest, gradient boosting) use raw features without scaling; logistic regression uses `StandardScaler` inside its pipeline. No other preprocessing (no imputation, feature selection, or resampling — the data has no real missing values).
- **Model hyperparameters (exact, all defaults except those listed)**:
  - `LogisticRegression(max_iter=1000, solver="lbfgs", random_state=20250607)` in a `Pipeline` with `StandardScaler()`.
  - `RandomForestClassifier(n_estimators=100, random_state=20250607, n_jobs=1)` on raw features.
  - `HistGradientBoostingClassifier(random_state=20250607)` on raw features. No alternative gradient-boosting implementation is accepted in this fixed-protocol task.
- **Threads**: one worker / `n_jobs=1` throughout, for determinism.
- **Metrics**: ROC-AUC, accuracy, precision, recall, F1 (positive class = `M` = 1). CV metrics are computed from the OOF probabilities over the whole training partition; test metrics from the held-out probabilities.
- **Selection**: best model = highest **mean training-fold ROC-AUC** (the unweighted arithmetic mean of the five per-fold ROC-AUC values; pooled OOF ROC-AUC is NOT equivalent and must not determine selection). **Tie-break (deterministic)**: if two models' mean CV ROC-AUC are exactly equal, prefer in the order logistic regression → random forest → gradient boosting. Test-set results must not influence selection.
- **Library pins**: Python 3.12, `numpy==2.3.3`, `scipy==1.16.2`, `pandas==2.3.3`, `scikit-learn==1.7.2`, `pytest==8.4.2`.

**Additional precise contract:**

- Preserve original CSV row order and original feature-column order. Apply `train_test_split` to row positions and use its returned training-position order unchanged when assigning CV folds. Do not sort rows before splitting or sort the training partition before CV.
- Model identifiers in every file are exactly `logistic_regression`, `random_forest`, `gradient_boosting`. All numeric arrays use float64 native defaults; probability comparisons use absolute tolerance 1e-6 and rtol=0.
- `metrics.json` has top-level keys `models` (an object keyed by the three model identifiers, with the named metrics as fields), `selected_model`, and `selection_rule`. Selection uses the arithmetic mean of five fold AUCs, with the listed model order as the tie-break; pooled OOF AUC is not an equivalent statistic. Use precision/recall/F1 with positive label 1 and zero_division=0.
- For descriptive EDA only, compute Pearson correlations over all 30 cleaned feature columns and count upper-triangular off-diagonal pairs with abs(r) > 0.9 once. Compute the first-two-component cumulative variance using `StandardScaler` followed by `PCA(svd_solver="full")` over all cleaned rows. This descriptive scaler must never be reused for model training/CV. `eda.json` keys: `class_counts` (B/M), `missing_values` (per original raw column, including the all-empty column), `high_correlation_pairs`, `pca_two_component_variance`.
- `selected_model_report.json` uses the names already specified, with `excluded_columns` containing `id` and the actual spurious column name; diagnosis is the target, not a predictor.
- `report.md` must contain at least 300 words, all three model identifiers, the selected identifier, the seed, and selected mean-CV-AUC, test AUC and test accuracy formatted to six decimal places, with discussion of limitations.
- You must supply `/app/run_pipeline.py` accepting `--data PATH --output-dir PATH` (defaults `/app/data/data.csv` and `/app/results`), writing the machine-readable artifacts there and `report.md` beside the output directory. The pipeline must be re-runnable end-to-end from the shell.

## Entry Points

- Raw data: `/app/data/data.csv` (569 rows; header `id,diagnosis,<30 numeric features>`; the header line ends with a trailing comma, which most CSV readers surface as a spurious empty-named column — inspect and handle it).
- Target column: `diagnosis` (`M` = malignant = 1, `B` = benign = 0).
- Work in `/app` (or a subdirectory you create). Python 3.12 with the pinned packages above is available; `uv` and `tmux` are pre-installed.
- Everything must run from the shell (no notebook interface).

## Required output schema (machine-readable, under `/app/results/`)

- `results/oof_predictions.csv` — one row per (training id, model), 1365 rows total: columns `id`, `model`, `fold` (0–4), `y_true`, `y_pred`, `y_proba`. Three rows per training id (one per model). `y_proba` is the OOF probability for that row under that model.
- `results/test_predictions.csv` — one row per (test id, model), 342 rows total: columns `id`, `model`, `y_true`, `y_pred`, `y_proba`. Three rows per test id. `y_proba` is the held-out probability from a model fit on the full training partition.
- `results/folds.csv` — one row per training id: `id`, `fold` (0–4). (Optional if fold membership is unambiguously recoverable from `oof_predictions.csv`, but the verifier will not rely on it.)
- `results/metrics.json` — for each of the three models: `cv_roc_auc_mean`, `cv_roc_auc_per_fold` (5 values), `cv_accuracy`, `cv_precision`, `cv_recall`, `cv_f1` (from OOF predictions), `test_roc_auc`, `test_accuracy`, `test_precision`, `test_recall`, `test_f1`; plus `selected_model` and `selection_rule` (a string describing "mean training-fold ROC-AUC, tie-break order LR → RF → GB").
- `results/selected_model_report.json` — `selected_model`, `cv_roc_auc_mean`, `test_roc_auc`, `test_accuracy`, `label_mapping` (`{"B": 0, "M": 1}`), `random_state`, `n_train`, `n_test`, `feature_count` (30), `excluded_columns` (`["id", "<the spurious empty column name>"]`).
- `results/eda.json` — class balance (counts of B and M), number of missing values per column, count of feature pairs with |Pearson r| > 0.9, cumulative variance explained by the first two principal components.
- `report.md` — human-readable: data-quality issues found and how each was handled, the label mapping, the split/fold rule as executed, why each model family was included, the comparison table, the selection decision and tie-break, and interpretation of which cytological features drive malignancy prediction (feature importance for the selected model is welcome but not graded).

## Acceptance Criteria

- All files above exist, parse, and conform to the schemas (row counts: 455 training ids × 3 models = 1365 OOF rows; 114 test ids × 3 models = 342 test rows).
- Every training `id` appears exactly once per model in OOF output, and every test `id` exactly once per model in test output; no duplicates, no missing ids, no ids outside the raw file.
- All `y_proba` values are finite and in [0, 1]; `y_pred` equals `(y_proba >= 0.5)`; `y_true` matches the raw labels for those ids under the published mapping.
- `metrics.json` values are **recomputed-consistent**: recomputing each metric from the corresponding predictions file reproduces the reported value within `1e-6`.
- The selected model is the argmax of mean training-fold ROC-AUC under the declared tie-break.
- `report.md` documents the protocol as executed and its headline numbers agree with `metrics.json`.
- The whole pipeline runs on 1 CPU in five minutes.

## Environment Constraints

- Single CPU, 2 GB RAM; no GPU. One worker/thread (`n_jobs=1`) throughout.
- No internet required (data is local); pinned packages are pre-installed.
- No deep learning; classical ML only. Modest model sizes (≤ 100 trees).

## Visible Paths

- `/app/data/data.csv` — the only input file
- `/app/` — working directory; expected outputs under `/app/results/` and `/app/report.md`
