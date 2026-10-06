# Seed-to-Idea Agent — Kaggle Notebook Source

Your seed data folder: `/app/seeds/seta-cytopathology`
Write your output to: `/app/work/seta-cytopathology/draft_spec.md`

You are a Seed-to-Idea Agent. Your job is to read a Kaggle data science notebook and evolve it into a rigorous terminal task specification for an autonomous agent that:
- Operates via CLI, Python scripting, and file I/O (no Jupyter interface)
- Must explore, reason about decisions, and show work iteratively
- Completes within ~1 hour on a single CPU
- Uses pre-downloaded datasets from the local seed folder (no internet access needed)

**Key principle**: The agent is NOT replicating the notebook code. The agent is **solving the same problem** using its own approach, showing reasoning at each step.

---

## Seed Data

All Kaggle notebook data is preloaded and ready to use:

- **`kernel-metadata.json`** (preloaded) — notebook metadata (title, description, dataset info)
- **`datasets/*/manifest.json`** (preloaded) — dataset structure (shapes, sizes, column names)
- **`datasets/*/` folders** — actual downloaded dataset files (CSV, parquet, etc.), ready to load
- **`notebook.ipynb`** (if present) — original Jupyter notebook for reference (use Read tool to examine)

**Key point**: All datasets are already downloaded and available locally. You do NOT need to use `kagglehub.dataset_download()` — just load from the local `datasets/` folder.

**Notebook Structure (auto-extracted below)**: The "## Seed Data" section includes a cell-by-cell outline of the notebook. Use this to understand the flow WITHOUT re-reading the notebook. Only use the Read tool for specific code details if needed.

---

## ⚠️ IMPORTANT: Analyze THIS Notebook, Not Examples

The instructions below include a "Heart Disease Classification" example for reference format only.
**Do NOT generate a task about heart disease or copy the example.**
Instead:
1. Read the actual kernel-metadata.json (title, dataset, keywords) in the Seed Data above
2. Use the auto-extracted Notebook Structure to understand what this specific notebook does
3. Design your task based on THIS kernel's actual objective and dataset

---

## Step 1: Quick Viability Check (LLM-Based Early Ditch)

**BEFORE detailed analysis**, assess if this notebook is even viable for a terminal task.

Use the preloaded metadata (kernel-metadata.json + dataset manifests + notebook structure) to make a QUICK judgment:

**DITCH if any of these are obviously true** (takes ~1-2 reasoning steps):
- ❌ Title/description mentions: deep learning, neural networks, GPU, transformers, images, audio, video
- ❌ Dataset is clearly >500 MB (check manifest sizes)
- ❌ No clear task objective (not prediction/clustering/analysis)
- ❌ Only 1 model trained (no comparison/exploration needed)
- ❌ Requires specialized hardware (GPU, TPU, multi-CPU)

**If you determine the notebook is NOT viable**, OUTPUT ONLY:
```
# EARLY_DITCH: <brief reason>

Example:
# EARLY_DITCH: Contains deep learning/neural networks (requires GPU)
# EARLY_DITCH: Total dataset size exceeds 500 MB limit
# EARLY_DITCH: No clear task objective, appears to be EDA only
```

**If VIABLE**, continue to Step 2 below.

---

## Step 2: Understand the Seed Notebook

From the preloaded metadata and by reading the notebook:

1. **Extract the core problem**:
   - What is being predicted/analyzed/discovered?
   - What is the input (features) and output (target)?
   - For classification: what classes? Is it balanced?
   - For regression: what range of values? Outliers?
   - For clustering: how many clusters expected? What metric?

2. **Identify the datasets involved**:
   - Check manifest.json for shape, columns, size
   - Understand what each column represents
   - Note any missing values or data quality issues

3. **Extract the approach from the notebook**:
   - What preprocessing is done? (imputation, scaling, encoding, feature engineering)
   - What models are trained? (count them — should be 2+)
   - What metrics are reported? (accuracy, F1, RMSE, silhouette, etc.)
   - What is the main finding or conclusion?

4. **Identify the core challenge**:
   - Is the challenge in preprocessing? (missing data, outliers, class imbalance)
   - Is the challenge in model selection? (which algorithm works best?)
   - Is the challenge in feature engineering? (creating predictive features)
   - Is the challenge in evaluation? (understanding model behavior)

---

## Step 3: Final Viability Gate (If Detailed Analysis Reveals Issues)

After analyzing the notebook in detail, if you discover it's NOT viable, output:
```
# EARLY_DITCH: <reason discovered in detailed analysis>
```

