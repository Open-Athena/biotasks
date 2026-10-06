## Task
Build a reproducible terminal evaluation of frozen cytopathology classifiers, compare feature-processing strategies, and select a model for distinguishing malignant from benign breast masses without training models.

## Agent-Visible Task Brief
**Goal**: A research team needs a trustworthy comparison of supplied classifiers for the Wisconsin breast-cancer cytopathology dataset. Produce an executable evaluation, select a candidate using development data, and report its performance on an independent holdout. Explain how preprocessing, correlated measurements, and false negatives affect the choice. This is a retrospective benchmark, not a clinical deployment.

**Entry Points**: `/workspace/data/development.csv`, `/workspace/data/holdout_features.csv`, `/workspace/data/folds.csv`, `/workspace/models/catalog.json`, and `/workspace/reference/analysis.Rmd`. The catalog documents the frozen inference bundles and their feature contracts. `/workspace/CONTRACT.md` describes artifact schemas and the evaluator interface.

**Acceptance Criteria**:
- Audit the development data: schema, class counts, missingness, duplicate identifiers, feature scales, extreme observations, and redundant measurements. Explain which fields should be predictors and how supplied transformations address the observed data.
- Evaluate all four supplied candidates, representing two model families and two preprocessing strategies. Produce one genuine out-of-fold malignant-class probability per development record per candidate using the supplied five-fold assignments and fold-specific models.
- Compare probability-based ROC AUC, accuracy, malignant precision, recall, F1, and confusion matrices. Use malignant as the positive class and a probability threshold of 0.5 for discrete predictions.
- Select the largest mean five-fold ROC AUC; resolve exact ties by lexicographic candidate identifier. Report variability and limitations of this selection estimate. Do not use holdout results to select the candidate.
- Generate holdout probabilities with the selected full-development model. The private evaluator requires holdout ROC AUC at least 0.95 and malignant recall at least 0.85. These thresholds must be validated by the builder before release.
- Measure and explain at least three influential features using a reproducible perturbation analysis on development folds; discuss correlated predictors and avoid causal claims.
- Document at least two measured comparisons and the decisions they support in an incremental experiment journal. Include an audit of the reference notebook's evaluation logic, distinguishing demonstrated code issues from unverified numerical claims.
- Supply a repeatable CLI, development predictions, fold metrics, candidate comparison, selected-model record, feature effects, holdout predictions, and a concise report. A clean rerun must recreate numeric results within stated tolerances.

**Environment Constraints**: Ubuntu 24.04, one CPU, 2 GB RAM, 10 GB disk; under one hour and preferably under 15 minutes for computation. Packages and artifacts are available locally. No network, GPU, model fitting, fine-tuning, or package installation is needed. Only frozen-model inference and bounded statistical calculations are required.

**Visible Paths**: Inputs above are read-only. Work under `/workspace`; deliver outputs under `/workspace/output`. Implement the documented `evaluate` and `predict` interfaces; implementation files and language organization are the agent's choice. `predict` accepts a feature CSV and output path and preserves input row identities and order. `evaluate` accepts the supplied data, fold, and model locations plus a fresh output directory. Required output schemas are public acceptance contracts, not hidden discoveries.

## Builder-Only Notes
**Hidden Details**: The staged CSV is observed data, not images. Its manifest reports 569 rows, 33 raw columns including an unnamed final field, and 125204 bytes. There are 30 intended numeric predictors plus `id` and `diagnosis`. Preserve the original field names, including spaces in `concave points_*`; document name mappings if any. Verify actual contents during Stage 2; no dataset computation was performed during this authoring stage.

Respect the agent-side no-training constraint by preparing frozen artifacts during subsequent builder execution. The Stage 1 pilot permits designing later model preparation, but no fitting, package installation, or biological analysis has been executed now. Artifact preparation is an explicit builder prerequisite, not an assertion that pretrained models are already in the seed.

