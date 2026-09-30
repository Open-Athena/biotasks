# Working on BioTasks

Build an open pipeline for generating and independently validating computational
biology tasks. Read the [design documentation](docs/README.md) for the proposed
scientific workflow. There is no runnable generator yet; the implemented CLI
lists and reads packaged prompt templates. Planning text is not execution evidence.

## Setup and CLI

Use the Python patch in `.python-version` and the uv development dependency pinned
in `pyproject.toml`. Install that uv release using the
[uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/),
then run from the checkout:

```bash
uv python install
uv sync --locked --python "$(cat .python-version)"
uv run --locked pre-commit install
```

This installs the package in editable mode and the locked development tools,
including uv. CI selects uv from `uv.lock`.

```bash
uv run --locked biotasks prompts list
uv run --locked biotasks prompts show find-units
uv run --locked biotasks prompts show author-task > author-task.md
```

`show` writes the original template text, preserving placeholders such as
`{{REPO}}`. It does not render prompts or call a model. Templates ship with the
installed package and load independently of the working directory.
`python -m biotasks` exposes the same commands.

## Research and promotion

- `main` holds the supported pipeline, packaged prompts, tests, and maintained
  documentation. Keep experiments and their raw evidence on research branches.
- Use one issue per research question. Include the goal or hypothesis, baseline,
  comparison criteria, scope, and execution budget. Keep its current conclusion
  and decisive links concise.
- Start research from a recorded `main` commit, using `codex/research/<issue>-<topic>`.
  Candidate changes use the normal source and prompt paths. Keep a branch-local
  `experiments/<issue>-<topic>/logbook.md`, with one-off scripts and run records
  alongside it. Record dated observations, decisions, failed hypotheses, and
  next steps. The issue summarizes conclusions; the logbook explains decisions;
  artifacts preserve execution evidence. Avoid duplicating the narrative.
- Checkpoint executable inputs before a reproducible run. Record exact source
  revisions, rendered prompts, input versions, model settings, configuration,
  environment, commands, budgets, outcomes, and artifact locations. Explicitly
  record unavailable information. Commit small evidence files afterward and link
  results with commit permalinks; branch links are only for navigation. Preserve
  original evidence and distinguish corrections from it.
- Never merge a research branch, including by squash. Extract a supported change
  into a fresh `codex/pipeline/<topic>` branch from current `main`. Validate the
  consolidated change, update documentation, add meaningful regression coverage,
  and link the evidence in its PR. Scientific changes also need relevant
  executable comparisons. State the resulting behavior, validation, and limits.
- Close a completed experiment's issue with a conclusion even if no pipeline
  change is promoted. Retain research branches or preserve a published archive
  tag before deletion. Preserve referenced external artifacts too.
- Keep large inputs and traces in versioned external storage, with checksums and
  retention recorded. Do not commit credentials, environments, or downloaded data.
- Follow the user's publication instructions. Distinguish local, committed,
  pushed, PR-opened, and merged states. Use `gh` with `--body-file` for multiline
  issue and PR bodies, and verify the published text.

## Implementation

- Keep runtime code in `src/biotasks/` and runtime templates in
  `src/biotasks/prompts/`. Load templates with `importlib.resources`, independently
  of the current working directory. Keep a single canonical copy.
- Keep ordinary tests in `tests/`; introduce small fixtures when a test needs
  them. Experiment-only scripts and checks belong with their experiment.
- Keep reference-case descriptions in `docs/`. No skills directory or issue/PR
  templates are required. Add structure when there is content to justify it.
- Keep the root README focused on project purpose, current maturity, and design
  documentation. Keep setup, CLI, and research instructions here. Use issues for
  migration records, progress, and follow-up work.
- Pin Python in `.python-version`, direct and development dependencies in
  `pyproject.toml`, and transitive dependencies in `uv.lock`. Pin uv as a
  development dependency; CI reads its version from the lockfile. Avoid an exact
  `tool.uv.required-version` guard, which blocks Dependabot's own uv runtime.
  Use the same locked environment for hooks and CI. Upgrade deliberately and
  revalidate affected behavior.
- Dependabot proposes monthly dependency and GitHub Actions updates. Group minor
  and patch development-tool updates; review runtime and major updates separately.
  Validate before merging, with pipeline evidence for changes affecting scientific
  outputs. Upgrade Python explicitly. Preserve recorded research environments.
- Workflow YAML defines checks; repository settings control required checks,
  branch protection, and Dependabot alerts/security updates. Report local checks,
  GitHub CI, and actual Dependabot runs separately.

## Checks

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked ty check
uv run --locked pytest
uv run --locked pre-commit run --all-files
```

Run one test worker. The tests include building and installing the package into a
clean environment to exercise the real CLI outside the checkout. Keep default
checks free of model calls, biological data downloads, and paid compute. Run
focused checks during development; repeat broader checks when changes justify it.
Pre-commit fixes lint/formatting locally and checks types. CI runs two independent
jobs: Code quality checks Ruff lint/formatting and ty without modifying files;
Tests runs pytest, including the distribution checks. Run each check once in CI
and keep CI coverage aligned with the local hooks when changing them.

## Scientific evidence

- Use observed biological data as the backbone; label adaptations and simulations.
  Preserve lineage, source terms, and benchmark exclusions from the design docs.
- Grade artifacts deterministically. LLM review can guide development but cannot
  supply the reward. Keep oracle and grading assets outside solver-visible inputs.
- Distinguish discovery, implementation, native execution, independent validation,
  and release readiness. Record infrastructure failures and incomplete attempts
  separately from scientific outcomes. Never invent missing evidence.
- Keep scientific tolerances and the grading contract justified. Validate with
  native references, independent checks, and meaningful incorrect submissions.

## Shared exe.dev VM

On the shared VM, inspect one-minute load and `MemAvailable` before launching
process-heavy work. Do not launch it at load >= 1.5 or available memory < 2.5 GiB.
Acquire `/tmp/exe-codex-local-heavy.lock` with nonblocking `flock` for the command's
full lifetime; abort if held. Estimate peak working set and refuse local work over
500 MiB. Require >= 2 GiB projected headroom, or >= 4 GiB available when an estimate
is unavailable. Run only one substantial command at a time, with one worker,
`nice -n 10`, and `ionice -c 2 -n 7`.

Set `POLARS_MAX_THREADS`, `RAYON_NUM_THREADS`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` to 1. Monitor the first minute;
stop if available memory falls below 2 GiB or load exceeds 2.5. Record start/end,
exit status, and peak RSS. Avoid eager full-data sorting/grouping, detached work,
and per-minute polling loops. Stop only this task's subprocesses and verify none
remain. Ask before unplanned cloud spend. Do not spawn agents or start other
Codex tasks without explicit authorization for that concurrency.

Use documented exe.dev features only. For authenticated GitHub operations, run
normal `gh` commands with elevated sandbox permissions before diagnosing auth.
Never extract credentials from credential helpers or stores.
