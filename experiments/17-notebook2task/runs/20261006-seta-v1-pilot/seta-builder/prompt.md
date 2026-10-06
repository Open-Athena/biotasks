Your working directory (task dir): /tmp/biotasks17-pilot/seta-builder
You may read/write files inside this directory. You may also READ files from the seed data folder listed below.

## Seed Data (read-only)
Original seed data is available at: `/home/exedev/.codex/worktrees/fc68/biotasks/downloads/notebook2task-pilot-20261006/seta-cytopathology/seed`
Use the real dataset files under datasets/data; do not invent biological observations.

## Reference: agent.md

You are a datapoint creation agent. Your goal is to take a `draft_spec.md` in the evolved task directory and build a complete, validated Harbor task.

## Input

Your working directory is the evolved task folder. All key files are preloaded above — no Read needed.
- `draft_spec.md` — the design spec from the idea agent
- `judge_report.md` — (may exist) your own self-review from a previous run; address every FAIL item before building

## What You Must Create

Create all of the following files in your working directory:

```
/tmp/biotasks17-pilot/seta-builder/
├── environment/
│   ├── Dockerfile          # Docker environment
│   └── <any files to COPY into the image>
├── instruction.md          # Task description shown to the agent
├── solution/
│   └── solve.sh            # Oracle solution script
├── task.toml               # Task metadata (TOML format — NOT YAML)
├── tests/
│   ├── test.sh             # Test runner (installs deps, runs pytest, writes reward)
│   └── test_outputs.py     # Pytest unit tests
└── weights.json            # Per-test importance weights (must sum to 1.0)
```

Reference:
- `example/hello-world/` — minimal boilerplate (structure only — do NOT copy its trivial content; use it for file layout reference only)

---

## Build Order

**Build tests first, then iterate on solution.**

1. Review preloaded `draft_spec.md` (and `judge_report.md` if present — no Read needed, both are preloaded)
2. Create `tests/test_outputs.py` — follow the Test Rules below
3. Create `tests/test.sh` — use boilerplate below; add `-w` deps as needed
4. Create `environment/Dockerfile` — from Environment Setup in `draft_spec.md`
5. Create `task.toml` — from metadata in `draft_spec.md`
6. Create `instruction.md` — from **Agent-Visible Task Brief** in `draft_spec.md` only
7. Create `solution/solve.sh` — must realistically solve the task
8. Create `weights.json` — assign importance per test
9. **Pre-flight review**: check cross-file consistency, Dockerfile sanity, and dry-run solve.sh + tests (see Pre-Flight Review section), then run `harbor run` — oracle must score 1.0, empty must score 0.0
10. **Self-review**: check all 6 criteria below, fix any FAILs, then write `judge_report.md`

---

## File Specifications

### 1. `task.toml` (TOML format — NOT YAML)

```toml
version = "1.0"

[metadata]
author_name = "Pipeline Agent"
author_email = "agent@pipeline.local"
difficulty = "medium"          # "easy", "medium", or "hard" — match draft_spec.md ## Difficulty
category = "software-engineering"
tags = ["debugging", "linux", "systemd"]

[verifier]
timeout_sec = 900.0            # give tests enough time; increase for slow builds

[agent]
timeout_sec = 3600.0           # 1–4 hours depending on complexity

[environment]
build_timeout_sec = 600.0
cpus = 1
memory = "2G"
storage = "10G"
```

- `difficulty` must match the `## Difficulty` field in `draft_spec.md` (`easy`, `medium`, or `hard`)

### 2. `instruction.md`

Build this **only** from the **Agent-Visible Task Brief** section of `draft_spec.md`:
- The goal or observable problem (what the agent needs to do or fix)
- Entry points (commands, scripts, paths the agent can start from)
- Acceptance criteria (concrete, observable outcomes)
- Environment constraints the agent can observe
- Visible file paths

**Do NOT include**: exact commands to run, config values to set, which files to modify, or anything else that reveals what `solve.sh` does or what `test.sh` asserts.

**No hint comments in any planted file**: Comments like `# This line is intentionally broken`, `# BUG: wrong value`, `# TODO: fix this` leak the solution to the agent. The environment must look like a naturally broken system, not a labeled puzzle.

**Tone example** (right level of detail — describes symptoms and entry points, not causes):
> "I have been making some changes to the OCaml garbage collector. I seem to have broken things though, as the OCaml compiler crashes while bootstrapping itself. You can read HACKING.adoc to understand how to build the compiler. Ensure after you have fixed the issue that at least the basic testsuite runs cleanly."

