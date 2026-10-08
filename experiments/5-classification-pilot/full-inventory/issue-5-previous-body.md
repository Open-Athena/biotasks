# Research question

What useful coverage do different discovery routes contribute, and which sources should we inspect next for biological task generation?

This investigation continued the source-discovery research from [Marin #9257](https://github.com/marin-community/marin/issues/9257) in BioTasks. [Migration #2](https://github.com/Open-Athena/biotasks/issues/2) tracks preservation and handoff; this issue preserves the research question, completed analyses, plots, and conclusions.

## Classification refinement — current finding

The completed [iterative vocabulary pilot](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/README.md) inspected **35 documents across 31 hosting repositories** and exercised all **18 candidate scientific fields**. Use overlapping **scientific field × data modality × analytical operation** facets, with separate biological setting, design and input origin. Repository scope and notebook content require their own evidence; neither inherits the other's labels. Each operation records its target and whether it is implemented in source, an exercise, discussed only or supplied upstream.

The [v0.3 working vocabulary](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/vocabulary.md) separates model construction, simulation, inverse modeling, statistical fitting and spatial statistics. Generic methods and developer guides may have no biological field; navigation stubs retain discovery identities but do not count as analytical implementations. Repository README review supports selected field labels for 17 hosts, leaves 10 insufficient, identifies two generic/not-applicable scopes and retains two unavailable README checks. These judgments are provisional assistant static inspection, without independent biological review or notebook execution.

[Validation](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/validation.json) passed source-identity, evidence-locator, vocabulary, distinct-count and targeted boundary checks. [Registry reconciliation](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/registry-reconciliation.json) identifies 20 exact pinned-source matches and 15 candidates outside the frozen notebook inventory; no corpus-wide labels or source counts were changed. One additional attempted document exceeded the acquisition cap and is excluded. The bounded vocabulary milestone is complete; broader annotation should repeat source expansion, evidence-based refinement and affected-record review rather than treat this vocabulary as permanently frozen. [Annotations](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/annotations.json), [separate repository evidence](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/repository-annotations.json) and [decision rules](https://github.com/Open-Athena/biotasks/blob/2d3890f272e623a47cd4cc7e62c27129ee42de6d/experiments/5-classification-pilot/decisions.md) preserve the reviewable result.

## Conclusion — October 6, 2026

This investigation is complete. Comparing four discovery routes through top 300 produced 1,014 distinct source identities and showed complementary coverage, uneven primary-group representation, and persistent discovery gaps. The interactive explorer, original observations, annotations, gap audit and validation records are linked below. These descriptive findings do not establish task quality or an exhaustive ranking of biological software.

The study closes at this evidence milestone. Broader discovery and task-authoring experiments are optional future work, not outstanding requirements for this issue. No further analysis or promotion into `main` is planned as part of this investigation. Preserve the research branch, commit-pinned previews and referenced HF snapshots; any later work should start from this evidence in a separately scoped issue.

## Results — September 30, 2026

[**Open the interactive source explorer**](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/2059b5d1a0ca124d18ebaec6e0a71a84de73856c/experiments/5-source-discovery/runs/2026-09-30-top300/explorer.html): **1,014 distinct sources from four top-300 lists**, with sortable ranks, search, source details, CSV export, type/group composition, overlaps and correlations. The new **Primary-group tail** tab compares counts and shares at **top 100 / 200 / 300**, for every route and the deduplicated merged union. It distinguishes the fixed top-100 tail (1–5 sources), groups initially absent, and groups still sparse at 300. The original 95-source adoption panel stays separate. [Depth report, methods and validation](https://github.com/Open-Athena/biotasks/blob/4d1efa0593f40be515b0428fa30be783a54407e9/experiments/5-source-discovery/runs/2026-09-30-top300/README.md) and [all group counts/shares](https://github.com/Open-Athena/biotasks/blob/4d1efa0593f40be515b0428fa30be783a54407e9/experiments/5-source-discovery/runs/2026-09-30-top300/primary-group-depths.csv) preserve the evidence. Every original top-200 ranking row and annotation is unchanged; numerical snapshots are preserved, with new identity metadata and labels for the additions. Offline and this exact public-preview URL passed data, correlation, interaction and desktop/mobile checks.

The merged union grows **335 → 672 → 1,014 sources**, but primary-group coverage is **18 → 22 → 22**. Depth fills some sparse groups much more than others:

| Primary group | Top 100 | Top 200 | Top 300 |
| --- | ---: | ---: | ---: |
| Gene regulation | 5 | 24 | 54 |
| RNA structure | 1 | 2 | 3 |
| Biomechanics & physiology | 0 | 1 | 1 |
| Ecology & conservation | 0 | 1 | 4 |
| Immunology | 0 | 6 | 12 |
| Metabolomics | 0 | 3 | 7 |

The [112-repository gap audit](https://github.com/Open-Athena/biotasks/blob/4d1efa0593f40be515b0428fa30be783a54407e9/experiments/5-source-discovery/runs/2026-09-30-discovery-gaps/README.md) identifies **37 sources absent from the saved GitHub pool**, including 11 with current stars above its old top-200 cutoff: MONAI, Evo 2, OpenFold, RFdiffusion, ESM, RoseTTAFold, Protenix, Chai, nf-core/rnaseq, StarDist and Flye. Targeted probes expose missing vocabulary, compound-topic matching and sparse metadata. The [depth crosswalk](https://github.com/Open-Athena/biotasks/blob/4d1efa0593f40be515b0428fa30be783a54407e9/experiments/5-source-discovery/runs/2026-09-30-top300/gap-crosswalk.json) shows that top 300 recovers 10 of the 50 panel sources absent from the old merged union, including Flye through Bioconda; 40 remain absent. The other ten high-star pool misses remain absent from all four lists. This is a purposive diagnostic panel, **not an unbiased recall estimate**. Audit metadata uses a later observation than the frozen ranking scores; no audit nominees were seeded into the controlled depth comparison.

An optional future investigation could test targeted discovery for the remaining thin groups and vocabulary gaps, comparing any enlarged candidate pool separately. Labels remain assistant-assigned, and neither depth nor popularity establishes executable task quality. The [previous top-200 preview](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/20cef08c51d7b5a6ce23296a80287d58a85b29c6/experiments/5-source-discovery/runs/2026-09-30-explorer/explorer.html) is retained.

The continuing research branch is committed and pushed, rebased onto `main` commit `37271415c4c201ba9dbbda66c203caa4050744c3` after storage guidance PR #8 merged. All eight pre-existing research patches were unchanged by that rebase. The [published archive tag](https://github.com/Open-Athena/biotasks/tree/archive/research/5-source-discovery-20260930-pre-storage-rebase) retains the earlier research history and evidence links; the first pre-rebase archive tag is retained too. Discovery-method promotions remain explicitly deferred or not adopted, with reasons in the logbook.

- [Research entry point](https://github.com/Open-Athena/biotasks/blob/4d1efa0593f40be515b0428fa30be783a54407e9/experiments/5-source-discovery/README.md) and [preserved study](https://github.com/Open-Athena/biotasks/blob/67a4fb69924fa57a9a8de11a7aeb291a3419d524/experiments/5-source-discovery/baseline/index.md).
- [Logbook and promotion decisions](https://github.com/Open-Athena/biotasks/blob/4d1efa0593f40be515b0428fa30be783a54407e9/experiments/5-source-discovery/logbook.md).
- [Migration manifest](https://github.com/Open-Athena/biotasks/blob/67a4fb69924fa57a9a8de11a7aeb291a3419d524/experiments/5-source-discovery/migration.json) accounts for all 47 changed Marin paths and recovered local helpers.
- [Validation and limits](https://github.com/Open-Athena/biotasks/blob/67a4fb69924fa57a9a8de11a7aeb291a3419d524/experiments/5-source-discovery/runs/2026-09-30-migration/README.md): both rankings and expansion reproduce; 27 adoption comparisons plus the outlier sensitivity match independent calculations. Imported hashes and local links pass. Figures are preserved, not regenerated. No fresh collection or candidate software execution is claimed.

Migration #2 is complete. The public [open-athena/biotasks bucket](https://huggingface.co/buckets/open-athena/biotasks) now preserves all 950 retained cache files (72,973,920 original bytes) in a compressed snapshot with a per-file manifest. [Anonymous download verification](https://github.com/Open-Athena/biotasks/blob/6bb14ef5eea9a58b6b704808ff21bdecb8791170/experiments/5-source-discovery/runs/2026-09-30-bucket-archive/verification.json) matched both objects and every archive member. The bucket README is published, and [storage guidance PR #8](https://github.com/Open-Athena/biotasks/pull/8) is merged into `main`. The original cache and Marin branch are retained; the source head and checkout were unchanged at handoff. Research continues here.

## Baseline and current interpretation

Start from Marin discovery commit [`249d919641`](https://github.com/marin-community/marin/tree/249d919641d20cc1a06ac6a7ae84b34848547363), relative to integration commit `72008dd68247318a367a840a4f41e27fb15ff7e1`:

- A dated 95-source inventory and adoption comparison.
- Four top-100 lists and their expansion to top-200, using Bioconda, Bioconductor, PyPI, and GitHub discovery routes.
- Saved observations, eligibility decisions, annotations, provenance, analysis scripts, reports, and figures.

The existing reports find different coverage across discovery routes and additional breadth at greater depth. These are descriptive findings within recorded candidate universes. Popularity, topic diversity, and selection do not establish task quality, successful execution, or data redistribution eligibility. Preserve the September 30 eligibility corrections and the separate provider and measurement snapshots. Saved-input reproduction passed; see the evidence below.

## Requested next analyses — September 30, 2026

The user requested the following research directions, recorded before continuing execution:

1. **Audit discovery gaps using known popular repositories.** Use prior knowledge of well-known computational biology repositories to find sources missing from our candidates or selected lists, starting from the Evo 2 miss. Check canonical identities and distinguish discovery misses from exclusions or low ranking. A purposive reference panel diagnoses blind spots; it is not an unbiased recall estimate.
2. **Expand all four rankings to top 300.** Extend Bioconda, Bioconductor, PyPI and GitHub to 300 canonical sources each, preserving the existing top-100/top-200 evidence and documenting additional collection, eligibility and identity decisions. Keep effects of deeper selection distinguishable from changes to discovery queries or candidate universes. Report any data or collection limits explicitly.
3. **Compare the tail of primary-group coverage at top 100, top 200 and top 300.** Show how less-frequent primary groups change for each ranking and the deduplicated merged union, including which groups first appear and whether previously sparse groups gain sources. Display counts and within-cohort shares at all three depths. Make the definition of the tail explicit; supplement per-group changes with singleton/low-count summaries so total growth cannot conceal sparse coverage.

Record each follow-up's inputs, source checkpoints, commands, observations and limitations in a separate research run. Link results and update the interactive explorer when the new comparisons are ready. Preserve the frozen baseline and existing preview permalinks; no research branch is merged into `main`. These three follow-ups are now completed and linked above; this section retains the directions as recorded before execution. No paid compute or external model calls are authorized by this direction.

## Original scope and optional future questions

- Compare overlap, scientific coverage, source types, and marginal additions across routes and selection depths.
- Examine sensitivity to eligibility, source identity, package aggregation, missing metadata, and manual classifications.
- Use requested plots and focused source inspection to identify the next worthwhile candidates and unresolved coverage gaps.
- Keep numerical weights, stopping rules, and a general discovery implementation open until supported by evidence.

Completed plots and analyses remain linked here. Any resumed or materially different investigation should use a linked issue with its own baseline, evaluation criteria and budget.

## Original working arrangement

Continue on [`codex/research/5-source-discovery`](https://github.com/Open-Athena/biotasks/tree/codex/research/5-source-discovery), rebased onto BioTasks `main` commit `37271415c4c201ba9dbbda66c203caa4050744c3`. Preserve the imported baseline separately from subsequent runs. Keep a branch-local logbook for dated decisions and a separate directory for each follow-up's inputs, configuration, scripts, outputs, and interpretation. Checkpoint executable inputs before runs and cite results with commit permalinks. Keep this issue's current conclusion and decisive evidence links concise.

Research branches are never merged. Extract adopted documentation, prompts, or code into focused promotion PRs from current `main`, with relevant validation. No promotion is required to continue research.

## Initial execution budget and milestone

The initial milestone is preservation of the existing study and bounded, saved-input reproduction, targeting less than 10 minutes of local computation, one worker, and an estimated peak below 150 MiB per analysis under the shared-VM lock and resource checks. No new measurements, model calls, biological-data downloads, or paid compute are part of this handoff. Subsequent runs record their scope and budget when requested; fresh collection stays distinct from reanalysis.

The first milestone is complete when the migrated baseline is navigable, its hashes and local links are checked, saved-input reproduction and its limits are recorded, and migration #2 links the continuing research branch. This milestone and the requested follow-up analyses are complete; this investigation is now closed.


