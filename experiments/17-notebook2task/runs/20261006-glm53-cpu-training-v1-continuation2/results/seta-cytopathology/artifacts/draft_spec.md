## Task

Execute a fixed, fully reproducible CPU model-comparison protocol on real breast-cancer fine-needle-aspirate cytopathology data: train logistic regression, random forest, and gradient boosting under one published split/fold rule, select the winner by mean training-fold ROC-AUC only, and emit per-model out-of-fold and held-out probabilities, recomputed CV/test metrics, and a selected-model report that an independent verifier can regenerate and match.

## Agent-Visible Task Brief

**Goal**: Working from a raw clinical CSV of digitized fine-needle-aspirate (FNA) measurements, run a **fixed, reproducible three-model comparison** and produce artifacts an independent verifier can regenerate exactly. This is NOT open-ended model optimization: the protocol below is mandatory and is published precisely so that results are reproducible and independently checkable. The deliverables are:

1. A clean, analysis-ready dataset derived from the raw CSV (spurious empty column removed, patient identifier excluded, decisions documented).
2. Exactly **three model families** — logistic regression, random forest, gradient boosting — trained under the published protocol.
3. Per-model **out-of-fold (OOF) probabilities** for every training row, **held-out test probabilities** for every test row, fold assignments, and recomputed CV/test metrics — all keyed by original row `id`.
4. A **selected-model report** naming the winner, chosen **by mean training-fold ROC-AUC only** (test outcomes must not decide selection), with a declared deterministic tie-break.
5. A human-readable `report.md` explaining the data cleaning, the protocol, and the comparison.

**Published protocol (mandatory — these values define reproducibility, so they are given to you explicitly):**

- **Label mapping**: `diagnosis` → `B` = 0 (negative), `M` = 1 (positive). Record this mapping in your artifacts.
- **Feature set**: all 30 numeric measurement columns. **Exclude** `id` (patient/case identifier, no predictive meaning) and the spurious trailing empty-named column (the header line ends with a comma, so most CSV readers surface a 33rd all-empty column — inspect and drop it).
- **Train/test split**: stratified, `test_size = 0.2`, `random_state = 20250607`, `shuffle = True`, on the label-mapped target. Test set = the held-out rows.
- **Cross-validation on the training partition**: 5-fold `StratifiedKFold` with `shuffle = True`, `random_state = 20250607`, `n_splits = 5`. **Fold assignment rule**: the fold index for a training row is the index of the test-fold it falls into when iterating `skf.split(X_train, y_train)` in order (fold 0, 1, 2, 3, 4). Each training row gets exactly one OOF probability from the fold in which it was held out.
- **Preprocessing**: standardization (`StandardScaler`) fit **separately within each training fold** via a `sklearn.pipeline.Pipeline`, never fit before splitting. Tree models (random forest, gradient boosting) use raw features without scaling; logistic regression uses `StandardScaler` inside its pipeline. No other preprocessing (no imputation, feature selection, or resampling — the data has no real missing values).
- **Model hyperparameters (exact, all defaults except those listed)**:
  - `LogisticRegression(max_iter=1000, solver="lbfgs", random_state=20250607)` in a `Pipeline` with `StandardScaler()`.
  - `RandomForestClassifier(n_estimators=100, random_state=20250607, n_jobs=1)` on raw features.
  - `HistGradientBoostingClassifier(random_state=20250607)` on raw features. (If you use a different gradient-boosting implementation, you must document it in `report.md`; the verifier compares against `HistGradientBoostingClassifier` as declared here.)
- **Threads**: one worker / `n_jobs=1` throughout, for determinism.
- **Metrics**: ROC-AUC, accuracy, precision, recall, F1 (positive class = `M` = 1). CV metrics are computed from the OOF probabilities over the whole training partition; test metrics from the held-out probabilities.
- **Selection**: best model = highest **mean training-fold ROC-AUC** (i.e., the mean of the 5 per-fold ROC-AUC values, or equivalently the OOF ROC-AUC — declare which you use). **Tie-break (deterministic)**: if two models' mean CV ROC-AUC are exactly equal, prefer in the order logistic regression → random forest → gradient boosting. Test-set results must not influence selection.
- **Library pins**: Python 3.12, `numpy==2.3.3`, `scipy==1.16.2`, `pandas==2.3.3`, `scikit-learn==1.7.2`, `pytest==8.4.2`.