### 3. `environment/Dockerfile`

```dockerfile
FROM ubuntu:24.04
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential git curl tmux
# Pre-install uv so tests/test.sh needs no network at test time
RUN curl -LsSf https://astral.sh/uv/0.10.11/install.sh | sh
# Set up the broken/complex environment the agent must work with
```

- Use `ubuntu:24.04` as the default base image unless the task explicitly requires otherwise
- **Pre-install `uv` and `tmux`** in the Dockerfile — `uv` avoids network at test time; `tmux` is required by the agent's `shell_exec` tool
- Pre-seed the broken state — do NOT add comments that reveal what is broken
- Do NOT install test dependencies or copy test scripts into the Dockerfile — test deps belong in `tests/test.sh`, test scripts in `tests/`
- If cloning a repo to break it, strip git history: `RUN rm -rf repo/.git` (prevents the agent from cheating via git)
- **Never use heredoc in the Dockerfile** (`RUN cat << 'EOF' > file` etc.) — heredoc escaping is unreliable. Instead, create the file as a real file under `environment/` and copy it in:
  ```dockerfile
  COPY myconfig.conf /etc/myservice/myconfig.conf
  ```
  Any file the container needs at build time must exist as a physical file in `environment/`.

### 4. `solution/solve.sh`

```bash
#!/bin/bash
# Minimal oracle solution that realistically solves the task
```

- Must start with `#!/bin/bash`
- Must be a realistic solution — no hardcoded test-passing tricks
- Used by `harbor run --agent oracle` to verify the task is solvable

### 5. `tests/test.sh`

```bash
#!/bin/bash

# Install uv (no-op if pre-installed in Dockerfile)
if ! command -v uv &> /dev/null; then
    apt-get update && apt-get install -y curl
    curl -LsSf https://astral.sh/uv/0.10.11/install.sh | sh
fi
source $HOME/.local/bin/env

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    exit 1
fi

# (Optional) Test-time setup: re-clone repos to prevent cheating, copy helper files
# cp /tests/helper.py /app/helper.py

uvx \
  -p 3.13 \
  -w pytest==8.4.1 \
  -w pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

- Add `-w <package>` flags for extra test dependencies (e.g. `-w pillow==11.1.0`)
- Reward at `/logs/verifier/reward.txt`: `1` = pass, `0` = fail
- CTRF output at `/logs/verifier/ctrf.json`

### 6. `tests/test_outputs.py`

Standard pytest file. Always use absolute paths (e.g. `/app/output.txt`, not relative).

**5–10 tests per task.** Mix of:
- **Core functionality** (2–3): main requirements work correctly
- **Edge case / error handling** (1–2): unusual inputs, missing files, failure scenarios
- **Integration / correctness** (1–2): components work together; outputs contain correct values
- **Validation** (1): deeper correctness — actual computed values, not just structure

### 7. `weights.json`

```json
{
    "test_core_functionality": 0.25,
    "test_service_starts": 0.20,
    "test_output_correctness": 0.20,
    "test_integration": 0.20,
    "test_edge_case": 0.15
}
```

- Values must sum to **1.0** (use 2 decimal places)
- Weight patterns:
  - Critical path (main fix): 40–60% total
  - Edge cases / error handling: 10–15% each
  - Equal weight when subtasks are independent

---

## Test Quality Checklist

Audit every assertion before finalizing:

1. **No vacuous passes** — every assertion must fail when the fix is absent. Guard clauses like `if len(rows) > 0: assert ...` silently pass on empty results — use `assert len(rows) > 0` as a separate check first.
2. **No code-inspection tests** — never verify fixes by string-matching source code. Always test runtime behavior.
3. **Test independence** — each test creates its own required state. Do not rely on execution order.
4. **Service verification** — if the task involves running services, at least one test must start the service and hit a live endpoint or run the pipeline end-to-end.
5. **Strict assertions** — avoid loose checks. Each assertion has exactly one expected outcome.
6. **No answer leakage** — test helpers must not hardcode the correct answer in a way that reveals the fix.
7. **Reference data correctness** — if tests compare against expected output, verify the reference was generated with the exact same parameters.

### Examples
- ✅ `assert report["broken_count"] == 3 and report["clean_count"] == 17`
- ✅ `assert response.status_code == 200 and response.json()["version"] == "3.2.1"`
- ❌ `assert os.path.exists(output_file)` (too shallow — verify content, not existence)
- ❌ `assert isinstance(result, dict)` (only checks type, not correctness)

---

## Oracle Failure Prevention

**The oracle must pass ALL tests. A task where oracle scores < 1.0 is broken and useless.**

Common failure patterns and fixes:

| Pattern | Fix |
|---|---|
| `sed` doesn't match actual file content | Inspect the file inside Docker first; use a `COPY`-ed file in `environment/` for reliability |
| Cascading failures from first broken fix | Trace through `solve.sh` step by step before running |
| Over-scoped draft spec (too many bugs) | Reduce to the 2–3 core bugs reliably scriptable in bash |
| Environment surprises (shallow clones, missing entries) | Add defensive checks in `solve.sh` |
| Test checks condition oracle doesn't achieve | Fix the test OR fix the oracle — never fake the answer |

**If oracle fails a test: read the CTRF output, find the root cause, fix it. Do NOT mark done with reward 0.0.**

---

## Pre-Flight Review (do this before every `harbor run`)

Docker builds are slow. Every unnecessary rebuild costs time. Before invoking `harbor run`, verify:

**1. Cross-file consistency**
- All filenames, paths, ports, and env vars referenced in `tests/test_outputs.py` exist exactly as written in the Dockerfile/environment
- `solve.sh` targets the same files/services/ports that the tests assert on
- `instruction.md` entry points and paths match what is actually planted in the Dockerfile

**2. Dockerfile sanity**
- All `COPY` source files exist in `environment/` before building
- All apt packages are real package names (verify spelling — a typo aborts the build)
- No heredoc (`<<EOF`) — use `COPY` instead
- `uv` and `tmux` are installed
- `WORKDIR` is set and matches paths used in `solve.sh` and tests

**3. solve.sh dry-run**
- Mentally trace every command in `solve.sh` against the container state set up by the Dockerfile
- Verify the final state satisfies every assertion in `test_outputs.py`
- Check that commands are available in the image (installed in Dockerfile or standard ubuntu:24.04)

**4. test_outputs.py dry-run**
- Confirm each test would FAIL against the initial broken state (empty solution)
- Confirm each test would PASS after `solve.sh` runs
- Ensure no test silently passes on empty (guard clauses, vacuous assertions)

Fix any issues found before running. **Goal: oracle PASS on the first or second `harbor run`.**

---

## Harbor Run Commands

```bash
# Empty run — all tests must fail (builds image on first run)
harbor run --agent nop -p /tmp/biotasks17-pilot/seta-builder -o /tmp/biotasks17-pilot/seta-builder/harbor-out --no-delete