Suggested artifact bank: logistic regression and a small random forest, each with (a) all 30 features and (b) training-only correlation pruning. Use standardized inputs for logistic regression. Fit every learned transformation solely on each corresponding training partition. Use deterministic settings and one worker. For pruning, process feature names in sorted order and keep a feature only if its absolute Pearson correlation with every previously retained feature is below 0.95. These are builder choices; agents compare their effects rather than reproduce their fitting code. Each candidate has five fold models and one full-development model, 24 small bundles total. Supply accessible inference adapters, class labels, preprocessing descriptions, and provenance. Do not require R, LightGBM, or XGBoost installations merely to reproduce the source stack.

Split the observed source once into 455 development and 114 holdout records using a stratified 80/20 split with seed 314. Construct five stratified development folds with shuffle and seed 314. Store explicit IDs and assignments; tests use these persisted memberships, not assumptions about random-generator equivalence. Builder-generated labels for the holdout remain outside the agent-visible filesystem. Do not copy the full labeled source CSV or a label lookup into the runtime image. Keep every original observation; no planted missing values or invented biological records.

Evaluate the artifact bank privately before release. Verify that the prescribed development selection reaches the stated holdout thresholds. If not, revise the bank and validate again before publishing; do not silently change expected scores or use notebook claims as truth. Record exact package versions, artifact hashes, source checksum, partitions, class counts, and expected predictions in private fixtures. Runtime measurements and model sizes also need builder validation.

**Dependency Chain**: Source validation precedes splitting; splitting precedes per-fold transformation/model preparation; model freezing precedes catalog generation; fold membership determines allowed inference artifacts; development scores determine selection; the selected full-development model determines holdout predictions. Private grading joins those predictions to held-back labels only after submission.

Reference metadata to preserve privately:
```json
{
  "dataset_shape_from_manifest": [569, 33],
  "predictor_count": 30,
  "target_name": "diagnosis",
  "target_classes": ["B", "M"],
  "positive_class": "M",
  "models_in_notebook": ["RandomForest", "GBM", "LightGBM", "XGBoost"],
  "notebook_split_seed": 314,
  "notebook_reduced_rf_reported_auc": 0.940,
  "notebook_xgboost_cv_auc_claim": ">0.99",
  "verified_expected_accuracy_range": null,
  "class_counts": null
}
```
Null fields are deliberately unverified; populate them from actual builder checks where applicable. The AUC figures are textual notebook claims, not independent references and not accuracy values. Do not require arbitrary accuracy gaps, nonzero fold-score variance, or exact feature-rank agreement.

## Instructions
Construct an offline research handoff with the original R Markdown reference, observed development rows, unlabeled holdout rows, frozen inference bundles, an honest model catalog, and public interface contracts. Do not include reference predictions or completed reports in visible inputs. The core work is discovering evaluation hazards, aligning records and model classes, executing genuine fold-specific inference, comparing transformations, and substantiating conclusions.

The catalog must identify candidate family, strategy, artifact path, class order, feature contract, fold validation IDs, training-ID digest, and full-development artifact. Validate provenance privately at build time. Models must expose inference with no fit step; preprocessing travels with each bundle. Make input validation behavior part of the public contract: accept reordered columns, ignore documented nonpredictor fields, preserve row order, and reject missing required predictors, duplicate IDs, malformed numeric values, or nonfinite required features with a nonzero status and useful error. Do not require general-purpose support for synthetic missingness absent from the source.

Public output contracts: `oof_predictions.csv` contains candidate_id, fold, id, p_malignant, predicted_label; `fold_metrics.csv` and `comparison.csv` contain denominators and named metrics; `selection.json` identifies the winner and rule; `feature_effects.csv` records feature, fold, repeat, seed, baseline_auc, permuted_auc, and delta; `holdout_predictions.csv` contains id, p_malignant, predicted_label; `audit.json`, `experiments.jsonl`, and `report.md` contain the data audit and supported interpretation. Define confusion matrix order as actual B/M rows and predicted B/M columns. Define precision as zero when no positives are predicted. Output probabilities with enough precision for 1e-8 metric checks.