**Entry Points**:
- Raw data: `/app/data/data.csv` (569 rows; header `id,diagnosis,<30 numeric features>`; the header line ends with a trailing comma, which most CSV readers surface as a spurious empty-named column — inspect and handle it).
- Target column: `diagnosis` (`M` = malignant = 1, `B` = benign = 0).
- Work in `/app` (or a subdirectory you create). Python 3.12 with the pinned packages above is available; `uv` and `tmux` are pre-installed.
- Everything must run from the shell (no notebook interface).

**Required output schema (machine-readable, under `/app/results/`):**

- `results/oof_predictions.csv` — one row per **training** row (455 rows): columns `id`, `model`, `fold` (0–4), `y_true`, `y_pred`, `y_proba`. Three rows per training id (one per model). `y_proba` is the OOF probability for that row under that model.
- `results/test_predictions.csv` — one row per **test** row (114 rows): columns `id`, `model`, `y_true`, `y_pred`, `y_proba`. Three rows per test id. `y_proba` is the held-out probability from a model fit on the full training partition.
- `results/folds.csv` — one row per training id: `id`, `fold` (0–4). (Optional if fold membership is unambiguously recoverable from `oof_predictions.csv`, but the verifier will not rely on it.)
- `results/metrics.json` — for each of the three models: `cv_roc_auc_mean`, `cv_roc_auc_per_fold` (5 values), `cv_accuracy`, `cv_precision`, `cv_recall`, `cv_f1` (from OOF predictions), `test_roc_auc`, `test_accuracy`, `test_precision`, `test_recall`, `test_f1`; plus `selected_model` and `selection_rule` (a string describing "mean training-fold ROC-AUC, tie-break order LR → RF → GB").
- `results/selected_model_report.json` — `selected_model`, `cv_roc_auc_mean`, `test_roc_auc`, `test_accuracy`, `label_mapping` (`{"B": 0, "M": 1}`), `random_state`, `n_train`, `n_test`, `feature_count` (30), `excluded_columns` (`["id", "<the spurious empty column name>"]`).
- `results/eda.json` — class balance (counts of B and M), number of missing values per column, count of feature pairs with |Pearson r| > 0.9, cumulative variance explained by the first two principal components.
- `report.md` — human-readable: data-quality issues found and how each was handled, the label mapping, the split/fold rule as executed, why each model family was included, the comparison table, the selection decision and tie-break, and interpretation of which cytological features drive malignancy prediction (feature importance for the selected model is welcome but not graded).

**Acceptance Criteria**:
- All files above exist, parse, and conform to the schemas (row counts: 455 training ids × 3 models = 1365 OOF rows; 114 test ids × 3 models = 342 test rows).
- Every original `id` appears exactly once per model in each predictions file; no duplicates, no missing ids, no ids outside the raw file.
- All `y_proba` values are finite and in [0, 1]; `y_pred` equals `(y_proba >= 0.5)`; `y_true` matches the raw labels for those ids under the published mapping.
- `metrics.json` values are **recomputed-consistent**: recomputing each metric from the corresponding predictions file reproduces the reported value within `1e-6`.
- The selected model is the argmax of mean training-fold ROC-AUC under the declared tie-break.
- `report.md` documents the protocol as executed and its headline numbers agree with `metrics.json`.
- The whole pipeline runs on 1 CPU in well under 30 minutes (in practice: seconds to a couple of minutes).

**Environment Constraints**:
- Single CPU, 2 GB RAM; no GPU. One worker/thread (`n_jobs=1`) throughout.
- No internet required (data is local); pinned packages are pre-installed.
- No deep learning; classical ML only. Modest model sizes (≤ 100 trees).