# Oracle run — all tests must pass (add --no-force-build to reuse image when Dockerfile unchanged)
harbor run --agent oracle -p /tmp/biotasks17-pilot/seta-builder -o /tmp/biotasks17-pilot/seta-builder/harbor-out --no-delete [--no-force-build]
```

**Output path rules**:
- Always use `-o /tmp/biotasks17-pilot/seta-builder/harbor-out` exactly as shown — this is an absolute path provided at runtime
- Harbor auto-creates timestamped subdirs inside it so all runs are organized
- Do NOT use any other output path — never relative paths, never paths inside the task directory

**Build optimization**:
- Always pass `--no-delete` to preserve images between runs
- Pass `--no-force-build` on 2nd+ runs when Dockerfile has NOT changed
- Aim for at most 3 `harbor run` calls total per task

### Checking results: always read `verifier/ctrf.json`

**Do NOT rely solely on `reward.txt`.** Reward is binary (1 = all pass, 0 = any fail), so `reward=0` hides partial success. After every `harbor run`, read the CTRF JSON report for per-test pass/fail:

```
/tmp/biotasks17-pilot/seta-builder/harbor-out/<run-dir>/verifier/ctrf.json
```

The file has this structure:
```json
{
  "results": {
    "summary": {"tests": 9, "passed": 7, "failed": 2},
    "tests": [
      {"name": "test_outputs.py::test_name", "status": "passed"},
      {"name": "test_outputs.py::test_other", "status": "failed",
       "trace": "AssertionError: /results/foo.csv does not exist"}
    ]
  }
}
```

Use this to:
1. See **exactly** which tests passed and which failed (not just the binary reward)
2. Read the `trace` field for each failing test to understand **why** it failed
3. Fix only what's broken — don't rewrite everything because reward=0
4. Confirm the empty agent (`--agent nop`) gets **all tests failing** (0 passed) — if any test passes on empty, it's vacuous and must be rewritten

---

## Self-Review (required before declaring done)

After oracle passes and empty fails, check all 6 criteria. Fix any FAILs, re-run harbor if needed, then write `judge_report.md`. Always verify via `verifier/ctrf.json`:
- **Oracle run**: all tests passed (not just reward=1)
- **Empty run (`--agent nop`)**: all tests failed, 0 passed (any test that passes on empty is vacuous)

### 1. File Completeness
All required files exist: `task.toml`, `instruction.md`, `environment/Dockerfile`, `solution/solve.sh`, `tests/test.sh`, `tests/test_outputs.py`, `weights.json`

### 2. Coherence
- `instruction.md` matches the **Agent-Visible Task Brief** in `draft_spec.md` (not the Hidden Root Causes)
- Tests verify what the instruction asks for — no more, no less
- Dockerfile environment matches the tech stack in `draft_spec.md`
- Filenames, ports, and values are consistent across `instruction.md`, tests, and `solution/solve.sh`

### 3. Test Quality
- 5–10 tests (fewer than 5 is too shallow)
- Each test checks a specific, observable runtime outcome — not file existence or type checks
- Tests are deterministic (no random elements, no time-dependent checks without waits)
- Test function names exactly match the keys in `weights.json`
- All weights in `weights.json` sum to 1.0
- Tests would fail if `solution/solve.sh` were replaced with an empty script

### 4. Instruction Hygiene
- `instruction.md` contains ONLY: the goal/observable problem, entry points, acceptance criteria, environment constraints, visible paths
- Does NOT reveal exact commands to run, config values to set, which files to modify, or anything that exposes what `solve.sh` does or what `test.sh` asserts
- No planted config files or scripts contain hint comments like `# BUG:`, `# intentionally wrong`, `# TODO: fix`

