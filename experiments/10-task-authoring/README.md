# Source inventories and task-authoring research

[Issue #10](https://github.com/Open-Athena/biotasks/issues/10) asks how repository
source inventories can preserve scientific meaning and support independently
validated computational biology tasks. Continue on
`codex/research/10-task-authoring`, based on BioTasks `main` commit
`37271415c4c201ba9dbbda66c203caa4050744c3` with the preserved migration commits.
This branch is never merged; adopted changes receive focused promotion PRs.

- [Preserved research](../3-authoring-migration/README.md): original templates,
  prompts, inputs, 37 run records, outputs and independent parent reviews.
- [Decisions and missing evidence](../3-authoring-migration/logbook.md#candidate-decisions).
- [Integrity and package checks](../3-authoring-migration/runs/2026-09-30-migration/README.md).
- [Complete public archive](../3-authoring-migration/runs/2026-09-30-ucsc-remaining/README.md):
  all 73 original cache files, with upstream notices, manifests, hashes and
  anonymous-download verification across three snapshots. No migrated cache
  file depends on a local worktree for retention.
- [Continuing logbook](logbook.md).
- Candidate [find-units](../../src/biotasks/prompts/find-units.md) and
  [author-task](../../src/biotasks/prompts/author-task.md) templates at the normal
  package paths. Main has not adopted these revisions.

The current discovery candidate still has source-fidelity and completion
failures. The task-authoring template has not been trialed. Structural checks,
unit counts and worker readiness claims do not establish scientific correctness
or a working task. The CLI matrix has three completed cells and one
service-blocked partial cell; do not combine it into a completed model ranking.
Independent solve/reflection orchestration and native task validation remain
future work.

Keep new records under `runs/<date>-<question>/` here. Before execution, record
the question, baseline, source/input versions, exact rendered prompt, withheld
review criteria, model/settings/tools, environment, commands and execution
budget, then checkpoint them. Preserve failures and original outputs; append
corrections and interpretations. Obtain the applicable authorization for model
calls, paid compute or concurrent agents. Opening this issue launches none.

Saved-input checks can use the migrated read-only verifier under the shared-node
guard described in the preservation entry point. Do not execute archived
preparation helpers or the historical CLI wrapper against preserved output
directories. Source ranking remains a separate study in
[issue #5](https://github.com/Open-Athena/biotasks/issues/5).
