# Breast Cancer FNA Cytopathology: Fixed Three-Model Comparison

## Data quality and cleaning

The raw file `/app/data/data.csv` holds 569 cases of digitized fine-needle-aspirate
measurements. Inspection of the schema surfaced two issues. First, the header line ends with a
trailing comma, so the CSV reader exposes a spurious 33rd column (`Unnamed: 32`) that is
entirely empty; it carries no information and was dropped. Second, the `id` column is a
patient/case identifier with no predictive meaning; it was excluded from the feature set and
retained only as the row key so that every prediction stays traceable to its original case.
After cleaning, 30 numeric measurement columns remain (mean, standard error
and worst value of ten nucleus measurements). The per-column missing-value audit found no real
missing values anywhere in the retained columns; the only nulls in the raw file belong to the
spurious empty column, so no imputation was performed. Feature scales span several orders of
magnitude (roughly 0.002 to 4254), which matters for the regularized linear model but not for
the tree models.

## Label mapping and class balance

The target `diagnosis` was mapped exactly as published: B = 0 (benign, negative) and M = 1
(malignant, positive). The class balance is 357 benign versus
212 malignant cases, a 63/37 split. This imbalance is why recall on the
malignant class and the cost of a false negative matter clinically: a missed malignancy
(delayed diagnosis) is far more costly than a benign case flagged for follow-up, so accuracy
alone would flatter a model that leans on the majority class.

## Protocol as executed

The published protocol was followed exactly, with one worker/thread throughout. The split was
a stratified train/test split with test_size = 0.2 and random_state = 20250607, applied to row
positions of the original CSV order, giving 455 training and 114 test
cases. Cross-validation on the training partition used 5-fold StratifiedKFold with shuffle =
True and random_state = 20250607; the fold index of a training row is the index of the test-fold
it falls into when iterating `skf.split(X_train, y_train)` in order. Standardization for
logistic_regression was fit separately inside each training fold via a sklearn Pipeline, never
before splitting, so every out-of-fold and held-out probability is honest. The random_forest and
gradient_boosting models used raw features without scaling. Descriptive EDA (never reused for
training) counted 21 feature pairs with absolute Pearson correlation
above 0.9 and a first-two-component cumulative variance of 0.632432 from
StandardScaler plus PCA with svd_solver = "full".

## Results

| model | mean CV ROC-AUC | CV accuracy | CV recall | test ROC-AUC | test accuracy | test recall |
| --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | 0.993602 | 0.969231 | 0.935294 | 0.997685 | 0.982456 | 0.952381 |
| random_forest | 0.987307 | 0.951648 | 0.917647 | 0.994544 | 0.956140 | 0.880952 |
| gradient_boosting | 0.987926 | 0.953846 | 0.911765 | 0.998347 | 0.964912 | 0.904762 |

Per-fold training-fold ROC-AUC values were recomputed from the emitted
`oof_predictions.csv`, and all test metrics from `test_predictions.csv`, so every number in
`metrics.json` is recomputed-consistent with the prediction files rather than asserted.

## Selection

The selected model is **logistic_regression**, chosen by mean training-fold ROC-AUC only
(0.993602), with the declared deterministic tie-break order
logistic_regression, then random_forest, then gradient_boosting. Test-set outcomes played no
role in the choice. On the held-out partition the selected model reaches a test ROC-AUC of
0.997685 and a test accuracy of 0.982456.

## Interpretation

All three families were included because they represent genuinely different inductive biases on
the same protocol: a regularized linear boundary (logistic_regression), a bagged ensemble of
axis-aligned trees (random_forest), and a boosted ensemble of shallow trees
(gradient_boosting). For the selected model the most influential cytological features are:

- texture_worst (0.0343)
- concavity_mean (0.0207)
- radius_se (0.0207)
- radius_worst (0.0202)
- symmetry_worst (0.0198)
- compactness_se (0.0193)
- area_worst (0.0189)
- concavity_worst (0.0185)
- concave points_mean (0.0176)
- perimeter_worst (0.0154)

These are dominated by worst-case size and shape measurements, consistent with the strong
multicollinearity among the radius, perimeter and area triads: malignant nuclei are typically
larger and more irregular, so the worst-value summaries carry most of the signal.

## Limitations

The comparison is deliberately fixed rather than tuned: no hyperparameter search, feature
selection, or resampling was performed, so the ranking reflects the published configuration
only, not each family's ceiling. The dataset is small (569 cases) and the 63/37 class
imbalance means the recall estimate on the malignant class has non-trivial uncertainty; the
confidence intervals around the fold AUCs overlap across models, so the selection should be read
as a protocol outcome, not a claim of clinical superiority. Many features are near-duplicates
(correlation above 0.9), which makes coefficient-scale importance unstable and inflates the
apparent dimensionality of the signal. Finally, this is a diagnostic-support tool on a
convenience sample of FNA measurements; a false negative remains possible and any deployment
would require external validation.