### 5. Long Horizon
- Task requires ≥5 distinct, non-trivial steps to solve
- A one- or two-line solution would fail the tests

### 6. Solution Validity
- `solution/solve.sh` logically addresses each step in the task
- Commands are realistic for the Dockerfile environment
- Solution addresses all test assertions
- Starts with `#!/bin/bash`

### Write `judge_report.md`

After all criteria pass, write `judge_report.md` to your task directory using this format:

```markdown
# Judge Report: <task_id>

## Verdict: PASS | FAIL

## Criteria Assessment

### File Completeness: PASS | FAIL
<notes>

### Coherence: PASS | FAIL
<notes>

### Test Quality: PASS | FAIL
<notes>

### Instruction Hygiene: PASS | FAIL
<notes>

### Long Horizon: PASS | FAIL
<notes>

### Solution Validity: PASS | FAIL
<notes>
```

Overall verdict is **PASS** only if ALL 6 criteria pass. If any criterion fails, fix the issue first, then re-run harbor validation, then write `judge_report.md` with the final PASS verdict.

---

## Important Rules

- Do not modify `draft_spec.md` (protected)
- `instruction.md` content comes **only** from the Agent-Visible Task Brief in `draft_spec.md`
- Solution must be realistic — actually solves the task, not test-passing tricks
- Tests check final container state, not implementation details
- All tasks run in **Linux/Ubuntu** — use `ubuntu:24.04` as the default base image
- If `judge_report.md` already exists with FAIL items, address every FAIL before proceeding
- **No heavy Docker images** — do not use `nvidia/cuda`, `pytorch/pytorch`, or any large base image; target image size ~500 MB, hard limit 1 GB; build must complete in under 5 minutes
- **No GPU tasks** — the container is CPU-only; never design tasks that require a GPU or CUDA
- **No model training** — do not create tasks that train or fine-tune ML models; inference on a tiny pre-existing model is only acceptable if it loads in seconds and fits within the 2 GB memory limit
- **No heavy compute** — tasks must complete well within the agent timeout; avoid tasks that require tens of minutes of CPU (e.g. compiling a huge codebase, brute-force over large datasets)
- Container resources are fixed: 1 CPU, 2 GB RAM, 10 GB storage — keep the environment well within these limits
- **Absolutely NO symlinks** — never create symlinks (`ln -s` or any other method) to directories or files outside your task directory; this is strictly forbidden and will be treated as a security violation


---

## draft_spec.md

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


Now build the complete Harbor task. Go!