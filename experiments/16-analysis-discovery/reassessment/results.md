# Project-wide reassessment results — 2026-10-07

The bounded reassessment is complete for all **1,014 fixed source identities**.
It confirms **34 source-level false negatives** in the previous inventory.
Source-level document presence increases from **502 to 536**. Main-repository
format scanning missed tutorial submodules, separate documentation collections,
text notebooks and documentation download links. Successful previous evidence is
retained; completion of this protocol does not mean exhaustive web discovery.

## Notebook counts across all supported formats

- **4,057 distinct notebook/literate documents across 454 repositories** with detections.
- **220 additional package, archive or documentation-download source locations**.
- **4,277 notebook/literate documents overall**, with **9 rendered-only fallbacks** reported separately.
- The [repository-count CSV](repository-counts.csv) includes **937 checked/linked repository identities**, including zero detections; the [source-count CSV](source-counts.csv) retains the original 1,014 project identities.

Per-repository counts sum to 4,090, whereas the
deduplicated total across repositories is 4,057: verified
copies can be represented in more than one repository. Project rows distinguish
main-repository notebooks from linked collections or package sources. Counts use
all recorded paths, not the old summary's five displayed examples.

| Format | Distinct documents across all locations |
| --- | ---: |
| Jupyter | 3,233 |
| R Markdown | 781 |
| Sweave/knitr | 156 |
| Quarto | 55 |
| Wolfram notebook | 25 |
| Jupytext | 14 |
| marimo | 6 |
| Percent-cell notebook | 4 |
| MyST notebook | 1 |
| MATLAB Live Script | 1 |
| .NET Interactive | 1 |

Notebook identity uses repository/path across recorded snapshots, retaining all
version evidence. Exact-byte copies are merged within repositories and between
collections explicitly associated with the same project. Documentation downloads
are merged with repository source only when their bytes match a complete Git
blob. Explicit Jupytext declarations and established versioned vignette groupings
also reconcile representations. **254 additional source-location aliases** were
recorded. Four repository renames/redirects were canonicalized using GitHub tree
response URLs. Evidence is in [alias-evidence.json](alias-evidence.json) and
[repository-alias-evidence.json](repository-alias-evidence.json).

These are discovered source documents, not independent analyses, a single
current checkout, or executable/biologically suitable tasks. Different-content
exports and uncertain pairings can remain separate. Files can be examples,
fixtures, templates or non-biological content; format detection is not screening.
Rendered fallbacks and unconfirmed HTML tutorial leads are not counted as
recovered authoring notebooks.

## Corrected examples

| Project | All-format notebooks | Main repository | Linked collections/downloads |
| --- | ---: | ---: | ---: |
| scvi-tools | 65 | 0 | 65 |
| squidpy | 50 | 0 | 50 |
| liana | 15 | 0 | 15 |
| decoupler | 9 | 0 | 9 |
| mdanalysis | 38 | 0 | 38 |
| theislab/scvelo | 14 | 0 | 14 |
| danforthcenter/plantcv | 11 | 0 | 11 |

The original four submodule regressions retain all 138 pinned Jupyter paths.
LIANA also has a separately located documentation download whose equivalence to
the pinned source was not established. MDAnalysis is now joined to its official
UserGuide collection, including the eight previously selected documents. The
candidate-to-inventory reconciliation records every original candidate in
[candidate-reconciliation.json](candidate-reconciliation.json); only established
project relationships are attached.

## Source-level outcomes

| Outcome | Sources |
| --- | ---: |
| Document located | 536 |
| Tutorial lead only | 83 |
| None located within bounds | 306 |
| Unresolved search | 89 |
| Total | 1,014 |

Besides the 34 corrected false negatives, 81 previous negatives now have tutorial
leads and 88 are explicitly unresolved after access failures. The old unresolved
source remains unresolved. All previously detected notebook paths remain in the
reconciled evidence. Domain labels and ranking memberships remain unchanged.
[summary.json](summary.json) contains per-source transitions and domain totals;
[documents.jsonl](documents.jsonl) is the deduplicated document registry.

## Reusable discovery corrections

