# Research workflow

`main` contains the supported pipeline, prompts, and maintained documentation.
Research branches preserve the questions, experiments, and evidence that inform
changes to it. A completed experiment can support a change, rule one out, or
remain inconclusive.

## Start and record an experiment

1. Open an issue for one research question. Include the goal or hypothesis,
   baseline, comparison criteria, scope, and execution budget. Keep a short
   current summary and links to decisive evidence in the body.
2. Start `codex/research/<issue>-<topic>` from a recorded `main` commit. Candidate
   changes use the normal source and prompt paths. Add
   `experiments/<issue>-<topic>/` for the logbook, one-off scripts, and run records.
3. Checkpoint the executable inputs before a reproducible run. Record that
   revision, rendered prompts, input versions, model and settings, tools, budget,
   environment, commands, and outcomes. Record what is unavailable explicitly.
4. Commit small evidence files afterward and link full commit permalinks from the
   issue. Use versioned external storage for large data and traces, recording
   locations, checksums, and retention. A branch link is for navigation; a result
   claim should cite the snapshot that supports it.
5. Keep dated observations and decisions in `logbook.md`. Retain failed
   hypotheses, incomplete attempts, and infrastructure failures with their actual
   status. Preserve original evidence when recording corrections.

The issue summarizes the current conclusion. The logbook explains meaningful
decisions. Run artifacts preserve exact execution and measurements. Avoid copying
the same narrative into all three.

## Promote a supported change

Never merge a research branch, including by squash. Create a fresh
`codex/pipeline/<topic>` branch from current `main` and extract the smallest
reusable change. Consolidate it, update relevant documentation, and validate it
against current `main`. Add tests for consequential behavior and known
regressions; scientific changes also need the relevant executable comparisons.

Open a PR linking the research issue and exact evidence. State the resulting
behavior, validation, and material limits. Raw research stays on its branch.
When the experiment ends, close its issue with a conclusion regardless of whether
a change was promoted. Retain the branch, or preserve a published archive tag
before deleting it. Referenced external artifacts need durable retention too.

## Maintain the environment

Use the Python patch in `.python-version` and the uv version required by
`pyproject.toml`. Direct dependencies and development tools use exact versions;
`uv.lock` pins the resolved environment. Use `uv sync --locked` and
`uv run --locked` so metadata drift requires an intentional lockfile update.

Dependabot proposes monthly dependency and GitHub Actions updates. Grouped minor
and patch updates reduce development-tool churn; runtime and major changes stay
separate. Review and validate before merging. Changes that could affect scientific
outputs need relevant pipeline evidence. Python and uv upgrades are explicit
maintenance changes. Preserved research environments remain unchanged.

The workflow YAML configures checks; repository settings control required checks,
branch protection, and Dependabot alerts/security updates. Verify those settings
when publishing the baseline. Local check results do not establish that GitHub CI
or Dependabot has executed.