**Visible Paths**:
- `/app/data/data.csv` — the only input file
- `/app/` — working directory; expected outputs under `/app/results/` and `/app/report.md`

## Builder-Only Notes

**Hidden Details** (oracle reference values — never copy into instruction.md):

```json
{
  "dataset_shape": [569, 33],
  "raw_columns": ["id", "diagnosis", 30 numeric features, ""],
  "trailing_empty_column": "header ends with a comma -> pandas names the last column 'Unnamed: 32', entirely empty",
  "target_name": "diagnosis",
  "target_classes": {"B": 357, "M": 212},
  "class_ratio": "62.7% benign / 37.3% malignant",
  "missing_values": "zero real missing values; only the spurious all-empty 'Unnamed: 32' column",
  "leakage_column": "id (patient/case identifier, no predictive meaning — must be excluded from features)",
  "split": {"test_size": 0.2, "random_state": 20250607, "stratified": true, "n_train": 455, "n_test": 114},
  "cv": {"n_splits": 5, "StratifiedKFold": true, "shuffle": true, "random_state": 20250607},
  "models": {
    "logistic_regression": "Pipeline(StandardScaler, LogisticRegression(max_iter=1000, solver=lbfgs, random_state=20250607))",
    "random_forest": "RandomForestClassifier(n_estimators=100, random_state=20250607, n_jobs=1)",
    "gradient_boosting": "HistGradientBoostingClassifier(random_state=20250607)"
  },
  "selection_rule": "argmax mean training-fold ROC-AUC; tie-break LR -> RF -> GB",
  "expected_test_accuracy_range": [0.93, 1.00],
  "expected_test_auc_range": [0.95, 1.00],
  "expected_cv_auc_mean_range": [0.95, 1.00],
  "top_features_reference": [
    "perimeter_worst", "area_worst", "concave points_worst", "radius_worst",
    "concavity_mean", "concavity_worst", "area_se", "concave points_mean",
    "texture_worst", "area_mean"
  ],
  "highly_correlated_pairs_abs_r_gt_0.9": "approximately 40-45 pairs (the radius/perimeter/area triads within each of mean/se/worst blocks)",
  "pca_first_two_components_cumulative_variance": "approximately 0.632 (63.2%)",
  "seed_notebook_split": "70/30 with set.seed(314) — NOT used here; the task's split is the published 80/20 @ 20250607",
  "models_in_seed_notebook": ["RandomForest(500 trees)", "GBM", "LightGBM", "XGBoost"],
  "seed_notebook_best_model": "GBM",
  "numeric_tolerance": "1e-6 for probability and metric comparisons (measured; sklearn on this data is deterministic to ~1e-12, so 1e-6 is a safe published bound)"
}
```

**Verifier design (builder-only — this is what `tests/` implements; never reveal to the solver):**

The verifier never trusts solver-supplied ground truth, fold assignments, metrics, model names alone, or any optional training-id file. It:

1. Loads its own trusted copy of the data from `tests/data.csv` (staged by the parent, never from the solver-visible `/app/data/`), reproduces the cleaning (drop empty column, drop `id`, map B→0/M→1).
2. Regenerates the split and folds with the published parameters (`train_test_split` stratified 0.2 @ 20250607; `StratifiedKFold(5, shuffle=True, random_state=20250607)` on the training partition).
3. Refits the three declared native algorithms from scratch (one worker) and computes reference OOF and test probabilities.
4. Compares the solver's `oof_predictions.csv` and `test_predictions.csv` probabilities against the reference within `1e-6`, keyed by `id` and `model`.
5. Independently recomputes every metric in `metrics.json` from the solver's own prediction files and checks self-consistency within `1e-6`.
6. Checks exact row coverage (455 train ids × 3 models; 114 test ids × 3 models), label mapping, split/fold membership against the regenerated reference, finiteness/range of probabilities, and absence of duplicate/missing ids.
7. Checks the selection: `selected_model` is the argmax of mean training-fold ROC-AUC under the declared tie-break, computed from the solver's own OOF probabilities.
8. Runs adversarial component checks (see Testing) and records per-component pass/fail.

