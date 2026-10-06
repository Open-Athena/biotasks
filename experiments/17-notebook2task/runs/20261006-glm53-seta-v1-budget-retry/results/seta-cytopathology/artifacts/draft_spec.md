## Task

Build and rigorously evaluate a binary classifier that predicts breast-cancer diagnosis (malignant vs. benign) from fine-needle-aspirate cytopathology measurements, deciding preprocessing, feature selection, and model choice from evidence rather than a fixed recipe.

## Agent-Visible Task Brief

**Goal**: Working from a raw clinical CSV of digitized fine-needle-aspirate (FNA) measurements, produce a reproducible, evidence-driven diagnostic model and a written analysis. The deliverables are:

1. A clean, analysis-ready dataset derived from the raw CSV (data-quality issues found and fixed, decisions documented).
2. At least **three distinct model families** trained and compared on a held-out test set, each with 5-fold cross-validation.
3. A selected best model meeting a **minimum ROC-AUC of 0.95 and minimum test accuracy of 0.93** on the held-out set (the reference analysis reaches ~0.95–0.99 AUC across tree ensembles).
4. A machine-readable results bundle (metrics, per-model CV scores, test predictions, feature importance, correlation/PCA findings) plus a human-readable report explaining every decision.

**Entry Points**:
- Raw data: `/app/data/data.csv` (569 rows; header `id,diagnosis,<30 numeric features>`; note the file has a trailing comma in the header, which most CSV readers surface as a spurious empty-named column — inspect and handle it).
- Target column: `diagnosis` (`M` = malignant, `B` = benign). All other columns except `id` are candidate predictors.
- Work in `/app` (or a subdirectory you create). Python 3 with `pandas`, `numpy`, `scikit-learn` is available; any additional packages can be installed with `uv` or `pip`.
- Everything must run from the shell (no notebook interface).

**Acceptance Criteria**:
- `results/metrics.json` exists and contains, for every trained model: test accuracy, precision, recall, F1, ROC-AUC, and 5-fold CV mean ± std of at least one metric.
- `results/predictions.csv` exists with one row per held-out test observation, containing at minimum: the original row `id`, the true `diagnosis` label (as `M`/`B` or 1/0 — mapping must be documented), and the predicted label AND predicted probability from the selected model.
- `results/feature_importance.csv` exists with feature names and importance scores for the selected model, sorted descending.
- `results/eda.json` exists and records at least: class balance (counts of B and M), number of missing values per column, the count of feature pairs with |Pearson r| > 0.9, and the cumulative variance explained by the first two principal components.
- The best model's test ROC-AUC ≥ 0.95 and test accuracy ≥ 0.93.
- `report.md` exists and documents, with rationale: data-quality issues found and how each was handled, encoding of the target, the train/test split strategy, why each model family was tried, the model comparison, the feature-selection decision, and the final interpretation of which cytological features drive malignancy prediction.
- A random seed is fixed and recorded, and re-running the pipeline reproduces the reported metrics.

**Environment Constraints**:
- Single CPU, 2 GB RAM; no GPU. The whole pipeline (all models + CV) must finish in well under 30 minutes — it should take seconds to a couple of minutes.
- No internet is required (data is local); package installs are permitted if needed.
- No deep learning; classical ML only.

**Visible Paths**:
- `/app/data/data.csv` — the only input file
- `/app/` — working directory; expected outputs under `/app/results/` and `/app/report.md`

## Builder-Only Notes

**Hidden Details** (oracle reference values — never copy into instruction.md):

```json
{
  "dataset_shape": [569, 33],
  "raw_columns": ["id", "diagnosis", 30 numeric features, ""],
  "trailing_empty_column": "header ends with a comma -> pandas names the last column 'Unnamed: 32', entirely NaN",
  "target_name": "diagnosis",
  "target_classes": {"B": 357, "M": 212},
  "class_ratio": "63.3% benign / 37.3% malignant",
  "missing_values": "zero real missing values; only the spurious all-NaN 'Unnamed: 32' column",
  "leakage_column": "id (patient/case identifier, no predictive meaning — must be excluded from features)",
  "expected_test_accuracy_range": [0.93, 1.00],
  "expected_test_auc_range": [0.95, 1.00],
  "expected_cv_auc_mean_range": [0.95, 1.00],
  "top_features_reference": [
    "perimeter_worst", "area_worst", "concave points_worst", "radius_worst",
    "concavity_mean", "concavity_worst", "area_se", "concave points_mean",
    "texture_worst", "area_mean"
  ],
  "highly_correlated_pairs_abs_r_gt_0.9": "approximately 40-45 pairs (the size/perimeter/area triads within each of mean/se/worst blocks)",
  "pca_first_two_components_cumulative_variance": "approximately 0.632 (63.2%)",
  "seed_notebook_split": "70/30 with set.seed(314)",
  "models_in_seed_notebook": ["RandomForest(500 trees)", "GBM", "LightGBM", "XGBoost"],
  "seed_notebook_best_model": "GBM",
  "seed_notebook_ensemble": "0.3*RF + 0.3*GBM + 0.4*XGB weighted average",
  "random_seed_reference": 314
}
```

