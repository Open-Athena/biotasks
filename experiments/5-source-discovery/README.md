# Source-discovery research

[Research issue #5](https://github.com/Open-Athena/biotasks/issues/5) tracks this
continuing study. [Migration #2](https://github.com/Open-Athena/biotasks/issues/2)
tracks its handoff from Marin. The question is: **What useful coverage do
different discovery routes contribute, and which sources should we inspect next
for biological task generation?**

## Start here

- [Interactive explorer](runs/2026-09-30-top300/explorer.html): all 1,014 sources
  from the four top-300 lists, sortable ranks, source-type and primary-group
  distributions, overlap/correlation views and the separate adoption cohort.
  The **Primary-group tail** tab compares counts and shares at 100 / 200 / 300
  for each route and the merged union. Download and open the HTML, or use the
  commit-pinned HTMLPreview link in issue #5.
  [Depth analysis, methods and validation](runs/2026-09-30-top300/README.md).
- [Known-repository gap audit](runs/2026-09-30-discovery-gaps/README.md):
  a purposive 112-repository panel, separate from the controlled depth expansion.
- [Preserved study](baseline/index.md): the 95-source inventory, adoption
  comparison, four top-100 rankings, and expansion to top-200.
- [Logbook](logbook.md): decisions, observations, open questions, and run records.
- [Migration manifest](migration.json): source revisions, every changed source
  path, migrated paths and hashes, and recovered local scripts.
- [Migration validation](runs/2026-09-30-migration/README.md): reproduced results,
  resource records, historical-hash reconciliation, and cache retention limits.
- [Public cache archive](runs/2026-09-30-bucket-archive/README.md): manifest,
  artifact locations and anonymous download verification of all 950 retained files.
- `scripts/verify_baseline.py`: offline, read-only reproduction checks.
- `baseline/local-scripts/`: original local collection, plotting, and checking
  helpers recovered during migration. These retain historical absolute paths
  and some write to the Marin checkout or contact remote services. **Do not run
  them directly.** Adapt a copy for a scoped follow-up and record its inputs,
  environment, output directory, and changes.

The reports retain the original scientific claims, uncertainties, and dates.
Only three reports received navigation or reproduction-command path changes;
their original and migrated hashes are in the manifest. Data, figures, and the
two tracked analysis scripts are byte-identical to the source revision.
Historical provenance paths identify Marin files; resolve them through the
manifest rather than treating them as paths in this checkout.

The baseline is frozen after migration. New requests, plots, corrections, and
measurements belong in separate `runs/<date>-<question>/` directories. A new
interpretation does not replace the original observation. The original report
commands write result files; use the read-only verifier below or copy the data
into a new run directory before invoking those commands.

## Reproduce the saved analyses

Use the repository's pinned Python and locked environment as described in
[AGENTS.md](../../AGENTS.md). On the shared exe.dev VM, run from the repository root:

```bash
python3 experiments/5-source-discovery/scripts/run_bounded.py 150 \
  .venv/bin/uv run --locked python \
  experiments/5-source-discovery/scripts/verify_baseline.py
```

The estimate is 150 MiB: the study's tracked inputs total about 4.3 MB and the
original standard-library ranking checks reported less than 50 MiB RSS. The
guard takes the shared lock nonblockingly, checks load and memory, limits thread
counts and priority, monitors resource thresholds, and reports start/end time,
exit status, and peak RSS. Run only one analysis at a time. The verifier does
not fetch data, run candidate software, or call models.

It checks imported hashes and local links, regenerates both ranking summaries
and topic-frequency tables in memory, recomputes expansion results, and
independently checks adoption correlations, sensitivities, and topic summaries
from the saved inventory. Numeric comparison uses an explicit 1e-12 tolerance;
identities, counts, and memberships must match exactly.

The original adoption environment was Python 3.12.3, NumPy 2.3.5, and SciPy
1.17.0; ranking analysis used the Python 3.12.3 standard library. Figure
generation reported Matplotlib 3.10.8. Those environments are historical;
migration checks use BioTasks' Python 3.13.13 and its standard library. Figures
are preserved by hash, not claimed to have been regenerated. The historical
helpers are starting points for reconstructing plotting, not a locked plotting
environment.

## Continue the study

For a follow-up, record the question, baseline, comparison criteria, execution
budget, and whether it uses saved measurements or collects new ones. Checkpoint
the executable inputs before a run. Record exact source revisions, selected
inputs and hashes, configuration, commands, environment, outcomes, plots, and
limitations. Include model settings only if a separately scoped run uses a
model; unavailable historical settings remain unknown.

Related plots stay under issue #5. A materially different question, such as
whether rankings predict successful task authoring, gets its own linked issue.
Use the issue for the current conclusion and decisive commit permalinks; use
the logbook for decisions and artifacts for execution evidence.

Initial handoff scope is saved-input preservation and reproduction only, with
less than ten minutes of local computation targeted. Future analyses receive
their own recorded scope and budget when requested. Adoption and topic labels
do not establish executable task quality or source-data redistribution rights.

Keep this research on `codex/research/5-source-discovery`. It is never merged,
including by squash. Adopted improvements are extracted into focused PRs from
current `main` with their evidence and validation. No promotion is required for
research continuity.