**Dependency Chain** (why the oracle scripts steps in this order):

1. **Data quality before modeling** — the spurious empty column and the `id` column must be identified and dropped *before* any split/fit; otherwise the empty column breaks scale-sensitive models and `id` corrupts importance rankings and id-keyed joins.
2. **Split before any fitted preprocessing** — scaling must be fit inside each training fold (Pipeline), never before splitting, so OOF/test probabilities are honest. The verifier's leaky-preprocessing check catches violations.
3. **Folds before OOF probabilities** — the fold assignment rule must be executed before per-row OOF probabilities can be emitted; the verifier regenerates folds independently and compares membership.
4. **All three models before selection** — the comparison (mean training-fold ROC-AUC per model) must exist before a winner can be declared; test outcomes must not decide selection.
5. **Predictions before metrics** — `metrics.json` values must be recomputed from the emitted prediction files, not asserted; the verifier recomputes them independently.
6. **Metrics before report claims** — `report.md` numbers must match `metrics.json`; the verifier cross-checks to catch fabrication.

## Instructions

Construct the environment and oracle as follows:

- **Stage the data twice, separately**: the parent (Dockerfile/build context) copies the seed's `datasets/data/data.csv` **verbatim** to `/app/data/data.csv` (solver-visible) and to `tests/data.csv` (verifier-only trusted copy). Do NOT clean either copy — the trailing-comma header artifact and the `id` column are intentional wrinkles the agent must discover. The Dockerfile must **not** copy `tests/` or `solution/` into the solver image; `tests/` is mounted/run only at test time.
- **Do not pre-install** a solution script, notebook, or cleaned copy of the data anywhere the agent can find. Never embed fabricated sample data or the source notebook/solution in the solver image.
- **Provide** Python 3.12 with `numpy==2.3.3`, `scipy==1.16.2`, `pandas==2.3.3`, `scikit-learn==1.7.2`, `pytest==8.4.2`. `uv` and `tmux` pre-installed per platform defaults.
- **Oracle solution** (`solution/solve.sh`): a Python pipeline that (a) loads the CSV, drops the spurious empty column and `id`, maps `diagnosis` B→0/M→1; (b) records EDA facts to `results/eda.json`; (c) performs the published stratified 80/20 split @ 20250607; (d) runs the published 5-fold StratifiedKFold CV on the training partition for each of the three declared models, collecting OOF probabilities keyed by original `id` and fold; (e) fits each model on the full training partition and predicts held-out probabilities for the test rows; (f) recomputes CV and test metrics from those prediction files into `results/metrics.json`; (g) selects the best model by mean training-fold ROC-AUC with the declared tie-break and writes `results/selected_model_report.json`; (h) writes `report.md` with the required sections. The oracle must run with one worker and comfortably fit 1 CPU / 2 GB / 5 minutes — measure and record its runtime and peak memory.
- **Multiple valid implementations, one fixed protocol**: the agent may structure code, file layout, and helper tooling however it likes, and may add extra diagnostics — but the protocol values (split, folds, models, hyperparameters, label mapping, selection rule) are fixed and published. The verifier compares numerical outputs, not code.
- **What to make non-trivial**: the raw file's trailing-comma header (spurious column), the `id` column (leakage trap), the strong multicollinearity (radius/perimeter/area near-duplicates), the 63/37 class imbalance, and — above all — getting the fold-assignment and OOF-keying mechanics exactly right so an independent regeneration matches within `1e-6`. None of the data wrinkles are called out in the data documentation the agent sees; the protocol values ARE published (per the recipe revision, reproducibility-defining config is agent-visible).
- **Adversarial validation set (builder prepares, runs as pytest components)**: an empty submission, perfect-label predictions (y_proba ∈ {0,1} matching y_true), shuffled ids, fabricated CV metrics, and intentionally leaky preprocessing (scaler fit on the full dataset before splitting). Each must be rejected by the verifier with a recorded component failure. These are validation harness components, not solver-visible material.