**Dependency Chain** (why the oracle scripts steps in this order):

1. **Data quality before modeling** — the spurious empty column and the `id` column must be identified and dropped *before* any split/fit; otherwise the empty column breaks scale-sensitive models (imputers/scalers choke on all-NaN) and `id` leaks noise into importance rankings.
2. **EDA before feature selection** — the correlation structure (|r| > 0.9 pairs) and PCA variance concentration must be computed on the cleaned feature matrix; the feature-selection decision (keep all 30 vs. prune redundant size/shape duplicates) is only meaningful once redundancy is quantified.
3. **Split before any fitted preprocessing** — imputation/scaling/feature selection must be fit on the training partition only, then applied to the test partition, so the reported test metrics are honest. The oracle verifies the train/test disjointness and the ~114-row test size.
4. **All models before selection** — the comparison table (and CV evidence) must exist before a "best model" can be declared; the selected model's predictions and importances are derived from that choice.
5. **Predictions before report claims** — `report.md` numbers must match the machine-readable artifacts; the oracle cross-checks report figures against `metrics.json` to catch fabrication.

## Instructions

Construct the environment and oracle as follows:

- **Seed the data**: copy the seed's `datasets/data/data.csv` to `/app/data/data.csv` verbatim (do NOT clean it — the trailing-comma header artifact and the `id` column are intentional wrinkles the agent must discover).
- **Do not pre-install** a solution script, notebook, or cleaned copy of the data anywhere the agent can find.
- **Provide** a Python 3 environment with `pandas`, `numpy`, `scikit-learn` (and `pytest` for tests). `uv` and `tmux` pre-installed per platform defaults.
- **Oracle solution** (`solution/solve.sh`): a Python pipeline that (a) loads the CSV, drops the spurious empty column and `id`, maps `diagnosis` B/M → 0/1; (b) records EDA facts (class counts, per-column nulls, high-correlation pair count, PCA cumulative variance for PC1+PC2) to `results/eda.json`; (c) performs a stratified 80/20 split with a fixed seed; (d) trains ≥3 families — e.g. logistic regression (scaled), random forest, and gradient boosting — each with 5-fold stratified CV on the training partition; (e) evaluates all on the test set (accuracy, precision, recall, F1, ROC-AUC) into `results/metrics.json`; (f) selects the best by CV AUC, writes `results/predictions.csv` (id, y_true, y_pred, y_proba) and `results/feature_importance.csv`; (g) writes `report.md` with the required rationale sections. The oracle must comfortably meet AUC ≥ 0.95 / accuracy ≥ 0.93.
- **Multiple valid solutions**: the agent may choose different models (SVM, k-NN, extra trees, etc.), different feature-selection strategies (all 30 features, correlation pruning, importance-based top-k, PCA components), and different seeds — tests must accept any of these as long as the artifacts are consistent and thresholds are met.
- **What to make non-trivial**: the raw file's trailing-comma header (spurious column), the `id` column (leakage trap), the strong multicollinearity (radius/perimeter/area are near-duplicates within each block), and the 63/37 class imbalance. None of these are called out in the data documentation the agent sees.

## Source Context