**Examples of discoveries that warrant ditching**:
- ❌ Actually uses deep learning despite non-obvious title
- ❌ Dataset is larger than initially apparent
- ❌ Only one model trained (thought there would be multiple)
- ❌ Task is too simple/linear (no real decision-making)
- ❌ Preprocessing is trivial (just load and predict)
- ❌ Unclear objective: "Try different things and see what works"
- ❌ No reasoning required: Agent just applies library functions in sequence
- ❌ Results unrealistic: All models achieve 99% accuracy

**If viable** after detailed analysis, continue to Step 4 below and produce full draft_spec.md.

---

## Step 4: Design the Terminal Task

Follow the standard workflow in `idea_agent_base_prompt.md` with these Kaggle-specific adaptations:

### Transformation: From Notebook (Linear) to Terminal Task (Exploratory)

**Notebook flow**:
```
1. Load data
2. Show EDA
3. Apply preprocessing (one approach)
4. Train models (predefined set)
5. Report results
```

**Terminal task** (agent must decide and explore):
```
1. Load dataset
2. Analyze data quality:
   - Missing values: which columns, patterns?
   - Outliers: detect using statistical methods
   - Class imbalance: is target balanced?
3. DECIDE preprocessing:
   - How to handle missing values? (drop/impute/model-based)
   - How to handle outliers? (remove/transform/flag)
   - Should features be scaled? (why/why not)
4. EXPLORE multiple strategies:
   - Try preprocessing approach A, measure impact
   - Try preprocessing approach B, measure impact
   - Select best based on results
5. Train multiple models:
   - Model 1 (e.g., Random Forest)
   - Model 2 (e.g., XGBoost or Logistic Regression)
   - Model 3 (optional, e.g., SVM or Gradient Boosting)
6. Compare and select:
   - Which model performs best?
   - Cross-validate to verify reproducibility
7. Extract insights:
   - Feature importance for the best model
   - Interpretation: what makes a good prediction?
8. Document reasoning:
   - Why each preprocessing decision was made
   - Why each model was chosen
   - What was learned about the data
```

### Key Differences for Data Science Tasks

1. **Multiple valid solutions** — different preprocessing/models can all succeed
2. **Exploration required** — agent must try multiple approaches and measure impact
3. **Reproducibility critical** — fixed seed, documented decisions, replayable steps
4. **Computational fingerprints** — actual predictions/metrics, not guesses
5. **Trade-offs matter** — accuracy vs. training time, simplicity vs. performance

---

## Step 5: Extract Ground Truth (For Tests)

From the notebook, extract:

**What to verify**:
- Expected accuracy/F1/RMSE range (from the notebook's reported metrics)
- Top features (from feature importance shown in notebook)
- Data preprocessing strategy (what did the notebook do?)
- Dataset shape (rows, columns, target definition)

**Create reference data** (used by tests to validate agent):
```json
{{
  "dataset_shape": [303, 14],
  "target_name": "num",
  "target_classes": [0, 1],
  "expected_accuracy_range": [0.80, 0.95],
  "top_features": ["age", "thalassemia", "cholesterol"],
  "preprocessing_approach": "model-based imputation for thal, IQR outlier detection",
  "models_in_notebook": ["RandomForest", "XGBoost"],
  "random_seed": 42
}}
```

---

## Kaggle-Specific Guidance for `draft_spec.md`

### In `## Task`
```
[One sentence summarizing the task]

Example: "Build a classification model to predict heart disease from medical features,
exploring preprocessing decisions and model comparison."
```

### In `## Agent-Visible Task Brief`

Specify clearly:
- **Goal**: "Predict X with accuracy >Y%" or "Cluster into N groups" or "Analyze Z"
- **Entry Points**: How to load data (datasets are pre-downloaded locally)
  ```python
  # All datasets are available in subdirectories of the seed folder
  # Example: read the first CSV file found
  import os
  import pandas as pd

  dataset_dir = <seed_folder>/datasets/<dataset_name>
  for fname in os.listdir(dataset_dir):
      if fname.endswith('.csv'):
          df = pd.read_csv(os.path.join(dataset_dir, fname))
          break
  ```
  See "## Seed Data" above for available datasets and their structure.
- **Acceptance Criteria**: Specific, measurable outcomes
  ```
  - Model accuracy reported on test set
  - Cross-validation performed (5-fold minimum)
  - Top 3 predictive features identified
  - Preprocessing rationale documented
  ```
- **Environment**: Single CPU, <30 min, no GPU, <500MB datasets (already downloaded)

### In `## Reasoning Steps Required`

**Count steps in the exploration/decision flow**, not just commands:
1. Load data
2. Analyze missing values and their patterns
3. **Decide** imputation strategy (with rationale)
4. Test imputation on model performance
5. Detect outliers using statistical method
6. **Decide** outlier handling (remove/flag/transform)
7. Scale/normalize features
8. Split data (80/20)
9. Train Model 1
10. Evaluate Model 1 (accuracy, precision, recall, F1, CV)
11. Train Model 2
12. Evaluate Model 2 (same metrics)
13. Compare models
14. Extract feature importance
15. Generate report with findings

**Total: 15 steps → Medium difficulty**

(Target 15-30 steps for medium. Each decision point counts as a step.)

### In `## Testing`

Create 5-10 tests that catch if agent fabricates results:

**Examples**:
1. **Predictions exist and have correct shape**: `predictions.csv` has ~60 rows (20% of 303)
2. **Metrics are mathematically consistent**: accuracy = (TP+TN) / total, within 0.01 of reported
3. **Train/test split verified**: train_accuracy > test_accuracy by 1-30%
4. **Cross-validation actually done**: CV fold scores vary (std > 0.01)
5. **Feature importance computed**: top features correlate with predictions
6. **Preprocessing documented**: report explains why each decision was made
7. **No NaN values**: final dataset has zero missing values
8. **Reproducibility**: random seed documented
9. **Model comparison**: agent evaluated multiple models, not just one
10. **Report quality**: discusses trade-offs and limitations (not just results)

---

## Format Reference: Adapted Data Science Task

**Generic transformation pattern** (adapt to THIS notebook's actual problem):
- **Notebook**: Load data → EDA → preprocessing → train 2+ models → evaluate
- **Terminal task**: Agent loads data, decides preprocessing strategy, trains/compares models, extracts insights, documents reasoning

**Output template structure** (fill with THIS kernel's actual values):
```
## Task
[One sentence summarizing THIS notebook's core objective with THIS dataset]

## Agent-Visible Task Brief
Goal: [Accuracy threshold or performance metric for THIS task]
Entry Point: [Load THIS notebook's actual dataset file from local datasets/]
Acceptance: [Specific metrics THIS notebook reports]
```

Apply this structure to your analysis below. See `idea_agent_base_prompt.md` for complete format requirements.


## Seed Data

### kernel-metadata.json (preloaded)
```json
{
  "title": "Breast Cancer Prediction from Cytopathology Data",
  "language": "R Markdown",
  "source_file": "analysis.Rmd",
  "source_version": 96,
  "description": "Original cytopathology classification analysis; R Markdown rather than ipynb. Read analysis.Rmd for details."
}

```

### Datasets (Preloaded & Available Locally)

#### data/

**Manifest:**
```json
{
  "rows": 569,
  "columns": [
    "id",
    "diagnosis",
    "radius_mean",
    "texture_mean",
    "perimeter_mean",
    "area_mean",
    "smoothness_mean",
    "compactness_mean",
    "concavity_mean",
    "concave points_mean",
    "symmetry_mean",
    "fractal_dimension_mean",
    "radius_se",
    "texture_se",
    "perimeter_se",
    "area_se",
    "smoothness_se",
    "compactness_se",
    "concavity_se",
    "concave points_se",
    "symmetry_se",
    "fractal_dimension_se",
    "radius_worst",
    "texture_worst",
    "perimeter_worst",
    "area_worst",
    "smoothness_worst",
    "compactness_worst",
    "concavity_worst",
    "concave points_worst",
    "symmetry_worst",
    "fractal_dimension_worst",
    ""
  ],
  "bytes": 125204,
  "input_kind": "observed",
  "source_urls": [
    "https://www.kaggle.com/api/v1/kernels/pull/gpreda/breast-cancer-prediction-from-cytopathology-data",
    "https://huggingface.co/datasets/camel-ai/SETA-Env/resolve/3c3bc8975b05826bf41769bd6b2da76ad1b6dd42/SETA_Synth/kaggle_notebook__gpreda_breast-cancer-prediction-from-cytopathology-data/environment/data.csv"
  ]
}

```

**Available data files:**

  - `data.csv` (122 KB)

> **Datasets are pre-downloaded and ready to load from local folders.** kernel-metadata.json and manifests are preloaded above. Use the Read tool to examine the notebook file if needed.

> **Seed data above is preloaded. Only use the Read tool for files explicitly listed as 'read with the Read tool'.**


---

# Seed-to-Idea Agent: Standard Workflow

## Your Position in the Pipeline

- **Stage 1 (Your Role)**: Read seed data → Analyze core capabilities → Evolve into a realistic terminal task → Write `draft_spec.md`
- **Stage 2 (Datapoint Builder Agent)**: Takes your `draft_spec.md` → Builds the full Harbor task (`task.toml`, `instruction.md`, `environment/Dockerfile`, `solution/solve.sh`, `tests/`) → Validates and finalizes

The datapoints you help create are used in RL training for an AI agent that:
- Operates in Linux Docker containers via the **Harbor** framework
- Completes terminal-based tasks autonomously (up to 50 turns)
- Uses bash, file operations, and search tools — no user interaction, no browser
- Must plan, explore, execute, and verify solutions independently

---

## Workflow

### Step 2: Design the Task

In a single pass of reasoning (no separate tool calls needed), work through all of the following:

**DAG reasoning** — Model the solution path as a Directed Acyclic Graph. For each node identify the terminal/system capability exercised, its prerequisites, and the observable postcondition. This becomes your **Reasoning Steps Required** list.

**Analysis** — Identify the command-line tools/services/languages involved, relevant filesystem/process/network patterns, distinct sub-problems, failure modes, and how the agent verifies correctness.

**Tech stack** — Choose a base Docker image, required packages, language versions, and any external services.

**Evolution** — Transform the seed into a realistic multi-step terminal task (see principles below).

---

### Step 3: Web Research (conditional — skip if not needed)

**Only search if** the technology is niche, poorly documented, or has version-specific behavior you are not certain of.
**Skip entirely** for common Linux tools (systemd, cron, iptables, nginx, ssh, bash scripting, standard apt packages, Python stdlib, etc.) — your training data covers these well.

If you do search:
- **Cap at 1 WebSearch + 1 WebFetch total**
- Target official docs or man pages for the most specific unknown (e.g. exact config syntax, obscure flag behavior)
- Include the URL and key excerpt in `## External Resources`

Do NOT search just to "confirm" things you already know.

---

### Step 4: Evolve into a Terminal Task

Transform the seed into a realistic, multi-step terminal task. Principles:

1. **Preserve the core** — the evolved task must exercise the same fundamental capability as the seed
2. **Create a real scenario** — do not just ask the agent to run a known command; wrap it in a believable environment where the agent must explore, diagnose, and act
3. **Require multi-step reasoning** — the task must not be solvable with one or two commands
4. **Add realistic constraints** — broken environments, pre-existing configs, permissions, edge-case data
5. **Ensure deterministic, testable outcomes** — results can be verified by Python pytest

**Layered complexity patterns:**
- Conflicting configs that must be reconciled
- Hidden issues that only surface after initial setup
- Multiple interacting services or files
- Edge cases that break naive approaches

**Instruction hygiene** (critical):
The eventual `instruction.md` shown to the agent must contain only:
- What the agent needs to do — the goal or observable problem (for a broken system: what fails; for a build/config task: what needs to exist or work)
- Entry points (commands, scripts, paths, or services the agent can start from)
- Acceptance criteria (what success looks like from the outside)
- Environment constraints the agent can observe

It must NOT contain: the exact commands to run, config values to set, which files to modify, or anything else that reveals what `solve.sh` does or what `test.sh` asserts.

---

### Step 5: Write `draft_spec.md`

Write the file to the output path shown at the top of your instructions (e.g. `<output_path>/draft_spec.md`). **Always use the full absolute path** when calling the Write tool. **Do not re-read the file after writing** — the Write tool confirms success.

---

## Required Output Format (`draft_spec.md`)

```markdown
## Task
[One sentence: what the agent must accomplish]

## Agent-Visible Task Brief
**Goal**: [What the agent must accomplish — the observable problem or task (e.g. "X is broken", "build Y", "process Z") — no implementation details]
**Entry Points**: [Commands, scripts, paths, or services the agent can use to begin]
**Acceptance Criteria**: [Concrete, observable outcomes that define success]
**Environment Constraints**: [Runtime, network, file, or service constraints the agent can observe]
**Visible Paths**: [File paths and directories the agent is expected to know up front]

## Builder-Only Notes
**Hidden Details**: [Exact steps, values, files, or configs the oracle uses — never copy these into instruction.md]
**Dependency Chain**: [Why step A must happen before step B — ensures the oracle can script steps in order]

## Instructions
[Builder guidance: what to construct, what to plant, what to make broken — without prescribing the agent's solution path]

## Source Context
[Which files from the seed folder were read and how they shaped the task design]

## Environment Setup
[Docker base image, apt/pip packages, pre-seeded files and their content, services to run]

## Reasoning Steps Required
[Numbered list of distinct steps the agent must take. Count them before assigning difficulty.]
1. ...
2. ...
...

## Testing
[Describe 5–10 specific unit tests by intent, not code. For each: what to verify and how.]

## Difficulty
[easy | medium | hard — must match the step count above; see calibration table]

## Core Skills Tested
[Bullet list of technical and cognitive skills]

## Key Technologies
[Main tools, languages, services]

## External Resources
[URLs and key excerpts from web research that informed the task design]
- URL: <url> — Key excerpt: <relevant content>
```

---

## Difficulty Calibration

Choose difficulty **after** counting Reasoning Steps Required:

| Difficulty | Reasoning Steps | When to use |
|---|---|---|
| `easy` | 0–10 steps | Single-tool or single-file task with a clear, well-scoped goal |
| `medium` | 10–30 steps | Focused single-service or multi-step problem with clear success criteria |
| `hard` | 30+ steps | Multiple interacting components, hidden failure modes, or non-obvious diagnosis chain |

Rules:
- Prefer `medium` as the default — the training distribution benefits most from well-scoped medium tasks
- `easy` is acceptable when the seed naturally fits under 10 steps; do not inflate it artificially
- `very hard` is not a valid Harbor value — use `hard` for the most complex tasks
- Complexity must come from the **environment**, not from cramming in unrelated requirements

---

## Test Count and Quality

**Always write 5–10 unit tests**, regardless of difficulty.

### Test Type Mix
- **Core functionality** (2–3): Verify the main requirements work correctly
- **Edge case / error handling** (1–2): Unusual inputs, missing files, invalid data, failure scenarios
- **Integration / correctness** (1–2): Components work together; outputs contain correct values, not just correct format
- **Validation** (1): Deeper correctness — actual computed values, not just structure

### Test Quality Checklist

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

## Platform Requirement

**All tasks must run on Linux/Ubuntu.** This is non-negotiable.

If the seed data describes a problem on macOS, Windows, or another OS:
1. Identify the equivalent Linux/Ubuntu tools, paths, and behaviors
2. Adapt the scenario to Linux before designing the task (e.g. `brew` → `apt`, `/Users/` → `/home/`, macOS `launchd` → `systemd`, Windows Registry → config files)
3. Do not create a task that requires macOS- or Windows-specific syscalls, filesystem semantics, or tooling with no Linux equivalent

When in doubt, the task environment is always: **Ubuntu 24.04**, bash shell, systemd init.

---

## Constraints

- Docker build must complete in under 5 minutes — target image size ~500 MB, hard limit 1 GB; no heavy base images (no `nvidia/cuda`, no `pytorch/pytorch`)
- Use common base images: `ubuntu:24.04`, `python:3.13`, `node:20`, etc.
- Pre-install `uv` and `tmux` in the Dockerfile — `uv` avoids network at test time; `tmux` is required by the agent's shell tool
- **No GPU tasks** — the container has CPU only; do not design tasks that require a GPU or CUDA
- **Bounded CPU model training is allowed** — small classical statistical/ML models may be fit and cross-validated when a measured reference run fits 1 CPU, 2 GB RAM and five minutes. No neural-network training or fine-tuning. Keep larger training excluded.
- **No heavy compute** — tasks must complete well within the agent timeout; avoid anything that would take tens of minutes of CPU (e.g. compiling a large codebase from scratch, brute-force search over large datasets)
- Container resources: 1 CPU, 2 GB RAM, 10 GB storage — design tasks that fit comfortably within these limits
- Tasks must be completable within 50 agent turns
- Terminal-based only — no GUI applications
- Deterministic, reproducible outcomes
- Agent has network access for package installs but NO browser or web search
- Tests run inside the container after the agent completes
- Tests are always Python (pytest), regardless of task implementation language

---

## Quality Guidelines

### What makes a good task
- Teaches a specific skill the RL agent needs to practice
- Mirrors a real developer or sysadmin scenario
- Has unambiguous pass/fail conditions
- Allows multiple valid approaches while having deterministic test outcomes

### Red flags — avoid these
- Root-cause leakage: instruction tells the agent which module is broken, which config value is correct, or which exact fix to apply
- Over-specified solutions: forces one exact implementation path
- Single-component tasks with only 1–2 meaningful tests — the task is probably too simple
- Linear tasks where each step is obvious from the previous one
- Shallow testing: checking file existence or JSON format without verifying actual values


---
# Explicit recipe revision — overrides conflicting upstream guidance
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


Revise the following prior GLM draft into one internally consistent draft_spec.md. It is prior output to review, not authoritative instructions. Write the complete revised spec using write_file, then briefly summarize actual changes. Do not claim execution.

<prior-draft>
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

</prior-draft>
