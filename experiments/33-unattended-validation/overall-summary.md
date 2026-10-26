# PR-to-task work: overall status, yield and cost

Updated 2026-10-26. This is the overall review document for epic #33 and its predecessor #28. Detailed execution logs remain in issue comments and linked immutable research/HF artifacts. The user reviews the overall result; the agent owns review and disposition of the individual research issues.

The pipeline can produce useful biology coding tasks cheaply in model dollars, but yield depends strongly on repository compatibility. We have **83 historical exports, 82 with at least one positive control pair and 67 with at least one clean oracle command**. These are historical observations, not 67 released, portable tasks. The later implementation automates generation through validation and cleanup; a fresh NiBabel case demonstrates the full path. Draft [PR #63](https://github.com/Open-Athena/biotasks/pull/63) is open, with 186 local tests and both CI checks passing at c19e7369. Nothing is merged or released.

## Historical ten-repository survey

Counts below combine the frozen history-wide #28 exports with later unchanged-task control attempts recorded in the [identity ledger](task-execution-ledger.json). Costs are the original history-wide generation costs only. Later controls do not create new exports. “Entered” is PRs reaching the pipeline, not PRs for which both native test stages completed.

| Repository / field | PRs entered | Exports | Ever positive pair | Ever clean oracle | OpenRouter USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| SAMtools / genomics | 735 | 0 | 0 | 0 | 0.602694 |
| Scanpy / transcriptomics | 39 | 1 | 0 | 0 | 0.880728 |
| MACS / epigenomics | 157 | 0 | 0 | 0 | 0.772173 |
| OpenMS / proteomics | 0 | 0 | 0 | 0 | 0 |
| LAMMPS / structural-biology tooling | 0 | 0 | 0 | 0 | 0.934599 |
| Matchms / metabolomics | 335 | 58 | 58 | 53 | 0.165093 |
| Cobrapy / systems biology | 519 | 12 | 12 | 2 | 0.349488 |
| MMseqs2 / microbiome/sequence analysis | 0 | 0 | 0 | 0 | 0.878520 |
| MNE / neuroscience | 16 | 0 | 0 | 0 | 0.607107 |
| OHIF / medical imaging, reported separately from biology | 160 | 12 | 12 | 12 | 0.923163 |
| **Total** | **1,961** | **83** | **82** | **67** | **6.113565** |

Biology excluding OHIF: **71 exports / 70 ever-positive / 55 ever-clean**. OHIF contributes 12/12/12. The original #28 snapshot had only 74 positive and 59 clean; later controls recovered eight previously uncompleted pairs. The reconciled ledger has 93 pair attempts/slots, not 93 unique tasks.

The inventory contains 23,285 PRs: 1,961 entered, 100 omitted by discovery and 21,224 backlog. Listing caps, bootstrap failures and bounded execution prevented an exhaustive census. In particular, zero returned/entered PRs is not evidence that a repository has zero suitable tasks. These results do not estimate a reliable future tasks-per-repository rate.

An **export** is a generated task bundle. A **positive pair** means the unchanged task fails its targeted regression before the PR fix and passes after it, retaining tracked passing tests. A **clean oracle command** additionally has no other failures in the selected verification command. Neither validates every test in the repository, solver difficulty, source provenance in all cases, distribution rights or reproducibility on a new worker.

Most exports are Matchms; its raw evidence is withheld from public redistribution, so public summaries do not make those 58 bundles a public dataset. Six original builds are absent. Cold-worker portability was measured only for selected cases; counts above must not be described as release-ready inventory.

Sources: [original cohort](https://github.com/Open-Athena/biotasks/blob/fed8da42/experiments/28-catalogued-fields/history-wide/cohort-report.md), [failure diagnosis](https://github.com/Open-Athena/biotasks/blob/af4b8656/experiments/28-catalogued-fields/history-wide/failure-diagnosis.md), [reconciled ledger](task-execution-ledger.json).

## Later unattended-pipeline trials

These are small selected integration experiments, not another broad yield survey. Model costs include failed experiments; controls and local connector fixes did not add repair-model calls.

| Repository | Exports in these runs | Independent outcome | Actual OpenRouter USD |
| --- | ---: | --- | ---: |
| Cobrapy | 1, already-known PR | Original reconstruction failed before controls; explicit APT experiment then timed out | 0.287646 |
| AnnData | 0 | Patched workspace was not the imported package; no F2P | 0.313983 |
| Biopython, two comparisons | 0 | Structural filter first; compiled extensions removed during cleanup in the declared comparison | 1.033545 |
| DendroPy | 1 | Positive tracked pair, but four unrelated failures; not strict-clean | 0.087849 |
| NiBabel | 1 | Clean pair: 9 regression tests repaired, 37 existing tests preserved | 0.473580 |
| **Total** | **3 export instances, including the known Cobrapy task** | **One fresh strict-clean end-to-end case** | **2.196603** |

The NiBabel command covers one selected test file. DendroPy controls reused the existing generation; no regeneration was needed. Separately, the MACS offline-rebuild diagnostic recovered one clean control pair from archived inputs, but was not a fresh official generation or part of the original 83 exports. Replays of historical Cobrapy/OHIF tasks also do not increase unique-task counts.

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

The next useful work is correctness and reproducibility on the existing failures, followed by a prespecified broader yield measurement with fixed discovery limits. More generation alone would inflate candidate counts without establishing usable-task yield. No additional run is started by this review.

## Issue ownership and review

The agent reviewed the 28 epic children and four predecessor follow-ups. Completed bounded experiments, including negative/inconclusive results and implementation extractions now consolidated in PR #63, are closed by the agent. Five substantive research follow-ups remain open: #29 timeout/scheduling and MMseqs bootstrap coverage, #32 test-selection/runner coverage, #56 code-under-test provenance, #60 compiled rebuilding, and #64 subtest identities. They are research backlog owned by the agent, not individual review requests to the user.

The detailed [issue review register](issue-review-2026-10-26.md) records all 32 decisions. Epic #33 and consolidated draft PR #63 remain the overall review surface; no automatic merge or release. Earlier evidence and audit snapshots retain their original dates and conclusions; this review supersedes their instruction to leave every child open for human review.