Require permutation effects for the selected candidate over all 30 original features using five repeats per feature per fold and documented deterministic seeds. Permute one raw feature among that fold's validation rows before applying its frozen pipeline. Removed features may correctly have zero effect. Average across folds and repeats for ranking. This produces a bounded, auditable interpretation without assuming the source's feature ranking is ground truth.

## Source Context
Read `/home/exedev/.codex/worktrees/fc68/biotasks/downloads/notebook2task-pilot-20261006/seta-cytopathology/seed/analysis.Rmd`, with focused inspection of its input and feature sections. Used the kernel metadata and manifest supplied in the prompt; listed the staged dataset paths to establish the actual entry point `datasets/data/data.csv`. Did not execute the R Markdown, load the CSV for analysis, or fetch source URLs.

The notebook describes ten nucleus measurements summarized by mean, standard error, and worst value. It explores density, correlation, PCA, and t-SNE, then compares RF, GBM, LightGBM, XGBoost, a reduced-feature RF, and a weighted combination. It removes ID and the all-NA final column and uses a 70/30 split with seed 314. Numeric 0/1 diagnosis makes its RF a regression fit followed by rounding. Several reported ROC AUC calls use rounded predictions. The LightGBM prediction assignment is commented out, so its subsequent confusion matrix and AUC reuse the preceding GBM predictions. XGBoost's final fit uses `nRounds` rather than the selected CV iteration. These are concrete reasons to build an inference/evaluation audit instead of copying its conclusions.

The notebook highlights perimeter_worst, area_worst, concave points_worst, radius_worst, concavity_mean, concavity_worst, area_se, and concave points_mean as influential RF features. Treat this as qualitative source context. Its claim that GBM is best and its high XGBoost CV AUC do not establish held-out accuracy for all models, so the “all models achieve 99% accuracy” ditch condition is not demonstrated. Viability passes: small tabular observations, clear binary objective, multiple classical model families, and meaningful evaluation decisions. No raw image processing or neural networks are required.

## Environment Setup
Use `ubuntu:24.04` with Python 3.12, bash, tmux, and uv. Preinstall pinned NumPy, pandas, SciPy, scikit-learn, joblib, and pytest in a virtual environment. Use binary wheels; no R toolchain, GPU stack, external service, or systemd service is required. Target image approximately 500 MB and below 1 GB; measure it during the build. Copy only the designated visible data and trusted frozen artifacts. Keep builder scripts, full labeled source, private metrics, and grading fixtures out of the agent image. Set numerical-library thread counts to one. Build under five minutes and benchmark end-to-end evaluation within the resource limits before release.

## Reasoning Steps Required
Each step lists prerequisites and an observable postcondition.
1. Inspect handoff schemas and catalog (none); identify available data and inference interfaces.
2. Validate row identities and schema (1); produce structural audit counts.
3. Establish label semantics and class balance (2); record positive class and denominators.
4. Audit missingness and malformed fields (2); distinguish absent predictors from unused fields.
5. Analyze feature scales and extreme values (4); justify interpretation of unusual measurements.
6. Examine feature redundancy (5); quantify examples of correlated morphology measurements.
7. Inspect artifact preprocessing contracts (1, 6); explain differences between supplied strategies.
8. Verify development/holdout and fold memberships (2); establish disjoint exhaustive partitions.
9. Establish probability-column semantics (3, 7); map model outputs to malignant probability.
10. Implement reliable inference and input validation (8, 9); run valid and invalid sample inputs.
11. Generate fold-specific predictions for all candidates (10); create complete out-of-fold tables.
12. Recompute probability and threshold metrics (11); emit consistent fold metrics and confusion counts.
13. Compare processing strategies within families (12); quantify gains and losses.
14. Compare model families and variability (12, 13); document the limits of selection evidence.
15. Apply the public selection rule (14); produce a deterministic selection record.
16. Perform fold-specific feature perturbations (15); produce replayable importance measurements.
17. Interpret leading features and correlation caveats (6, 16); relate measurements to morphology without causal claims.
18. Generate selected-model holdout predictions (15); preserve identity and probability semantics.
19. Audit source evaluation claims (9, 12); document specific code-supported discrepancies.
20. Replay the CLI and reconcile all deliverables (18, 19); produce reproducible outputs and a supported final report.

