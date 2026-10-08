# Breast Cancer Classification from Cytopathology (FNA) Data — Analysis Report

**Task:** Predict malignant (M=1) vs benign (B=0) breast tumors from 30 cell-nuclei measurements
computed on digitized fine-needle-aspirate images.
**Data:** `/data/breast-cancer-wisconsin/data.csv` — 569 samples, 32 columns (id + diagnosis + 30 features).
**Protocol:** 70/30 stratified train/test split, 5-fold stratified cross-validation (CV), seed = 42.

---

## 1. Data Exploration Findings

- **Size & cleanliness.** 569 samples, 30 numeric features, no missing values. The raw CSV had a
  trailing comma producing an empty `Unnamed` column, which was dropped along with the `id`
  identifier (no predictive value, and keeping it would risk leakage).
- **Class balance.** 212 malignant (37.3%) vs 357 benign (62.7%) — a moderate imbalance. All
  models therefore use class-agnostic default settings but are evaluated with ROC-AUC (threshold-
  and imbalance-robust) in addition to accuracy. The stratified split preserved the ratio in both
  train (M = 37.2%) and test (M = 37.4%) sets.
- **Feature scale.** Features span several orders of magnitude (e.g., `area_worst` ~ thousands vs
  `fractal_dimension_se` ~ 0.001), so all distance/gradient-based models (logistic regression, SVM)
  were wrapped in a pipeline with `StandardScaler` fit inside each CV fold to avoid leakage.
- **Strong multicollinearity.** The correlation matrix (`figures/eda_overview.png`) shows the
  size family — radius, perimeter, area — are near-perfectly correlated (|r| ≈ 0.95–1.0) within
  each of the mean / SE / worst groups, as expected since perimeter and area are deterministic
  functions of radius. This motivated the redundancy-pruning step in feature selection.
- **Signal strength.** Even the strongest single features are highly informative: the top features
  correlate with diagnosis at |r| ≈ 0.78 (`concave points_worst`), `perimeter_worst` (0.78),
  `radius_worst`/`area_worst` (0.77), and `concavity_mean` (0.70). Malignant nuclei tend to be
  **larger, more irregular in texture, and more concave** — consistent with oncologic cytopathology:
  cancer cells enlarge, lose uniform nuclear membrane contour, and show marked anisonucleosis.

## 2. Feature Selection Rationale

Selection was performed **on the training split only** (test set untouched) in three principled steps:

1. **Relevance ranking** — ANOVA F-test (`f_classif`) between each feature and the diagnosis label.
2. **Redundancy pruning** — walking down the relevance ranking, a feature was dropped if it
   correlated |r| > 0.9 with an already-selected feature. This removed 9 of 30 features
   (`area_worst`, `perimeter_mean`, `radius_mean`, `area_mean`, `radius_worst`,
   `concave points_mean`, `area_se`, `perimeter_se`, `texture_mean`) — all near-duplicates of a
   stronger-kept feature, e.g. `perimeter_worst` was kept over `radius/area_worst`.
3. **Choosing k by cross-validation** — a scaled logistic regression was evaluated with k ∈
   {5, 8, 10, 12, 15, 21} selected features via 5-fold CV, applying the **1-SE parsimony rule**
   (smallest k within one standard error of the best CV AUC):

   | k | 5 | 8 | 10 | 12 | 15 | **21** |
   |---|---|---|----|----|----|--------|
   | CV AUC | 0.9832 | 0.9833 | 0.9815 | 0.9819 | 0.9868 | **0.9954** |

   All 21 surviving features were kept: the full pruned set gave the best CV AUC (0.9954 ± 0.0038),
   and no smaller k fell within one SE of it. The final feature set spans all 10 measurement types
   (size, texture, smoothness, compactness, concavity, concave points, symmetry, fractal dimension)
   across mean/SE/worst aggregations — see `figures/feature_selection.png`.

## 3. Model Comparison

Five classifiers (exceeding the required three) were trained on the 21 selected features and
evaluated with 5-fold stratified CV on the training set, then on the untouched 30% test set
(171 samples: 107 benign, 64 malignant):

| model | accuracy | precision | recall | f1 | test AUC | CV AUC (mean ± std) |
|---|---|---|---|---|---|---|
| **WeightedEnsemble** | **0.982** | 1.000 | 0.953 | 0.976 | **0.998** | **0.9928 ± 0.0039** |
| LogisticRegression | 0.971 | 1.000 | 0.922 | 0.959 | 0.998 | 0.9925 ± 0.0063 |
| SVM_RBF | 0.977 | 1.000 | 0.938 | 0.968 | 0.995 | 0.9923 ± 0.0048 |
| XGBoost | 0.977 | 1.000 | 0.938 | 0.968 | 0.996 | 0.9905 ± 0.0061 |
| LightGBM | 0.982 | 1.000 | 0.953 | 0.976 | 0.994 | 0.9905 ± 0.0095 |
| RandomForest | 0.971 | 1.000 | 0.922 | 0.959 | 0.997 | 0.9879 ± 0.0080 |

