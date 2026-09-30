# Integration migration

The initial baseline comes from Marin `codex/bio-tasks` at [`72008dd68247318a367a840a4f41e27fb15ff7e1`](https://github.com/marin-community/marin/tree/72008dd68247318a367a840a4f41e27fb15ff7e1), tracked in [BioTasks #1](https://github.com/Open-Athena/biotasks/issues/1).

The source contains planning docs and prompt templates, not a working end-to-end generator. The migration preserves that distinction.

## Source map

| Source at the pinned commit | Destination | Changes |
| --- | --- | --- |
| [index.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/index.md) | [docs/pipeline.md](pipeline.md) | Attribution, links, and repository context; reference cases extracted to [reference-cases.md](reference-cases.md) |
| [discovery.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/discovery.md) | [docs/discovery.md](discovery.md) | Attribution, links, and repository context |
| [requirements.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/requirements.md) | [docs/requirements.md](requirements.md) | Attribution, links, and repository context |
| [storage.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/storage.md) | [docs/storage.md](storage.md) | Attribution, links, and repository context |
| [task-authoring.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/task-authoring.md) | [docs/task-authoring.md](task-authoring.md) | Attribution, links, and repository context |
| [validation.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/validation.md) | [docs/validation.md](validation.md) | Attribution, links, and repository context |
| [examples/transcriptomics.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/examples/transcriptomics.md) | [docs/examples/transcriptomics.md](examples/transcriptomics.md) | Attribution, links, and repository context |
| [examples/star-deseq2.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/examples/star-deseq2.md) | [docs/examples/star-deseq2.md](examples/star-deseq2.md) | Attribution, links, and repository context |
| [prompts/author-task.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/prompts/author-task.md) | [src/biotasks/prompts/author-task.md](../src/biotasks/prompts/author-task.md) | Byte-for-byte copy |
| [prompts/find-units.md](https://github.com/marin-community/marin/blob/72008dd68247318a367a840a4f41e27fb15ff7e1/docs/experiments/bio-task-generation/prompts/find-units.md) | [src/biotasks/prompts/find-units.md](../src/biotasks/prompts/find-units.md) | Byte-for-byte copy |

## Prompt identity

These SHA256 values identify the original and copied prompt bytes. Scientific prompt content is unchanged.

- `author-task.md`: `a94cd4fa14e5dfaadd9b034fabfdd738639f0841710b56e88197e68ac36dd95a`
- `find-units.md`: `7ae464276280269e8ad9d2491412ce69cd9371f3775469fad011b38b8aefbbd0`

## Adaptations and history

- Documentation carries an adaptation notice. Relative links follow the new layout, the code repository points here, and research tracking points to BioTasks issues and the branch workflow.
- The former pipeline-development testbed section is now [reference cases](reference-cases.md), without adding a top-level data directory. Its scientific examples are unchanged.
- The source `docs/experiments/bio-tasks.md` was a redirect to the plan and historical material. Its role is covered by the README; an extra redirect page is unnecessary.
- Historical implementation and catalog links remain pinned to their original Marin revisions. No historical generator, task data, or experiment results were imported.
- The source root Apache-2.0 license matches this repository's `LICENSE`; its root contains no `NOTICE`. Attribution for imported material is recorded in this repository's `NOTICE`.

## Follow-up work

- [Discovery migration #2](https://github.com/Open-Athena/biotasks/issues/2) follows the live `codex/bio-tasks-discovery` branch.
- [Authoring migration #3](https://github.com/Open-Athena/biotasks/issues/3) follows the live `codex/bio-tasks-authoring` branch, including its newer prompt trials.
- Those issues select and record source commits when migration begins. Their changes and uncommitted research are not part of this baseline.
- The public task-release location and large-artifact storage remain undecided. No model calls, scientific runs, or dataset publication are needed to validate this migration.