## Testing
Use nine independent pytest tests with isolated temporary outputs or independently materialized fixtures. Tests exercise runtime behavior and do not inspect solution source text.

1. **Dataset audit correctness**: Compare nonempty audit results against builder-verified schema, development class counts, missing-value counts, duplicate count, and total rows. Check concrete reported redundancy examples numerically.
2. **Out-of-fold inference correctness**: Require exactly 455 rows per candidate, each ID once, correct persisted fold memberships, and finite probabilities in [0,1]. Independently invoke trusted matching fold artifacts and compare probabilities within 1e-8; this catches in-sample predictions and copied predictions.
3. **Metric correctness**: Recompute every fold's AUC from continuous probabilities and every discrete metric from threshold 0.5. Assert exact confusion counts and denominators, metric tolerance 1e-8, and the specified averaging convention.
4. **Comparison and selection**: Require four distinct catalog candidates, both families and both strategies. Recompute the mean-fold-AUC ordering and exact tie rule, and verify the selected identifier and reported comparisons. Do not demand that every pair of models disagree on every row.
5. **Holdout correctness and performance**: Require exactly the 114 persisted holdout IDs, once each, without development overlap. Compare predictions against independent selected-full-model inference, then join private labels and verify published AUC and malignant-recall thresholds.
6. **Permutation effects**: Require all features, five folds, and five repeats, including zero-effect removed features. Independently replay documented permutations with matching fold artifacts, compare deltas within 1e-8, and verify ranked summaries against computed effects.
7. **Input edge cases**: In fresh fixtures reorder rows and columns and change documented nonpredictor fields; verify identity-aligned predictions are invariant. Separately remove a required predictor, duplicate an ID, or insert invalid/nonfinite numeric data; require failure and a useful diagnostic without a successful predictions artifact.
8. **End-to-end reproducibility**: Invoke the public evaluator twice into fresh directories under single-thread limits. Compare predictions, selection, metrics, and permutation values; ignore timing and journal timestamps. Independently invoke `predict` on held-out feature subsets and confirm matching full-run outputs.
9. **Evidence integration**: Require nonempty journal entries for at least two measured comparisons, resolvable candidate/artifact references, and reported values matching computed tables. Check the structured source audit correctly identifies the rounded-score AUC and inactive LightGBM prediction behavior. Human review assesses explanatory quality; automated assertions check factual artifacts, not prose keywords or stylistic judgments.

## Difficulty
medium — 20 dependent reasoning steps, bounded inference, and multiple evaluation pitfalls; no training or infrastructure repair required from the solving agent.

## Core Skills Tested
- CSV schema and identity validation.
- Probability semantics and binary classification metrics.
- Correct use of frozen cross-validation artifacts and independent holdouts.
- Comparative reasoning about preprocessing and model families.
- Reproducible perturbation analysis with correlated biological measurements.
- Source-code auditing and evidence-backed terminal reporting.

## Key Technologies
Ubuntu 24.04, Python 3.12, bash, uv, tmux, pandas, NumPy, SciPy, scikit-learn frozen pipelines, joblib, pytest, CSV and JSON artifacts; R Markdown as reference text only.

## External Resources
None accessed. The design uses only staged source text and supplied metadata. Source URLs in the manifest and notebook are provenance, not runtime dependencies or independently verified evidence.