## Source Context

- `/app/seeds/seta-cytopathology/kernel-metadata.json` — title "Breast Cancer Prediction from Cytopathology Data"; R Markdown source (`analysis.Rmd`), not ipynb.
- `/app/seeds/seta-cytopathology/analysis.Rmd` (read in full) — established the core objective and reference values: WDBC FNA cytology dataset (30 features = mean/SE/worst of 10 nucleus measurements), PCA (PC1+PC2 = 63.3% variance), 70/30 split with `set.seed(314)`, four models (RF 500 trees, GBM with 5-fold CV, LightGBM with 5-fold CV, XGBoost), confusion matrix + AUC evaluation, RF variable importance naming `perimeter_worst`, `area_worst`, `concave points_worst`, `radius_worst`, `concavity_mean`, `concavity_worst`, `area_se`, `concave points_mean` as most important, a reduced-feature experiment (AUC dropped to 0.940), a 0.3/0.3/0.4 weighted ensemble, and the conclusion that GBM performed best.
- `/app/seeds/seta-cytopathology/datasets/data/manifest.json` — confirmed 569 rows, 33 columns including the trailing empty-name column, 125 KB (well within limits).
- `/app/seeds/seta-cytopathology/datasets/data/data.csv` (header + rows read) — confirmed the quoted header ends with a trailing comma (spurious 33rd column), `M`/`B` string labels, and the `id` column format.

Design choices driven by the source and the recipe revision: the task preserves the notebook's core capability (diagnostic classification with model comparison on real cytopathology data) while replacing the notebook's free-choice model selection with a **fixed, published, reproducible protocol** (LR / RF / GB, one split, one fold rule, selection by training-fold ROC-AUC only). This is a deliberate **loss of openness** relative to both the notebook and a generic "explore and choose" task: the agent's job is correct, leak-free, exactly-reproducible execution and honest artifact generation, not model optimization. The verifier independently regenerates everything from a trusted data copy, so the task grades a reproducible comparison rather than tuned holdout performance. The observed public dataset is not a private or novel evaluation distribution; no hidden-label security or benchmark novelty is claimed. Task difficulty and scientific validity remain unestablished until execution.

## Environment Setup

- **Base image**: `python:3.12-slim` (Ubuntu-based, ~150–250 MB).
- **apt**: none required beyond base.
- **pip (pinned)**: `numpy==2.3.3`, `scipy==1.16.2`, `pandas==2.3.3`, `scikit-learn==1.7.2`, `pytest==8.4.2`.
- **Pre-installed per platform**: `uv`, `tmux`.
- **Pre-seeded files**:
  - `/app/data/data.csv` — verbatim copy of the seed dataset (trailing-comma header artifact intact), staged by the parent.
  - `tests/data.csv` — separate trusted verifier copy, staged by the parent before execution; **not** copied into the solver image by the Dockerfile.
  - No other files; `/app/results/` is created by the agent.
- **No services to run**; pure CLI + file I/O.
- **Resource check**: 569×33 numeric data; three sklearn models with 5-fold CV on one worker — reference run fits 1 CPU / 2 GB / well under 5 minutes (measure and record actual runtime and peak memory at build-validation time).

## Reasoning Steps Required

