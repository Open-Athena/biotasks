# Working on BioTasks

Build an open pipeline for generating and independently validating computational
biology tasks. Read the README for implemented behavior and `docs/pipeline.md`
for the proposed scientific workflow. Planning text is not execution evidence.

## Research and promotion

- `main` holds the supported pipeline, packaged prompts, tests, and maintained
  documentation. Keep experiments and their raw evidence on research branches.
- Use one issue per research question. Keep its current conclusion and decisive
  links concise. Record dated observations, decisions, failed hypotheses, and
  next steps in a branch-local logbook under `experiments/<issue>-<topic>/`.
- Start research from a recorded `main` commit, using `codex/research/<issue>-<topic>`.
  Record exact source revisions, prompts, inputs, configuration, environment,
  commands, budgets, outcomes, and artifact locations. Link results with commit
  permalinks. Preserve original evidence and distinguish corrections from it.
- Never merge a research branch, including by squash. Extract a supported change
  into a fresh `codex/pipeline/<topic>` branch from current `main`. Validate the
  consolidated change, add meaningful regression coverage, and link the evidence
  in its PR. Retain research branches or preserve an archive tag before deletion.
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
- Pin Python in `.python-version`, direct and development dependencies in
  `pyproject.toml`, transitive dependencies in `uv.lock`, and uv through
  `tool.uv.required-version`. Use the same locked environment for hooks and CI.
  Upgrade deliberately and revalidate affected behavior.

## Checks

```bash
uv sync --locked --python "$(cat .python-version)"
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

## Scientific evidence

- Use observed biological data as the backbone; label adaptations and simulations.
  Preserve lineage, source terms, and benchmark exclusions from the migrated plan.
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
