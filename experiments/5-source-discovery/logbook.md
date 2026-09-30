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