1. Locate and inspect the raw data file (`ls`, `head`, `wc -l`) to confirm its location and general shape.
2. Load the CSV into a data frame and inspect schema: column names, dtypes, dimensions.
3. **Discover data-quality issues**: the spurious empty-named column from the trailing header comma, and the `id` identifier column.
4. **Handle** each issue per the published protocol (drop the empty column; exclude `id` from features, retaining it only as the row key) and document why `id` must not be a predictor.
5. Encode the target (`diagnosis` M→1 / B→0) exactly as published and record the mapping and class balance (357 B / 212 M).
6. Check for missing values and dtypes across all 30 feature columns; confirm no imputation is needed (verify rather than assume).
7. Explore feature distributions and scale differences (raw ranges span ~0.002 to ~4254) and note which models need scaling (only logistic regression, inside its pipeline).
8. Compute the feature correlation matrix and quantify redundancy (pairs with |r| > 0.9 — the radius/perimeter/area triads).
9. Run PCA on the standardized features and record the cumulative variance explained by PC1+PC2 (~63%) as an EDA finding.
10. Perform the published stratified 80/20 split (`test_size=0.2`, `random_state=20250607`) and confirm 455/114 row counts and stratification.
11. Construct the published 5-fold `StratifiedKFold(shuffle=True, random_state=20250607)` on the training partition and assign each training row a fold index 0–4 per the published fold-assignment rule.
12. Build model 1 (logistic regression in a `Pipeline` with `StandardScaler`, scaling fit inside each training fold) and collect OOF probabilities for all 455 training rows keyed by `id` and fold.
13. Build model 2 (random forest, 100 trees, raw features) and collect OOF probabilities under the same folds.
14. Build model 3 (gradient boosting, raw features) and collect OOF probabilities under the same folds.
15. Fit each of the three models on the full training partition and predict held-out probabilities for the 114 test rows.
16. Recompute CV metrics (per-fold and OOF ROC-AUC, accuracy, precision, recall, F1) and test metrics from the emitted prediction files; write `results/metrics.json`.
17. **Select** the best model by mean training-fold ROC-AUC only, applying the declared tie-break (LR → RF → GB); verify test outcomes did not influence the choice.
18. Write `results/selected_model_report.json` with the selection, headline metrics, label mapping, seed, and excluded columns.
19. Check the class-imbalance implication: recall on the malignant class specifically, and discuss the cost of false negatives in `report.md`.
20. Extract feature importance (or coefficients) from the selected model and interpret the top cytological predictors against the correlation/PCA findings (size/shape "worst" features dominating).
21. Write all machine-readable artifacts (`oof_predictions.csv`, `test_predictions.csv`, `folds.csv`, `metrics.json`, `selected_model_report.json`, `eda.json`) conforming exactly to the published schemas.
22. Write `report.md` documenting the protocol as executed, the comparison table, limitations, and interpretation.
23. Re-run the pipeline (or a verification pass) to confirm the reported probabilities and metrics are bit-reproducible with the recorded seed.

**Total: 23 steps → medium difficulty.**

## Testing

All tests are Python (`pytest`), live under `tests/` (separate from the solver-visible environment), and run inside the container after the agent finishes. The verifier loads the agent's artifacts and **independently regenerates** ground truth from its own trusted copy `tests/data.csv` — it never relies on solver-supplied ground truth, fold assignments, metrics, model names alone, or an optional training-id file. Each test records a component pass/fail.