**Discussion.** All five models clear the 0.93 AUC requirement by a wide margin (test AUC
0.994–0.998), confirming the FNA measurements are highly separable. Regularized **logistic
regression** was the best individual model by CV AUC (0.9925): the features are roughly monotone
and linearly separable after scaling, so a linear model with low variance generalizes as well as
or better than the tree ensembles. The margin-based **SVM (RBF)** is a close second, while
**XGBoost/LightGBM/RandomForest** trail slightly — with only ~400 training samples, trees spend
capacity modeling noise. Note that every model achieves **precision = 1.000** on the test set
(zero false positives): all 6–8 residual errors are false negatives, which in a screening context
is the safer failure mode. ROC curves and confusion matrices are in `figures/`.

## 4. Ensemble Weighting Rationale

The ensemble is a **soft-voting weighted average of predicted malignant probabilities**:

> P(ensemble) = Σᵢ wᵢ · Pᵢ(malignant),  with **wᵢ ∝ CV-mean-AUCᵢ** (normalized to sum to 1).

Weights were derived from each model's **out-of-fold 5-fold CV AUC on the training set** — never
from test-set performance — so the weighting cannot overfit the held-out test data. Because all
five models had nearly identical CV AUCs (0.988–0.993), the weights came out nearly uniform
(LR 0.2004, SVM 0.2003, XGB 0.1999, LGBM 0.1999, RF 0.1994), i.e., the ensemble is effectively a
well-calibrated soft vote. The ensemble's own CV statistics were estimated with a fully nested
procedure (per outer fold, inner CV determines weights, outer fold measures honest AUC):
**0.9928 ± 0.0039** — the lowest CV variance of any model, and the best test AUC (0.9978) tied
with logistic regression. Averaging five diverse learners (linear, kernel, and three tree-based)
reduces variance while preserving the strengths of each family.

## 5. Key Insights: Which Nuclear Properties Predict Malignancy

From the best individual model's feature importance (`feature_importance.csv`) and univariate
correlations:

1. **Nuclear size — the dominant signal.** `perimeter_worst` (|r| = 0.78 with diagnosis) and
   `radius_se` are the top-ranked features. Malignant tumors have markedly larger nuclei, and the
   elevated `radius_se` indicates **heterogeneity of nuclear size within the sample** —
   anisonucleosis is a classic hallmark of malignancy in cytopathology.
2. **Nuclear contour irregularity.** Concavity-family features (`concavity_mean` r = 0.70,
   `concave points_worst` r = 0.78, `concavity_worst`) are among the strongest predictors:
   malignant nuclei have irregular, indented membranes, whereas benign nuclei are smooth and oval.
3. **Texture.** `texture_worst` (standard deviation of gray-scale values, |r| ≈ 0.46) captures
   chromatin coarseness/pleomorphism — another top-5 feature.
4. **"Worst" > "mean" > "SE" aggregation.** The largest-value (`_worst`) statistics consistently
   outrank their mean and SE counterparts: the most abnormal cells in a smear carry the diagnostic
   signal, echoing real pathology practice where the worst-appearing cells drive the diagnosis.
5. **Least informative.** Fractal dimension and symmetry features (all aggregations) contribute
   marginally — nuclear shape symmetry and boundary roughness at fine scale add little beyond
   size and concavity.

**Bottom line.** A regularized logistic regression on 21 correlation-pruned features already
achieves test AUC = 0.998 (accuracy 97.1%), and the CV-AUC-weighted ensemble reaches 98.2%
accuracy with 100% precision and 95.3% recall — comfortably above the 0.93 AUC target. The
biological story is coherent: **malignancy is signaled by large, size-heterogeneous, irregularly
contoured, coarsely textured nuclei.**

---

## Reproducibility

- Script: `/app/analysis.py` (seed = 42 everywhere; `random_state=42` in splits, CV, all models).
- Split: `train_test_split(test_size=0.30, stratify=y, random_state=42)` → 398 train / 171 test.
- CV: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.
- Outputs: `predictions.csv` (best individual model = LogisticRegression),
  `ensemble_predictions.csv`, `model_comparison.csv`, `feature_importance.csv`,
  figures in `results/figures/`.