- `/app/seeds/seta-cytopathology/kernel-metadata.json` — title "Breast Cancer Prediction from Cytopathology Data"; R Markdown source (not ipynb), which is why the notebook structure came from `analysis.Rmd`.
- `/app/seeds/seta-cytopathology/analysis.Rmd` (read in full) — established the core objective and all reference values: dataset description (30 features = mean/SE/worst of 10 nucleus measurements), class definition, PCA (PC1+PC2 = 63.3% variance), 70/30 split with `set.seed(314)`, four models (RF 500 trees, GBM with 5-fold CV, LightGBM with 5-fold CV, XGBoost with 5-fold CV), confusion matrix + AUC evaluation, RF variable importance naming `perimeter_worst`, `area_worst`, `concave points_worst`, `radius_worst`, `concavity_mean`, `concavity_worst`, `area_se`, `concave points_mean` as most important, a reduced-feature experiment (AUC dropped to 0.940), a 0.3/0.3/0.4 weighted average ensemble, and the conclusion that GBM performed best.
- `/app/seeds/seta-cytopathology/datasets/data/manifest.json` — confirmed 569 rows, 33 columns including the trailing empty-name column, 125 KB (well within limits).
- `/app/seeds/seta-cytopathology/datasets/data/data.csv` (header + sample rows read) — confirmed the trailing comma in the header line, `M`/`B` string labels, and the `id` column format.

Design choices driven by the source: the task preserves the notebook's core capability (evidence-driven diagnostic classification with model comparison) while converting the linear R Markdown flow into an exploratory terminal workflow where the agent must discover the data-quality issues, decide on redundancy handling, and justify model selection. The AUC ≥ 0.95 / accuracy ≥ 0.93 thresholds are calibrated to the notebook's reported results (~0.94–0.99 AUC).

## Environment Setup

- **Base image**: `python:3.12-slim` (or `python:3.13-slim`), Ubuntu-based, ~200 MB.
- **apt**: none required beyond base (optionally `curl` for health checks).
- **pip**: `pandas`, `numpy`, `scikit-learn`, `pytest`. (Optionally `scipy` — pulled in by scikit-learn anyway.)
- **Pre-installed per platform**: `uv`, `tmux`.
- **Pre-seeded files**:
  - `/app/data/data.csv` — verbatim copy of the seed dataset (with trailing-comma header artifact intact).
  - No other files; `/app/results/` is created by the agent.
- **No services to run**; the task is pure CLI + file I/O.
- **Resource check**: 569×33 numeric data, three sklearn models with 5-fold CV — total runtime well under 1 minute on 1 CPU; memory footprint a few tens of MB.

## Reasoning Steps Required

1. Locate and inspect the raw data file (`ls`, `head`, or `wc -l`) to confirm its location and general shape.
2. Load the CSV into a data frame and inspect schema: column names, dtypes, dimensions.
3. **Discover data-quality issues**: the spurious empty-named column from the trailing header comma, and the presence of the `id` identifier column.
4. **Decide** how to handle each issue (drop the empty column; drop or set aside `id` for indexing but exclude from features) and document why `id` must not be a predictor.
5. Encode the target (`diagnosis` M/B → 1/0) and record the mapping and class balance (357 B / 212 M).
6. Check for missing values and dtypes across all feature columns; decide whether any imputation is needed (it is not, but the agent must verify rather than assume).
7. Explore feature distributions and scale differences (raw ranges span ~0.002 to ~4254) and decide which models need scaling.
8. Compute the feature correlation matrix and quantify redundancy (pairs with |r| > 0.9 — the radius/perimeter/area triads).
9. Run PCA on the standardized features and record the cumulative variance explained by PC1+PC2 (~63%) to confirm the notebook's finding.
10. **Decide** a feature strategy: keep all 30 features vs. prune redundant ones, with rationale tied to the correlation/PCA evidence.
11. Perform a stratified train/test split (e.g. 80/20) with a fixed, recorded random seed.
12. Build model 1 (e.g. logistic regression with scaling inside a pipeline) and evaluate with 5-fold stratified CV on the training partition.
13. Build model 2 (e.g. random forest) and evaluate with the same 5-fold CV protocol.
14. Build model 3 (e.g. gradient boosting) and evaluate with the same protocol.
15. Evaluate all three on the held-out test set: accuracy, precision, recall, F1, ROC-AUC (using predicted probabilities for AUC).
16. Compare models on CV and test metrics; **decide** the best model and justify the choice (including the trade-off between interpretability and performance).
17. Check the class imbalance implication: verify recall on the malignant class specifically and discuss the cost of false negatives.
18. Extract feature importance (or coefficients) from the selected model and identify the top predictive features.
19. Cross-check the top features against the correlation/PCA findings (size/shape "worst" features dominating) and interpret them clinically.
20. Write the machine-readable artifacts: `results/metrics.json`, `results/predictions.csv`, `results/feature_importance.csv`, `results/eda.json`.
21. Write `report.md` documenting every decision, the comparison table, limitations, and interpretation.
22. Re-run the pipeline (or a verification pass) to confirm the reported metrics are reproducible with the recorded seed.

