# BioTasks

An open pipeline for generating and validating computational biology tasks.

The initial baseline packages two prompt templates and a CLI to inspect them.
The [pipeline plan](docs/pipeline.md) describes the proposed generation and
validation process; end-to-end generation, model execution, and task release are
not implemented yet. The prompts retain their provisional scientific status.

## Setup

Use Python **3.13.13** and uv **0.12.21**, pinned in `.python-version` and
`pyproject.toml`. Install the pinned uv release using the
[uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/),
then run from the checkout:

```bash
uv python install
uv sync --locked --python "$(cat .python-version)"
uv run --locked pre-commit install
```

This installs the package in editable mode and the locked development tools,
including uv. CI selects uv from `uv.lock`. Dependency upgrades require
intentional changes to the pins and lockfile.

## Inspect prompts

```bash
uv run --locked biotasks prompts list
uv run --locked biotasks prompts show find-units
uv run --locked biotasks prompts show author-task > author-task.md
```

`show` writes the original template text. Placeholders such as `{{REPO}}` are
preserved; these commands do not render prompts or call a model. The templates
live in `src/biotasks/prompts/` and ship with installed distributions, so the CLI
also works outside a checkout. `python -m biotasks` exposes the same commands.

## Development

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked ty check
uv run --locked pytest
uv run --locked pre-commit run --all-files
```

Tests cover prompt access, CLI errors, and installation from built distributions
outside the checkout. They run without model calls or biological data downloads.
CI runs the same checks with one test worker. Pre-commit fixes lint/formatting
locally and checks types; CI checks formatting before hooks can change files.
Dependabot proposes monthly updates. See [AGENTS.md](AGENTS.md) for repository
conventions and shared-VM resource requirements.

## Research and migration

Keep the supported pipeline on `main` and research on branches linked from issues.
Research branches contain logbooks and reproducible evidence and are never
merged. Promote consolidated, validated improvements through separate PRs from
current `main`. See the [research workflow](docs/research-workflow.md).

This baseline migrates the pinned Marin integration branch from
[Marin #9257](https://github.com/marin-community/marin/issues/9257).
The [migration record](docs/migration.md) maps every imported file to its source
and records prompt hashes and documentation adaptations.

- [Integration baseline #1](https://github.com/Open-Athena/biotasks/issues/1)
- [Discovery research #2](https://github.com/Open-Athena/biotasks/issues/2)
- [Authoring research #3](https://github.com/Open-Athena/biotasks/issues/3)

The follow-ups use their source branches' heads when migration begins. The
[reference cases](docs/reference-cases.md) describe scientific review examples;
they are not an automated evaluation suite.
