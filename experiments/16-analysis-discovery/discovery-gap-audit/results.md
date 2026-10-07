# Reopened discovery audit: project coverage exceeds repository coverage

Issue #16 reopened on 2026-10-07 after the user identified the scvi-tools tutorial
catalog despite a negative inventory result. The original observations remain
valid as bounded main-repository searches, but do not support project-wide
negative conclusions. The published inventory is a historical checkpoint pending
reconciliation; its 502 located / 509 negative totals are not corrected totals.

## Confirmed missed pattern

The repository scanner enumerates Git tree blobs and counts gitlinks (`type:
commit`) without following them. scvi-tools mounts its separate tutorial
repository at `docs/tutorials/notebooks`. A complete recursive parent-tree
response does not enumerate files in that child repository.

Four purposively selected probes at the **original parent revisions and their
recorded child gitlink commits** all recovered Jupyter file paths:

| Inventory project | Declared tutorial repository | Notebook paths |
| --- | --- | ---: |
| scverse/scvi-tools | scverse/scvi-tutorials | 65 |
| scverse/squidpy | scverse/squidpy-tutorials | 50 |
| scverse/liana | dbdimitrov/liana-tutorials | 14 |
| scverse/decoupler | scverse/decoupler-tutorials | 9 |

These are 138 file locators, not 138 inspected, independent or suitable biological
analyses. One small scvi notebook was retrieved and parsed as notebook JSON with
code cells; none was executed. The fixed child commits establish that these
misses existed in the original revision graph, rather than reflecting recent
upstream additions. The stable website and the pinned sources need not be the
same release. Exact revisions, paths, response fingerprints and the content
probe are in [evidence.json](evidence.json).

## Other structural gaps

1. **Documentation traversal was conditional on missing GitHub mapping.** The
   alternative-source pass covered only the 143 unmapped identities. All 871
   mapped identities were excluded from that follow-up, regardless of their
   tree result. Repository discovery prematurely ended project discovery.
2. **Known evidence is not reconciled across collections.** The selected-document
   manifest already contains eight MDAnalysis documents in `MDAnalysis/UserGuide`,
   while the inventory's `MDAnalysis/mdanalysis` row is negative. The official
   [examples catalog](https://userguide.mdanalysis.org/stable/examples/README.html)
   explicitly links its notebook collection in that separate repository. The
   current workbench joins repository and alternative-source summaries, not
   candidate-to-project relationships.
3. **Authoring sources can hide behind rendering and build configuration.** Follow
   official tutorial indexes, Sphinx toctrees, `.gitmodules`, Read the Docs and
   documentation build configuration, download/edit-source links, and declared
   Colab/Binder/nbviewer links. These can reveal separate repositories, branches
   or generated downloads. Follow declared relationships; do not guess sibling
   repositories or count arbitrary dependency links as the project's tutorials.
4. **Text detection remains narrow.** The old scanner probes at most six specially
   named Python/Julia/R/Markdown files. Ordinary tutorial filenames, MyST notebook
   directives, percent-cell scripts and worked RST/Markdown analyses need explicit
   treatment. API examples are not automatically worked biological analyses.
5. **Completeness needs separate fields.** The scanner's `notebook_count_complete`
   expression does not include unexpanded submodules. A complete parent tree,
   complete format detection, complete project-route search, source retrieval and
   suitability screening are different claims.

## Reassessment scope and order

The [queue](reassessment-queue.json) preserves all 871 mapped source identities,
their revisions, previous status, submodule count and unprobed-text count.
Counts were recomputed directly from the saved per-source observations.

| Priority | Scope | Required reassessment |
| --- | ---: | --- |
| 1 | 49 negative repositories with submodules | Resolve declared child URLs and pinned commits; inspect documentation/tutorial children, record dependency-only exclusions and nested/budget limits. Four are confirmed above; the other 45 are unassessed. |
| 2 | All 465 negative mapped repositories, plus one unknown | Inspect official documentation and tutorial catalogs even when a GitHub mapping exists; reconcile previously selected documents first. This includes the priority-1 set. |
| 3 | 405 positive mapped repositories | Check external collections and formats for incomplete breadth. This includes the other 17 repositories with submodules. |
| 4 | All 1,014 source identities | Apply the same route-completeness ledger; revisit capped/error/lead-only searches among the 143 previously followed unmapped sources. Keep source identities fixed and add collection relationships. |

Use project → declared collection → pinned authoring document → rendered/launch
representations as distinct relationships. Keep ownership/relevance evidence on
each edge and deduplicate documents by source identity/version; preserve aliases
without double-counting the same notebook across GitHub, Colab and rendered HTML.
Do not promote an entire tutorial catalog to screened biological evidence.

Acceptance for the next full pass: the four pinned examples must be found;
MDAnalysis must not remain project-negative while its accepted document evidence
exists; every source must report which routes were checked, skipped, capped or
failed; unresolved gitlinks must prevent a completeness claim. Recompute source
and domain totals from the reconciled records, while retaining old observations
and selected-document screening counts. A deliberately excluded dependency-doc
example such as scCoord → generic PyTorch should remain excluded.

## Execution and limits

This is a bounded diagnosis and reassessment specification, not the completed
1,014-source re-audit or a refreshed explorer. No biological inputs, source
analyses, models or paid compute were used. The four project probes are purposive
and cannot estimate a false-negative rate across the inventory.

The probe script was checkpointed before each attempt. Three initial attempts
failed on mixed `.gitmodules` indentation, a trailing URL slash, and the GitHub
Contents API omitting inline content for a large notebook. These are acquisition
failures, not scientific results. Their exact run times/RSS were not captured;
the tool transcript preserves the failures. The corrected probe selects a small
notebook and retains success/failure run records. The successful run is recorded
in [runs.jsonl](runs.jsonl), with a 100 MiB estimate, 23,972 KiB Python peak RSS,
45,672 KiB maximum child RSS, resource guards, one sequential worker and the shared
nonblocking lock. All subprocesses were synchronous and completed.

Reproduction (authenticated GitHub access required):

```bash
flock -n /tmp/exe-codex-local-heavy.lock env POLARS_MAX_THREADS=1 RAYON_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 10 ionice -c 2 -n 7 python experiments/16-analysis-discovery/discovery-gap-audit/inspect.py
```
