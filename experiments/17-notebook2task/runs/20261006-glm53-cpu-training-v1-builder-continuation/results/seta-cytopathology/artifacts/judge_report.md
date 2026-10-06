# Judge Report: seta-cytopathology

## Verdict: PASS

Package built per the reviewed `draft_spec.md` and the explicit recipe contract
(fixed, reproducible CPU model-comparison protocol; reproducibility-defining
config published to the agent; verifier regenerates everything independently).

## Criteria Assessment

### File Completeness: PASS
All required files exist in the task directory:
`task.toml`, `instruction.md`, `environment/Dockerfile`,
`solution/solve.sh` (plus `solution/run_pipeline.py`, the pipeline it installs),
`tests/test.sh`, `tests/test_outputs.py`, `weights.json` (9 tests, weights sum
to exactly 1.00, keys match test function names exactly).

Data staging is deliberately deferred to the parent, per contract:
- `environment/data/data.csv` → copied by the Dockerfile as
  `COPY data/data.csv /app/data/data.csv` (relative to the environment build
  context; never reads `tests/` or `solution/`).
- `tests/data.csv` → trusted verifier copy, staged by the parent next to
  `test_outputs.py`; located at runtime relative to `__file__`, never from
  `/app/data/`.
No `data.csv` or fabricated sample data was authored by the builder; the
Dockerfile copies nothing from `tests/` or `solution/` into the solver image.

### Coherence: PASS
- `instruction.md` is the Agent-Visible Task Brief only (goal, published
  protocol, entry points, schemas, acceptance criteria, constraints, visible
  paths). Hidden reference values (expected AUC ranges, top-feature list, PCA
  value, notebook lineage) are not disclosed.
- `tests/test_outputs.py` verifies exactly what the brief demands: artifact
  schemas and row counts (1365/342), per-model id coverage and label integrity,
  split/fold membership against independent regeneration, probability match
  against independently refit declared algorithms at 1e-6 (rtol=0), metrics
  recomputed-consistent from the solver's own prediction files, selection by
  mean training-fold ROC-AUC with the LR→RF→GB tie-break, three genuinely
  distinct model families (compared by probability vectors, not names), EDA
  facts recomputed from trusted data, and report content requirements.
- Dockerfile matches the draft's environment: `python:3.12-slim`, pinned
  `numpy==2.3.3`, `scipy==1.16.2`, `pandas==2.3.3`, `scikit-learn==1.7.2`,
  `pytest==8.4.2`, `uv` + `tmux` pre-installed, single-thread env vars, data at
  `/app/data/data.csv`.
- Filenames, paths, model identifiers, seeds, and tolerances are consistent
  across `instruction.md`, `solution/`, and `tests/`.

### Test Quality: PASS
- 9 tests, each asserting specific observable outcomes with explicit counts
  (no vacuous passes; empty/missing artifacts fail via `pytest.fail` and hard
  assertions).
- No code-inspection grading: the only source-level check is that
  `/app/run_pipeline.py` exists, is non-empty, and `compile()`s (syntax only,
  never executed); all other tests inspect emitted artifacts.
- Tests are independent; shared read-only state is a module-scoped fixture
  regenerated from trusted data.
- The leaky-preprocessing discrimination check is embedded inside
  `test_probabilities_match_reference` (which inspects solver artifacts and
  fails on empty), not a standalone meta-test that could pass vacuously.
- Adversarial submissions are rejected by the graded assertions themselves:
  empty submission (missing artifacts), perfect-label predictions and shuffled
  ids (fail the 1e-6 reference match and/or y_true/y_pred/key-integrity
  checks), fabricated CV metrics (fail recomputed-consistency), leaky
  preprocessing (fails the honest-reference match, and the embedded guard
  asserts the tolerance actually discriminates honest vs leaky fits).
- Deterministic: fixed seeds, one worker/thread, no time or randomness in
  assertions.

### Instruction Hygiene: PASS
- `instruction.md` contains only the goal, published protocol (explicitly
  agent-visible per the recipe contract override), entry points, schemas,
  acceptance criteria, environment constraints, and visible paths.
- No oracle code, no numerical answers, no grader internals.
- No hint comments in planted files; the only planted file is the verbatim
  dataset staged by the parent (trailing-comma header and `id` column left
  intact as intentional wrinkles).

### Long Horizon: PASS
The task requires the full published chain: inspect the raw CSV schema, detect
and drop the spurious empty column, exclude `id`, encode the target, run
descriptive EDA, execute the stratified 80/20 split at 20250607, run 5-fold
StratifiedKFold with the exact fold-assignment rule, fit three declared model
families with fold-local scaling for the linear model, emit id-keyed OOF and
held-out probabilities, recompute metrics from the emitted files, apply the
selection rule with tie-break, and write conforming JSON/CSV artifacts plus a
substantial report, exposed as a re-runnable `/app/run_pipeline.py`. A one- or
two-line solution cannot satisfy the tests.

### Solution Validity: PASS
- `solution/solve.sh` starts with `#!/bin/bash`, locates its pipeline source,
  copies it to `/app/run_pipeline.py`, runs it with one worker, and sanity
  checks the seven artifacts.
- `solution/run_pipeline.py` implements the protocol exactly as published
  (same split call on row positions, same fold iteration order, same model
  constructors and hyperparameters, fold-local `StandardScaler` inside the
  logistic-regression `Pipeline`, full-precision CSV output via `%.17g`,
  metrics recomputed from the emitted prediction files, selection by mean
  training-fold ROC-AUC with the declared tie-break, report written beside the
  output directory). It is a realistic pipeline, not a test-passing trick.
- Commands are standard for the image (`python3`, `cp`, `mkdir`, `test`).

## Runtime / container checks: NOT RUN
This authoring stage cannot execute code, Docker, pytest, or Harbor. The
following remain NOT RUN and must be validated by the parent:
- Docker image build (Dockerfile COPY of the parent-staged
  `environment/data/data.csv`; pip install of the pinned wheels; uv install
  script).
- `harbor run --agent oracle` (expected: all 9 tests pass, reward 1).
- `harbor run --agent nop` (expected: all 9 tests fail, reward 0).
- Oracle runtime and peak memory measurement on 1 CPU / 2 GB (expected well
  under five minutes; ~18 small sklearn fits on 455×30 data plus one
  permutation-importance pass).
- Verifier reference runtime (module fixture: 18 fits + 1 leaky fit + EDA).
- Empirical confirmation that the 1e-6 (rtol=0) probability tolerance is both
  achievable by an honest reimplementation and discriminating against the
  leaky variant (the embedded guard asserts the leak gap exceeds 1e-6).
- Repeatability rerun of `/app/run_pipeline.py` for bit-reproducibility.

## Notes for parent validation
- Stage `environment/data/data.csv` and `tests/data.csv` as verbatim copies of
  the observed CSV with checksum verification; neither is authored here.
- `tests/test.sh` uses the preinstalled Python 3.12 and pytest only (no
  network), writes `1`/`0` to `/logs/verifier/reward.txt`, emits JUnit XML at
  `/logs/verifier/junit.xml`, and exits with pytest's status.
- `results/folds.csv` is treated as optional-but-validated, matching the
  published schema note; fold membership is graded from
  `oof_predictions.csv`.
- No claims of hidden-label security or benchmark novelty are made; the dataset
  is an observed public one, and difficulty/scientific validity are unestablished
  until execution.
