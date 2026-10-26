# PR-to-task work: overall status, yield and cost

Updated 2026-10-26. This is the overall review document for epic #33 and its predecessor #28. Detailed execution logs remain in issue comments and linked immutable research/HF artifacts. The user reviews the overall result; the agent owns review and disposition of the individual research issues.

The pipeline can produce useful biology coding tasks cheaply in model dollars, but yield depends strongly on repository compatibility. Across the recorded #28/#33 cohorts we have **85 unique exports, 84 with at least one positive control pair and 68 with at least one clean oracle command**. The original ten-repository subset contributes 83/82/67; DendroPy and NiBabel add two exports. These are observations from unequal, incomplete coverage, not 68 released, portable tasks. The later implementation automates generation through validation and cleanup; a fresh NiBabel case demonstrates the full path. Draft [PR #63](https://github.com/Open-Athena/biotasks/pull/63) is open, with 186 local tests and both CI checks passing at c19e7369. Nothing is merged or released.

## Broader reassessment in progress

[Issue #67](https://github.com/Open-Athena/biotasks/issues/67) now executes the broader assessment requested after this summary. Full inventory through October17 contains 5,031 PRs across NiBabel, DendroPy, AnnData and Biopython; excluding two already-exported AnnData tasks from #27 leaves 5,029 queued. Successive batches are at most100, not a repository cap. Original NiBabel job is submitted on reserved TRC CPUs; remaining stages/repositories share the existing budget. No new yield is counted until measured. The totals below intentionally cover #28/#33, not the earlier #27 AnnData exports.

## Repository yield: all assessed repositories

One table covers both the history-wide survey and the four partially assessed repositories. Counts are unique PR tasks in these recorded #28/#33 cohorts, not generation attempts; they exclude earlier #24/#25 work and the separately adapted MACS diagnostic. Costs include the recorded #33 generation comparisons, including failed and duplicate-task runs. Different discovery windows and execution profiles mean these rows are not comparable estimates of population yield.

| Repository / field | Coverage so far | Unique exports | Ever positive pair | Ever clean oracle | OpenRouter USD |
| --- | --- | ---: | ---: | ---: | ---: |
| SAMtools / genomics | History-wide; 735 entered | 0 | 0 | 0 | 0.602694 |
| Scanpy / transcriptomics | History-wide; 39 entered | 1 | 0 | 0 | 0.880728 |
| MACS / epigenomics | History-wide; 157 entered | 0 | 0 | 0 | 0.772173 |
| OpenMS / proteomics | Acquisition stopped before entry | 0 | 0 | 0 | 0 |
| LAMMPS / structural-biology tooling | Bootstrap stopped before entry | 0 | 0 | 0 | 0.934599 |
| Matchms / metabolomics | History-wide; 335 entered | 58 | 58 | 53 | 0.165093 |
| Cobrapy / systems biology | History-wide; 519 entered; later repeated known PR | 12 | 12 | 2 | 0.637134 |
| MMseqs2 / microbiome/sequence analysis | Bootstrap stopped before entry | 0 | 0 | 0 | 0.878520 |
| MNE / neuroscience | History-wide; 16 entered | 0 | 0 | 0 | 0.607107 |
| OHIF / medical imaging, separate from biology | History-wide; 160 entered | 12 | 12 | 12 | 0.923163 |
| AnnData / transcriptomics | **Partial:** 2 returned PRs, one-day window | 0 | 0 | 0 | 0.313983 |
| Biopython / sequence-analysis tooling | **Partial:** 2 PRs, two declared comparisons | 0 | 0 | 0 | 1.033545 |
| DendroPy / phylogenetics | **Partial:** 2 returned PRs, three-day window | 1 | 1 | 0 | 0.087849 |
| NiBabel / neuroimaging | **Partial:** 1 returned PR, limit one | 1 | 1 | 1 | 0.473580 |
| **Observed total across these cohorts** | **Incomplete and unequal coverage** | **85** | **84** | **68** | **8.310168** |

Biology excluding OHIF contributes **73 exports / 72 ever-positive / 56 ever-clean**; OHIF contributes 12/12/12. Cobrapy's repeated PR1497 adds $0.287646 but no new unique task. The original ten-repository subset remains 83/82/67 and $6.113565. Its original #28 snapshot had only 74 positive and 59 clean; later controls recovered eight previously uncompleted pairs. Its 93 pair attempts/slots are not 93 unique tasks.

For the historical ten, inventory/returned/entered/backlog remain in the [original cohort table](https://github.com/Open-Athena/biotasks/blob/fed8da42/experiments/28-catalogued-fields/history-wide/cohort-report.md): 23,285 inventoried, 1,961 entered, 100 discovery-omitted and 21,224 backlog. “Entered” does not mean both native test stages completed. Listing caps, bootstrap failures and bounded execution prevented an exhaustive census. Zero returned/entered PRs is not evidence of zero suitable tasks.

For the four newer repositories, a history-wide inventory and backlog have **not been measured**. Their frozen discovery scopes were AnnData October 19 (limit50; stable-branch bootstrap), Biopython October 18–19 (limit50), DendroPy October 22–24 (limit2), and NiBabel October 18–24 (limit1), all inclusive in 2026. Two Biopython comparisons reused the selected PRs with declared different settings; they do not double the discovery denominator. These narrow results establish observed outcomes only, not expected tasks per repository.

An **export** is a generated task bundle. A **positive pair** means the unchanged task fails its targeted regression before the PR fix and passes after it, retaining tracked passing tests. A **clean oracle command** additionally has no other failures in the selected verification command. Neither validates every test in the repository, solver difficulty, source provenance in all cases, distribution rights or reproducibility on a new worker.

Most exports are Matchms; its raw evidence is withheld from public redistribution, so public summaries do not make those 58 bundles a public dataset. Six original builds are absent. Cold-worker portability was measured only for selected cases; counts above must not be described as release-ready inventory.

Sources: [original cohort](https://github.com/Open-Athena/biotasks/blob/fed8da42/experiments/28-catalogued-fields/history-wide/cohort-report.md), [failure diagnosis](https://github.com/Open-Athena/biotasks/blob/af4b8656/experiments/28-catalogued-fields/history-wide/failure-diagnosis.md), [reconciled ledger](task-execution-ledger.json).

## Why processing stopped, and what the newer results establish

The four newer repositories belong in the same yield assessment, but broad processing remains unfinished. AnnData produced no export because validation imported installed code rather than the patched workspace. Biopython first encountered structural filtering; the declared filter/path comparison then lost compiled extensions during cleanup and failed collection. DendroPy produced a tracked-positive export but four unrelated failures prevent strict-clean acceptance. NiBabel produced a clean task with nine regression tests repaired and 37 existing tests preserved; the command covers one selected file.

DendroPy controls reused its existing generation. The later Cobrapy run repeated an already-known task and failed reconstruction; the separate APT experiment then timed out. None of those repetitions adds a unique task. Separately, the MACS offline-rebuild diagnostic recovered a clean pair from archived inputs with an explicit adaptation; it was not a fresh official generation and remains outside the table's cohort definition.

The next yield step is broader discovery and processing for AnnData, Biopython, DendroPy and NiBabel under one recorded protocol: a common historical cutoff, explicit pagination/listing caps, deduplication against existing PR identities, frozen execution settings and serial cumulative budget accounting. Record inventory, returned PRs, entered/filtered/completed stages, exports, both controls, failure reasons, remaining backlog, actual model cost and CPU usage for each repository. Preserve existing results and label any setting change as a separate comparison. No unrecorded repair or regeneration of known tasks. This documentation update starts no new paid or native run.

[Detailed delivery, changes and rationale](conclusion.md) · [per-run model accounting](model-cost-by-run.json) · [NiBabel evidence](https://github.com/Open-Athena/biotasks/blob/0d7344963b050bf3743de14d4d6858039c2c6201/experiments/66-fresh-nibabel/results.md).

## Cost interpretation

- History-wide #28: **$6.113565** OpenRouter; **$12.088851** including its earlier September batch.
- Incremental #33: **$2.196603**, 61 original upstream model calls, and **14.892111111 allocated CPU-hours** on existing reserved capacity. No outstanding CPU/model reservations or active paid run.
- Together #28 and #33 account for **$14.285454** in model charges. This is not a lifetime project total: earlier #24/#25 work is outside these ledgers.
- #33 retains an **unreconciled $10 storage reserve**. Reserved CPU allocation is measured, but no all-in dollar price for compute/storage is established here.

The later generation experiments cost about **$0.09–$0.66 per run**, including runs yielding nothing; Biopython's two runs total $1.03. Bootstrap expense can be amortized over many PRs, explaining the inexpensive original Matchms/Cobrapy batches. Dividing these costs by clean tasks would not establish a general price per usable task: selection, failures, validation compute, portability and redistribution all matter.

## What works, and what remains

The candidate automates frozen discovery, the official built-in LLM bootstrap, export, deterministic controls, accounting, HF readback and owned cleanup. Codex is outside its execution loop. Generic wrapper/options are explicit; no per-task repairs or additional repair-model stage are included.

The largest remaining reliability problems are environment reconstruction and import identity, revision-specific compiled artifacts, incomplete test/parser coverage, and timeout cancellation. Increasing timeouts is sometimes useful (OpenMS checkout completed in 77.9 seconds versus a 60-second deadline), but Scanpy still did not complete controls at 1,200 seconds. A package installation error or missing compiled extension will not be fixed by waiting longer.

Broader yield measurement for the four partially assessed repositories is the next assessment step. Preserve the known failure mechanisms as explicit outcomes and keep any correctness improvements in separate declared comparisons; do not silently repair inputs to improve yield.

## Issue ownership and review

The agent reviewed the 28 epic children and four predecessor follow-ups. Completed bounded experiments, including negative/inconclusive results and implementation extractions now consolidated in PR #63, are closed by the agent. Five substantive research follow-ups remain open: #29 timeout/scheduling and MMseqs bootstrap coverage, #32 test-selection/runner coverage, #56 code-under-test provenance, #60 compiled rebuilding, and #64 subtest identities. They are research backlog owned by the agent, not individual review requests to the user.

The detailed [issue review register](issue-review-2026-10-26.md) records all 32 decisions. Epic #33 and consolidated draft PR #63 remain the overall review surface; no automatic merge or release. Earlier evidence and audit snapshots retain their original dates and conclusions; this review supersedes their instruction to leave every child open for human review.
