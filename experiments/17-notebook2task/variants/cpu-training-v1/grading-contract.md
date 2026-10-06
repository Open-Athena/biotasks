# Reproducible CPU model-comparison recipe (explicit additional variant)

This is a recipe change, not an unchanged SETA baseline. Preserve the task's
real breast-cancer cytopathology data and source lineage. Resolve ambiguity in
favor of executable scientific evidence, within the following grading contract:

- Training small classical models is allowed. For this case define a reproducible
  comparison of logistic regression, random forest, and gradient boosting.
  Publish exact hyperparameters, preprocessing, label mapping, train/test split
  seed and fraction, fold assignment rule, library pins, metrics and output
  schemas in the agent-visible brief. Override SETA's instruction against
  exposing config values where those values define reproducibility. Do not
  reveal oracle code, numerical answers, or grader internals to the solver.
- Use the observed CSV unchanged as source. Clean spurious empty columns and
  exclude patient identifiers. Fit scaling separately within each training fold
  (Pipeline), never before splitting. Select the best model by mean training-fold
  ROC-AUC only, with a declared deterministic tie-break; test outcomes must not
  decide selection. No tuned holdout-performance cutoffs.
- Grade a reproducible comparison, not open-ended model optimization. Require
  per-model out-of-fold and held-out probabilities keyed by original row ID,
  folds, recomputed CV/test metrics, and a selected-model report. The verifier
  independently regenerates splits, fits the declared native algorithms from a
  trusted data copy, and compares output probabilities within justified numeric
  tolerances. It must never rely on solver-supplied ground truth, fold assignments,
  metrics, model names alone, or an optional training-ID file.
- Keep verifier data/reference computation under tests/, separate from the
  solver-visible environment; Dockerfile must not copy tests/ or solution/.
  Parent stages the observed CSV into environment/data/data.csv and a separate
  trusted verifier copy tests/data.csv before execution. Never embed fabricated
  sample data or the source notebook/solution in the solver image.
- Test exact row coverage, label mapping and split/fold membership; reject
  nonfinite/out-of-range probabilities and duplicate/missing IDs. Accept close
  floating differences (e.g. 1e-6 if measured), not broad performance thresholds.
  Do not force a top-feature overlap or nonzero CV variance. The reference
  comparison must be computed independently of the solver's implementation.
- Pin Python 3.12 and scientific packages: numpy==2.3.3, scipy==1.16.2,
  pandas==2.3.3, scikit-learn==1.7.2, pytest==8.4.2. Use one worker/thread,
  modest model sizes (e.g. <=100 trees), and measure runtime and peak memory.
- Artifacts must support parent validation of an honest native reference plus
  empty submission, perfect-label predictions, shuffled IDs, fabricated CV
  metrics and intentionally leaky preprocessing. Record component failures.
  An observed public dataset is not a private or novel evaluation distribution;
  don't claim hidden-label security or benchmark novelty.

This introduces a fixed analysis protocol and narrows the notebook adapter's
free-choice model-selection goal. Describe this loss of openness explicitly.
Task difficulty and scientific validity remain unestablished until execution.