**Total: 22 steps → medium difficulty.**

## Testing

All tests are Python (`pytest`) and run inside the container after the agent finishes. Tests must load the agent's artifacts and recompute ground truth from `/app/data/data.csv` independently.

1. **Artifacts exist and are non-empty**: `results/metrics.json`, `results/predictions.csv`, `results/feature_importance.csv`, `results/eda.json`, `report.md` all exist, parse, and contain data (e.g. `predictions.csv` has > 100 rows; `feature_importance.csv` has ≥ 10 rows).
2. **Data-quality handling verified**: `eda.json` (or the feature list in `feature_importance.csv` / predictions columns) shows no empty-named or all-NaN column and no `id` among the features used; re-reading the raw CSV with pandas confirms the agent actually dealt with the trailing-comma artifact rather than silently failing.
3. **Test-set integrity**: the `id` values in `predictions.csv` are a subset of the raw file's ids, are unique, number between 100 and 130 rows (~20% of 569), and are disjoint from the training ids if a train-id artifact is produced (or: the true labels in `predictions.csv` match the raw labels for those ids exactly — catches label corruption).
4. **Metrics are mathematically consistent**: recomputing accuracy, precision, recall, F1, and ROC-AUC from `predictions.csv` (y_true, y_pred, y_proba) reproduces the selected model's reported values in `metrics.json` within 0.005; accuracy equals (TP+TN)/total exactly.
5. **Performance threshold met**: the selected model's test ROC-AUC ≥ 0.95 and test accuracy ≥ 0.93 (the reference analysis's tree ensembles achieve ~0.95–0.99 AUC; a correct pipeline clears this).
6. **Cross-validation actually done**: `metrics.json` contains per-model CV fold results or mean ± std for ≥ 3 models; the fold scores are floats in [0, 1] and at least one model's fold std is > 0 (real CV varies, it is never exactly constant); the CV protocol is 5-fold (5 entries or explicitly documented as such).
7. **Model comparison is real**: at least 3 distinct model families appear in `metrics.json` with distinguishable results (not three copies of identical numbers).
8. **Feature importance is plausible**: the top-5 features in `feature_importance.csv` overlap by ≥ 3 with the reference set {perimeter_worst, area_worst, concave points_worst, radius_worst, concavity_mean, concavity_worst, area_se, concave points_mean, texture_worst, area_mean}; importances are non-negative and sum (or normalize) consistently with the stated method.
9. **EDA facts are correct**: `eda.json` class counts are exactly {B: 357, M: 212}; missing-value report is consistent with the raw file (0 real missing after the spurious column is excluded); the high-correlation pair count is in a plausible range (≥ 30 pairs with |r| > 0.9); PC1+PC2 cumulative variance is in [0.55, 0.70].
10. **Report quality and reproducibility**: `report.md` is ≥ 300 words, names the chosen best model, states the random seed, discusses the class imbalance / false-negative cost, and its headline metrics match `metrics.json` (numbers appearing in the report agree with the JSON within 0.01).

## Difficulty

medium

## Core Skills Tested

- Exploratory data analysis on a raw, imperfect CSV (schema inspection, artifact detection)
- Data-cleaning judgment: spurious columns, identifier leakage, encoding categorical targets
- Multicollinearity detection (correlation matrix) and dimensionality-reduction reasoning (PCA variance interpretation)
- Stratified train/test splitting and leakage-free preprocessing (fit on train only)
- Training and comparing multiple classical ML model families with cross-validation
- Metric computation and interpretation (accuracy, precision, recall, F1, ROC-AUC) under class imbalance
- Feature-importance extraction and clinical interpretation
- Reproducibility engineering (fixed seeds, re-runnable pipeline)
- Machine-readable + human-readable artifact production (JSON/CSV + report)
- Documenting and justifying decisions with evidence

## Key Technologies

- Python 3 (pandas, numpy, scikit-learn)
- Bash / CLI file operations
- JSON and CSV artifact generation
- pytest for validation

## External Resources

No web research was needed — the task uses only the standard pandas/scikit-learn APIs (CSV loading, `train_test_split`, `StratifiedKFold`, `Pipeline`, `roc_auc_score`, PCA), which are covered by training data. All reference values were extracted directly from the seed files listed under Source Context.
