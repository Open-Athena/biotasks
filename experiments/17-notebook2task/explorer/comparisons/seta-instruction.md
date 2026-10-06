# Breast Cancer Classification from Cytopathology Data

## Goal

Predict whether a breast tumor is malignant (M) or benign (B) from fine needle aspirate (FNA) cell nuclei measurements. You must achieve a test set AUC of at least 0.93, train at least three different classifiers, perform principled feature selection, and build a weighted ensemble. All work must be documented in a structured analysis report.

## Dataset

The dataset is located at `/data/breast-cancer-wisconsin/data.csv`. It contains 569 samples with 32 columns: an `id` column, a `diagnosis` column (M for malignant, B for benign), and 30 numeric features representing mean, standard error, and worst (largest) values for 10 cell nuclei measurements: radius, texture, perimeter, area, smoothness, compactness, concavity, concave points, symmetry, and fractal dimension.

## Required Outputs

All output files must be saved to the `/results/` directory:

1. **`results/predictions.csv`** — Test set predictions from your best individual model with columns: `id`, `true_label`, `predicted_label`, `predicted_proba`

2. **`results/model_comparison.csv`** — Per-model metrics with columns: `model_name`, `accuracy`, `precision`, `recall`, `f1`, `auc`, `cv_mean_auc`, `cv_std_auc`

3. **`results/feature_importance.csv`** — Top features for the best-performing model with columns: `feature`, `importance` (sorted by importance descending)

4. **`results/ensemble_predictions.csv`** — Weighted ensemble predictions with columns: `id`, `true_label`, `predicted_label`, `predicted_proba`

5. **`results/analysis_report.md`** — A structured markdown report covering:
   - Data exploration findings
   - Feature selection rationale
   - Model comparison discussion
   - Ensemble weighting rationale
   - Key insights about which cell nuclei properties are most predictive

## Requirements

- Use 5-fold stratified cross-validation for all models
- Set random seed to 42 for reproducibility
- Use a 70/30 train/test split, stratified by diagnosis
- Train at least three different classifiers
- Build a weighted ensemble from individual model predictions
- All numeric labels should use: malignant = 1, benign = 0

## Environment

- Python 3.11 with scikit-learn, xgboost, lightgbm, pandas, numpy, matplotlib, seaborn available
- Single CPU, no GPU
- Dataset is local at `/data/breast-cancer-wisconsin/data.csv`
- Output directory: `/results/`
