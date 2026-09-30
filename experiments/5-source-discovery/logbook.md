# Source-discovery logbook

## 2026-09-30 — Continue the Marin study in BioTasks

Decision: transfer the research direction and its evidence into one continuing
branch for [issue #5](https://github.com/Open-Athena/biotasks/issues/5). Follow-up
questions and plots can proceed here without adopting a ranking algorithm or
requiring a promotion into `main`.

### Source and destination

- Marin integration baseline: `72008dd68247318a367a840a4f41e27fb15ff7e1`.
- Marin discovery head at migration start: `249d919641d20cc1a06ac6a7ae84b34848547363`.
- Original discovery commits: `539198684e`, `96a144591c`, and `249d919641`.
- BioTasks `main` baseline: `c860147af3883e209d9724c7abf4f9c13f337eb9`.
- Destination branch: `codex/research/5-source-discovery`.
- Source checkout was clean at the start. Ignored Python bytecode is not research
  evidence. No authoring-branch material is included.

The full delta contains 47 paths. Forty-three report/data/figure files move to
`baseline/`; two analysis scripts move to `scripts/`. The two Marin navigation
changes remain at the pinned source revision and are replaced here by the
research README and issue links. The manifest accounts for all 47 paths.

An additional local cache contained 48 Python helpers. Forty-seven are preserved
byte-for-byte under `baseline/local-scripts/`, with null source revision and
content hashes. The downloaded PyPIStats implementation is retained at source
as an upstream reference rather than vendored. These helpers were not committed
in Marin and are not asserted to be the exact executed versions. They require
path and environment adaptation before future use.

Provider responses and other scratch evidence remain in
`/tmp/bio-discovery-20260929`. This is a local, non-durable location, not an
external archive. A separate inventory records retained files and hashes;
environments, generated documentation sites, and the unrelated integration
checkout are excluded. Do not delete the cache. Durable archival storage remains
an explicitly deferred handoff item; the migrated curated inputs support
saved-input reproduction without it.

### Promotion decisions

| Candidate | Decision | Missing evidence or next step |
| --- | --- | --- |
| Versioned archives alongside repositories | Defer documentation/prompt promotion | Establish the intended source-inspection contract with an archive example; the current prompt accepts a repository. |
| Separate package/source identity and dated provider observations | Defer reusable schema/code | The design already retains metric definitions and dates. Exercise a consumer and counterexamples before standardizing additional fields or identity rules. |
| Explicit candidate universe and eligibility for every comparison cohort | Retain as research practice; defer a maintained validator | Existing ranking checks cover this study. A second concrete use can establish the reusable interface and appropriate regression cases. |
| Ranking/expansion scripts as supported CLI commands | Defer | Fixed registries, cohort sizes, and manual label meanings are study-specific; no pipeline consumer is established. |
| Maximum package counter, numerical ranking weights, or top-200 as general defaults | Do not adopt from this study | Descriptive comparisons do not validate a universal aggregation rule, stopping rule, or task-selection policy. |
| Discovery prompt changes | None in the migrated delta | Future prompt improvements require a scoped comparison. |

### Initial validation plan

Checkpoint imported files and executable validation inputs before running.
Check all migrated hashes and local links, reproduce both ranking analyses and
the expansion from saved inputs, and recompute adoption correlations and topic
summaries independently using the standard library. Preserve historical
provenance hashes even if a later recorded source correction superseded them;
report any such differences separately.

Budget: one local worker; 150 MiB estimated analysis working set; less than ten
minutes of computation; shared lock, thread limits, low priority, and monitored
resource gates. No new provider collection, candidate package execution, model
calls, biological-data download, paid compute, or figure regeneration.

Publication plan: push the preservation and validation commits to this research
branch, link exact commits from issues #5 and #2, and record the remaining
external-cache archival limitation. No PR or merge is part of this handoff.

### Validation outcome

Executable inputs were checkpointed in `d0e52828229127776a1a5b94b669c711f39e0a5c`.
The [first verification](runs/2026-09-30-migration/verification-01.txt) passed:
92 migrated hashes, 400 top-100 positions, 800 top-200 positions, the expansion
comparison, 27 adoption comparisons, the outlier sensitivity, all 95 adoption
export rows, topic summaries, and 76 local links. This is saved-input
reproduction, not fresh collection or independent scientific eligibility review.
The analysis took 0.21 seconds and peaked at 33,620 KiB RSS; exit status was zero.

Three hashes in the original top-200 baseline provenance refer to the pre-review
versions of the top-100 GitHub candidate table, exclusions, and provenance.
Each matches Marin commit `96a144591cced7b577962e0041f0f8b49386a32d` exactly;
`249d919641` contains the documented eligibility correction. Original provenance
was preserved, and the migration manifest identifies the imported current
bytes. The [reconciliation](runs/2026-09-30-migration/historical-hash-check.json)
records both. No historical result was silently rewritten.

The [retained-cache inventory](runs/2026-09-30-migration/retained-cache.json)
accounts for 950 local files totaling 72,973,920 bytes after the stated exclusions.
It is a content inventory, not a copy or durable archive. Cache inventory peaked
at 30,764 KiB RSS and exited zero. Durable archival remains the outstanding item
in migration #2; research can continue from the migrated curated inputs.

At the final source check on September 30, the local and remote Marin discovery
heads still matched `249d919641d20cc1a06ac6a7ae84b34848547363`, and the working
checkout remained clean. No intervening committed or uncommitted delta was
observed. Future discovery work continues here; the Marin branch is retained.
Repository licenses match, and original script attribution is preserved.

## 2026-09-30 — Rebase after the GitHub guidance promotion

[PR #6](https://github.com/Open-Athena/biotasks/pull/6) merged as
`86f0b1c149788c1ae5e86a210c218df36665bd72`. The continuing research branch was
rebased onto that `main` revision without conflicts. Git range-diff showed both
research patches unchanged, and the research tree matched the pre-rebase tree
byte-for-byte before this log entry was added. No scientific analysis was rerun.

The published archive tag
[`archive/research/5-source-discovery-20260930-pre-rebase`](https://github.com/Open-Athena/biotasks/tree/archive/research/5-source-discovery-20260930-pre-rebase)
retains `67a4fb69924fa57a9a8de11a7aeb291a3419d524` and its ancestors so existing
evidence permalinks remain reachable. Recorded experiment baselines and
validation checkpoints still identify the original runs; this rebase does not
change those historical records.

## 2026-09-30 — Public HF bucket archival

The user selected the public `open-athena/biotasks` Hugging Face Storage Bucket
for early research artifacts, with HF dataset repositories reserved for eventual
task releases. The [archive run](runs/2026-09-30-bucket-archive/README.md) preserves
the exact 950-file migration allowlist (72,973,920 bytes) in a compressed bundle
with a per-file SHA-256 manifest. The prior inventory and frozen baseline remain
unchanged; no new scientific measurements or source collection were performed.

Preparation rechecked every source hash. Upload followed a committed object
plan, and anonymous download into a new directory verified both object hashes
and all archive members. The public archive is complete. No credential-pattern
matches were found; this limited scan is not a source-eligibility review. Raw
provider errors and partial responses remain part of the evidence, and original
third-party terms still apply. The local source cache was retained.

The manifest hash names the snapshot prefix. Bucket storage itself is mutable;
append-only snapshots and retention of cited evidence are operational project
conventions. A separate PR from current `main` documents these conventions and
the bucket's research role. This resolves the remaining archival item in
migration #2; continuing research remains tracked in #5.

The bucket root README is published and verified by anonymous readback and a
public page check. Its source and maintained storage guidance are proposed in
[PR #8](https://github.com/Open-Athena/biotasks/pull/8), open against `main`.
Research evidence is committed and pushed separately; no research branch is
being merged. The root README can evolve as a catalog without changing the
retained snapshot.

## 2026-09-30 — Rebase after storage guidance merged

[PR #8](https://github.com/Open-Athena/biotasks/pull/8) merged as
`37271415c4c201ba9dbbda66c203caa4050744c3`. The continuing research branch was
rebased onto that freshly fetched `origin/main` revision, which also includes
the agent-attribution guidance from PR #9. The rebase completed without
conflicts. Git range-diff matched all eight research patches exactly, and the
entire experiment tree was byte-identical to the previous tip before this
logbook entry. No scientific analysis or storage transfer was rerun.

The published archive tag
[`archive/research/5-source-discovery-20260930-pre-storage-rebase`](https://github.com/Open-Athena/biotasks/tree/archive/research/5-source-discovery-20260930-pre-storage-rebase)
preserves `6bb14ef5eea9a58b6b704808ff21bdecb8791170` and its ancestors. Existing
Git-pinned manifests, upload receipts, bucket README links and original run
checkpoints remain reachable and unchanged. The earlier pre-rebase archive tag
is retained too. The recorded historical statements that PR #8 was open describe
publication at that time; the storage guidance is now on `main`.

## 2026-09-30 — Interactive discovery explorer

The user requested a standalone HTML page, previewed through HTMLPreview and
linked from issue #5, to browse every source selected by any top-200 route and
compare ranks, source types, subdomains, overlap and correlation. The
[explorer run](runs/2026-09-30-explorer/README.md) uses only the preserved inputs;
no collection, annotation, model call or paid computation was performed.

All 672 canonical sources are included, including non-GitHub repositories and
archives. Absent ranks mean not selected. Linked table and comparison views
support exploring exact set membership, pairwise overlap, rank agreement, type
and topic composition, and depth gains. The original 95-source adoption study
has a separate view because its population and measurements differ. Labels are
explicitly assistant-assigned, and popularity is not presented as task quality.

Executable inputs were checkpointed before the final build at
`86c3d038b8c565435f539d08b6eafe8ced08f365`. Exact data checks and browser checks
passed, including all twelve saved pairwise correlations, offline operation,
sorting, filters, details, CSV export and mobile layout. Earlier browser startup
and layout failures are retained separately with their fixes. The resulting
HTML embeds all data and assets and is about 562 KB. Hosted testing found that
HTMLPreview executes JSON script tags; embedding a JavaScript assignment fixed
the compatibility issue without changing scientific inputs. This is a research artifact
on the continuing branch; no promotion to `main` is proposed.

## 2026-09-30 — Compare list composition with the merged union

The user requested source-type and primary-group distributions for each list
and their merged set. The [Composition follow-up](runs/2026-09-30-composition/README.md)
adds a dedicated tab with aligned bars for Bioconda, Bioconductor, PyPI, GitHub
and the canonical-source union. Counts and percentages appear together, with
selectable common bar scales. Each column shows its denominator. The merged
set has 672 distinct sources, not 800 ranking positions; its percentages are
computed from those sources rather than by averaging the four lists.

Both distributions respond to search, type/group/topic filters and list depth.
Category buttons apply filters, and empty columns have undefined percentages.
The previous type bars and group heatmap moved from Compare rankings into this
expanded view. Source labels and rankings remain frozen. Independent checks
against the original CSVs passed for all five populations, both dimensions,
both scales, top-100 and top-200, filtered populations and empty states, alongside
the existing offline interaction and correlation checks. Earlier published
artifacts and their validation remain reachable in Git history.

## 2026-09-30 — Known-source gaps and requested top-300 work

The user requested a knowledge-based discovery-gap audit, all four rankings
extended to top 300, and the tail of primary-group coverage at top 100/200/300.
All three directions were published and read back in issue #5 before further
execution. The [112-repository audit](runs/2026-09-30-discovery-gaps/README.md)
finds 37 absent from the saved GitHub pool, including 11 currently above its
889-star cutoff. The latter include MONAI, Evo 2, OpenFold, RFdiffusion, ESM,
RoseTTAFold, Protenix, Chai, nf-core/rnaseq, StarDist and Flye. Sixteen targeted
search probes reveal vocabulary, compound-topic matching and sparse-metadata
gaps. Three erroneous nominee paths were corrected explicitly. This purposive
panel is not an unbiased recall estimate, and live counts are a separate snapshot.

The depth expansion will remain distinguishable from discovery-pool expansion.
Additional sources due solely to deeper cutoffs should not be confused with
known-source additions or broader queries. Tail comparisons will show all
primary-group counts/shares at the three depths plus explicit low-count summaries
for each list and the distinct-source union.

## 2026-09-30 — Controlled top-300 expansion and primary-group tail

The [top-300 run](runs/2026-09-30-top300/README.md) extends all four lists while
preserving every first-200 ranking row and annotation. The merged union grows
335 → 672 → 1,014 sources at top 100/200/300 and reaches 18 → 22 → 22 primary
groups. More depth strengthens gene regulation (5 → 24 → 54) but leaves
biomechanics (0 → 1 → 1), RNA structure (1 → 2 → 3) and ecology (0 → 1 → 4) thin.

The new tail view tracks groups sparse at 100 with fixed membership, distinguishes
initially absent groups and shows all count bands with explicit denominators.
This prevents a changing count of sparse groups from being mistaken for coverage
improvement. Counts and shares tell different stories. Next useful work is targeted
discovery in thin groups and the missed vocabulary exposed by the gap audit,
with any broader pool kept separate from this controlled depth comparison.

Saved-table checks and offline/public browser validation passed for the new
explorer, including all 18 ranking correlations at three depths, six adoption
pairs, all tail selectors and desktop/mobile layouts. The gap-panel crosswalk
shows that depth alone recovers 10 of the 50 previously absent panel sources,
including Flye through Bioconda; 40 remain absent from the top-300 union. This
is a purposive diagnostic, not unbiased recall. The original 37 GitHub-pool
misses remain pool misses because this run does not broaden that pool.