1. **Artifacts exist, parse, and have exact row coverage**: `results/oof_predictions.csv` has exactly 1365 rows (455 train ids × 3 models), `results/test_predictions.csv` exactly 342 rows (114 test ids × 3 models), `results/metrics.json`, `results/selected_model_report.json`, `results/eda.json`, and `report.md` all exist and parse. Assert the counts explicitly (no vacuous passes on empty files).
2. **Row/key integrity**: every `id` in each predictions file is unique per model, is a subset of the raw file's ids, and the union over models covers exactly the 455 training / 114 test ids with no duplicates and no missing ids; `y_true` for each id matches the raw label under the published B→0/M→1 mapping exactly (catches label corruption and shuffled ids).
3. **Split and fold membership verified against independent regeneration**: the verifier regenerates the stratified 80/20 split @ 20250607 and the 5-fold StratifiedKFold @ 20250607 from `tests/data.csv` and asserts the solver's train/test id sets and per-id fold assignments match exactly.
4. **Probabilities are valid and match the independent reference**: all `y_proba` are finite and in [0, 1]; `y_pred == (y_proba >= 0.5)`; the verifier refits the three declared native algorithms from its trusted data copy with one worker and compares the solver's OOF and test probabilities within `1e-6`, keyed by (`id`, `model`). Accept close floating differences, not broad performance thresholds.
5. **Metrics are recomputed-consistent**: the verifier recomputes ROC-AUC, accuracy, precision, recall, and F1 from the solver's own `oof_predictions.csv` and `test_predictions.csv` and asserts they reproduce the corresponding `metrics.json` values within `1e-6`; per-fold CV values are present (5 per model) and are consistent with the fold-keyed OOF rows.
6. **Selection is rule-consistent**: `selected_model` equals the argmax of mean training-fold ROC-AUC computed from the solver's own OOF probabilities, with the declared LR → RF → GB tie-break; the selection does not depend on test metrics.
7. **Three distinct model families really compared**: `metrics.json` contains all three declared models with distinguishable OOF probability vectors (not three copies of identical numbers) — verified by comparing the actual probability columns, not model-name strings.
8. **Leakage rejection (adversarial)**: a component that fits the scaler (or any preprocessing) on the full dataset before splitting, or trains on test rows, must produce probabilities that fail the `1e-6` reference match in test 4 — the verifier includes an intentionally leaky reference variant and asserts it is *rejected* by the same comparison (i.e., the tolerance genuinely discriminates honest from leaky pipelines).
9. **Fabrication rejection (adversarial)**: empty submission, perfect-label predictions (`y_proba` ∈ {0,1} equal to `y_true`), shuffled ids, and fabricated CV metrics each fail at least one of tests 1–5, and the verifier records the component failure. These harness cases must not silently pass.
10. **EDA facts and report quality**: `eda.json` class counts are exactly {B: 357, M: 212}; the missing-value report is consistent with the raw file (0 real missing after the spurious column is excluded); the high-correlation pair count is ≥ 30 pairs with |r| > 0.9; PC1+PC2 cumulative variance is in [0.55, 0.70]. `report.md` is ≥ 300 words, names the selected model, states the random seed and label mapping, discusses class imbalance / false-negative cost, and its headline metrics agree with `metrics.json` within 0.01. No top-feature overlap requirement and no nonzero-CV-variance requirement is enforced.

## Difficulty

medium

## Core Skills Tested

- Executing a fixed scientific protocol exactly and reproducibly (seeds, splits, fold assignment, hyperparameters)
- Exploratory data analysis on a raw, imperfect CSV (schema inspection, artifact detection)
- Data-cleaning judgment: spurious columns, identifier leakage, categorical target encoding
- Leakage-free preprocessing (scaling fit inside each training fold via Pipeline, never before splitting)
- Out-of-fold prediction mechanics: keying OOF probabilities by original row id and fold
- Training and comparing three classical ML model families under a common CV protocol
- Metric computation and interpretation (accuracy, precision, recall, F1, ROC-AUC) under class imbalance
- Model selection by training-fold evidence only, with a declared deterministic tie-break
- Reproducibility engineering (fixed seeds, pinned libraries, one worker, re-runnable pipeline)
- Machine-readable + human-readable artifact production (CSV/JSON schemas + report)
- Honest reporting: metrics recomputed from emitted predictions, not asserted

## Key Technologies

- Python 3.12 (pandas 2.3.3, numpy 2.3.3, scipy 1.16.2, scikit-learn 1.7.2)
- `sklearn.pipeline.Pipeline`, `StratifiedKFold`, `train_test_split`, `LogisticRegression`, `RandomForestClassifier`, `HistGradientBoostingClassifier`
- Bash / CLI file operations
- JSON and CSV artifact generation with exact schemas
- pytest 8.4.2 for independent verification

## External Resources

No web research was needed — the task uses only standard pandas/scikit-learn APIs (CSV loading, `train_test_split`, `StratifiedKFold`, `Pipeline`, `roc_auc_score`, PCA), which are covered by training data. All reference values were extracted directly from the seed files listed under Source Context.
