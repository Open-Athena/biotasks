# Notebook2task prompt experiment

Preparation for [issue #17](https://github.com/Open-Athena/biotasks/issues/17).
This branch contains an untested baseline prompt and experiment design. There
are no approved source assignments, worker runs, generated tasks, or acceptance
results yet. The batch runner is not implemented yet. At Gonzalo's request,
source selection now includes brainstorming from familiar repositories and
reusing issue #10 inspections, rather than waiting for manually supplied files.

Base main commit: `2a1950d239f1ada467c35393991dac87debe35f7`.
Permanent research branch: `codex/research/17-notebook2task`.
Never merge this branch wholesale.

- [Baseline prompt](../../src/biotasks/prompts/notebook2task.md)
- [Protocol and proposed budget](protocol.md)
- [Worker output contract](output-contract.md)
- [Source intake](sources.json)
- [Logbook](logbook.md)
- [Interactive notebook and task-idea explorer](explorer/index.html)
- [Editable shortlist with source evidence](explorer/catalog.json)

The existing CLI can read the candidate using `biotasks prompts show notebook2task`.
Reading the template does not render placeholders, launch jobs, or validate tasks.

## Required before the first batch

Select sources with Gonzalo from the shortlist or supplied files. Assign development
and reserved splits before conversion. Freeze source revisions and checksums;
record data access, terms, and evaluation-overlap evidence. Do not replace this
intake with ranked discoveries or known benchmark analyses. The shortlist is
purposive brainstorming and remains separate from the approved source manifest.

Select the worker backend, exact model/reasoning settings, permitted compute,
and enforceable spend limits. Confirm the proposed execution budget in the
protocol. Pin a task harness/specification and provision isolated workspaces.
Then implement and exercise the minimal batch runner against that backend,
including interruption, timeout, failed-job retention, and telemetry checks.
Checkpoint executable inputs before any scientific/model run.

Research publication, paid services, and concurrent worker launches have not
been performed. Shared-VM safety rules still apply; the issue's desired parallel
workflow does not by itself allocate remote resources or authorize local workers.

## Replay API option

[Replay API design notes](replay-api.md) describe the user-requested option for
serving verified recorded responses offline. These notes remain separate from the notebook shortlist: Atlas was removed
because the identified source was an API guide. Artifact-specific training-use
terms remain unresolved for any future Atlas work. This is not an implemented service.

[Validation records](validation/README.md) cover the prompt package and explorer.

[Open the published explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/365a27799a1dc936d9f3b2ccefd8e282d53227be/experiments/17-notebook2task/explorer/index.html).
The public controls and one full notebook embed were browser-verified; see the
validation records for exact scope. The source remains on the research branch.
