# BioTasks

BioTasks develops open tools for creating and validating computational biology
tasks. Inspired by [Marin](https://github.com/marin-community/marin), it combines
research through code, experiments and recorded results with focused, reusable
pipelines and helpers.

The project is in early development. Its CLI lists and reads bundled prompt
templates. Python helpers convert ordinary Python notebooks without execution,
inspect staged files and record GLM worker interactions. An end-to-end task
factory, remote provisioning and scientific validation still require an external
controller and separate execution evidence.

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