1. Inspect Git submodule declarations and pinned gitlinks, rather than treating a
   recursive parent-tree response as the whole project. All 66 original
   submodule-bearing parents were reassessed. Across the encountered graphs,
   11 documentation/tutorial gitlinks were inspected, one failed access, and 196
   dependency or unclassified gitlinks remain explicitly unexpanded.
2. Follow declared documentation for GitHub-mapped projects too. Separate tutorial
   repositories occur beyond scvi-tools, including MDAnalysis, scVelo, omicverse,
   SpikeInterface, PlantCV and others.
3. Resolve relative links against the final redirected documentation URL. A
   dedicated follow-up repaired versioned-path traversal and reconciled known
   candidates across 198 source ledgers.
4. Preserve ownership and scope. Theme footers, generic PyTorch tutorials, cloud
   sample repositories and downstream dependencies are not automatically project
   notebook collections. A specifically linked AlphaGenome notebook does not
   justify assigning all Vertex AI samples to AlphaGenome; MONAI tutorial
   directories are likewise scoped to the declared relationship.
5. Count all supported formats and preserve known representation relationships.
   Report source presence, repository counts, project attribution and global
   deduplicated counts as different quantities.

## Bounds, validation and execution evidence

The main pass produced 1,014 route ledgers and 6,339 request events, including
cache reuse; 95 sources reused successful prior package evidence without new
requests. It revisited declared documentation regardless of repository status,
while retaining earlier authoring-source recovery. The main and supplemental
records preserve requests, hashes, revisions, declarations and route outcomes.
The main pass read declared documentation for 433 sources; others can have no
eligible declared target, prior package evidence, or failed/bounded access.

**495 source ledgers have recorded access or search-budget
limits.** Four documentation pages, two linked collections, selected text probes,
32 requests per source and response caps bound a pass. Reassessment completion
means every source received the protocol, not that every possible document was
found. Zero located is never asserted as absence. Failed routes, unclassified
submodules, uncertain HTML leads and unprobed text remain visible in the explorer.

[Accounting and regression validation](validation.json) passes: fixed identities
and labels, every original detected path, all-format and CSV totals, document
alias/version handling, vignette pairing, text-notebook detection, all four pinned
submodule regressions, MDAnalysis reconciliation and exclusion of generic PyTorch
content. [Local browser checks](../evidence/browser-reassessment-local.json)
passed on the rebuilt presentation, including responsive views, filtering,
notebook sorting, export and evidence inspection. [Public browser checks](../evidence/browser-reassessment-public.json) also
passed against published presentation commit
`dd5bc22f54102f6165b2c3e940b2d90a9ddd7880`, with no page errors
and 284,184 KiB peak child RSS.

A sandbox browser invocation stalled before Chromium startup and was terminated
(exit 143), with no result claimed. Follow-up UI checks exposed a lazy-inspector
timing assumption and missing prior-acquisition detail; the check now waits for
loaded evidence, and the inspector preserves both original and new provenance.
The latter failure is retained in
[the failure record](../evidence/browser-reassessment-prior-evidence-failure.json).

No source analyses, model calls, biological-data downloads or paid compute were
performed. The selected-document collection remains 100 candidates, 98 substantive
static inspections, two access-only leads and 70 apparently suitable documents.
No new discovery count is a scientific validation score.

Acquisition and checks used the shared nonblocking lock, one worker, thread caps,
reduced CPU/I/O priority and resource guards. [runs.jsonl](runs.jsonl) records
execution times, exit status and peak RSS. The main successful acquisition took about 18 minutes 33 seconds, with
77,292 KiB peak self RSS. The largest recorded
builder peak was 235,692 KiB; local browser child peak was 276,600 KiB. One initial
acquisition stopped on a malformed documentation URL after 56 completed source
records; the parser was fixed and the resumed run completed. The long
run's original logger captured Git HEAD at completion rather than start; its
actual scanner revision and hash are preserved in the explicit
[execution correction](run-execution-correction.json). Later runners capture the
revision at start. [Input fingerprints](input-sha256.json) anchor derived results.
