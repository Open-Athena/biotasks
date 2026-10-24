# BioTasks

BioTasks develops open tools for creating and validating computational biology
tasks. Inspired by [Marin](https://github.com/marin-community/marin), it combines
research through code, experiments and recorded results with focused, reusable
pipelines and helpers.

The project is in early development. The CLI inspects bundled prompt templates
and resumes native validation of existing Repo2RLEnv inline PR task exports on
reserved Iris CPUs. It preserves task files, records control outcomes, verifies
archives and cleans up owned resources. See [validation](docs/validation.md) for
supported inputs and limits. It does not generate tasks or call models.

`main` holds reasonably established tools, tests and the documentation needed to
use and maintain them. Experiments and their evidence live on permanent research
branches; useful results need not produce a change to `main`. Focused pipelines
can develop independently, with common helpers extracted when useful. Broader
research directions and literature synthesis belong in a separate, evolving
research document or knowledge base outside the repository.

Read the [documentation](docs/README.md) for existing functionality and storage
practices, and [AGENTS.md](AGENTS.md) for setup and contribution guidance.
See [issues](https://github.com/Open-Athena/biotasks/issues) for experiments and
results.
