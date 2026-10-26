**Current status:** PR-to-task generation works for some repositories at low model cost, but environment reconstruction and validation reliability limit usable yield. Draft PR #63 automates discovery → upstream bootstrap/generation → export → independent controls → accounting, preservation and cleanup. It passes 186 tests and both CI checks; nothing is merged or released. **This issue body is the primary overall summary.** Detailed execution records and HF receipts belong in comments and linked artifacts.

### Observed yield and model cost

These are deduplicated #28/#33/#67 cohort results, with unequal and incomplete coverage. New #67 exports await independent controls. “Positive” means a failing regression passes after the reference fix while tracked passing tests remain passing. “Clean” additionally requires the selected oracle command to finish without other failures; it does not verify the entire repository suite or release readiness.

| Repository / field | Coverage of completed assessment | Exports | Positive | Clean | OpenRouter USD |
| --- | --- | ---: | ---: | ---: | ---: |
| SAMtools / genomics | 735 PRs entered | 0 | 0 | 0 | 0.602694 |
| Scanpy / transcriptomics | 39 entered | 1 | 0 | 0 | 0.880728 |
| MACS / epigenomics | 157 entered | 0 | 0 | 0 | 0.772173 |
| OpenMS / proteomics | Acquisition stopped before entry | 0 | 0 | 0 | 0 |
| LAMMPS / structural-biology tooling | Bootstrap stopped before entry | 0 | 0 | 0 | 0.934599 |
| Matchms / metabolomics | 335 entered | 58 | 58 | 53 | 0.165093 |
| Cobrapy / systems biology | 519 entered; later known task repeated | 12 | 12 | 2 | 0.637134 |
| MMseqs2 / microbiome/sequence analysis | Bootstrap stopped before entry | 0 | 0 | 0 | 0.878520 |
| MNE / neuroscience | 16 entered | 0 | 0 | 0 | 0.607107 |
| OHIF / medical imaging, separate from biology | 160 entered | 12 | 12 | 12 | 0.923163 |
| AnnData / transcriptomics | Partial: 2 recent PRs returned | 0 | 0 | 0 | 0.313983 |
| Biopython / sequence-analysis tooling | Partial: 2 PRs, two comparisons | 0 | 0 | 0 | 1.033545 |
| DendroPy / phylogenetics | Partial: 2 recent PRs returned | 1 | 1 | 0 | 0.087849 |
| NiBabel / neuroimaging | 577 / 812 historical PRs entered; 235 backlog; prior small-run results included | 20 | 3 | 2 | 1.001352 |
| **Recorded cohort total** | **Incomplete coverage** | **104** | **86** | **69** | **8.837940** |

The ten-repository history survey inventoried 23,285 PRs; 1,961 entered, 100 were omitted by discovery and 21,224 remained backlog. Zero exports can therefore reflect a blocked or unfinished pipeline. These rows do not predict tasks per repository. Subsequent control attempts improved the original 83-export subset to 82 positive/67 clean without creating new tasks. The repeated Cobrapy task adds cost, not a unique export. Earlier #27 separately produced two AnnData exports, one cleanly verified and one timed out; those are outside this table and are excluded from regeneration. The adapted MACS rebuild diagnostic is also separate from fresh-generation yield.

### Broader reassessment underway

NiBabel generation completed: **577 PRs entered → 19 new exports**, **$0.527772 / 14 original model calls**, **4.334598333 CPUh**, generation cleanup verified. Its 2,464-file evidence archive exposed our connector’s 1,000-file small-input limit before controls. A bounded, tested evidence-verification adaptation now imports that same sealed generation with **zero regeneration/model calls**; independent controls have resumed under a new frozen plan. The live table shows which repositories are running or queued.

<!-- biotasks67-monitor-start -->
**Monitored progress — Oct 26, 02:15 PM EDT:** `monitoring`. The original controller owns execution; this monitor only reads artifacts and reports changes.

| Repository | Stage | Entered / queued | Exports | Positive / clean controls | Settled OpenRouter USD |
| --- | --- | ---: | ---: | ---: | ---: |
| NiBabel | waiting for cleanup capacity | 577 / 812 | 19 | 2 / 1 | 0.527772 |
| DendroPy | generation running or finalizing | pending / 72 | pending | pending | pending |
| AnnData | not started | pending / 1529 | pending | pending | pending |
| Biopython | not started | pending / 2616 | pending | pending | pending |

Settled new model cost: **$0.527772**; unfinished billing remains pending. Shared ledger: **$2.724375 settled model cost**, **19.599 CPUh used / 6.667 reserved**; outstanding dollars include the existing storage reserve. Counts enter this block only from retained readbacks, with positive/clean controls requiring verified cleanup.
<!-- biotasks67-monitor-end -->

#67 now covers the four partially assessed repositories using complete historical inventories through October 17, 2026: **NiBabel 812, DendroPy 72, AnnData 1,531, Biopython 2,616**. After excluding the two known AnnData exports, **5,029 PR identities are queued**. Successive batches of at most 100 reuse the bootstrap cache and cumulative model allowance; there is no per-repository count cap. The monitor above records the active repository and stage; remaining work shares the original budget. New results enter the table only after reconciliation. Original failure modes are retained; no additional repair-model stage or task-specific fixes.

### Costs and limits

Completed history-wide #28 cost **$6.113565** OpenRouter, or **$12.088851 including September**. Completed incremental #33 work cost **$2.196603 / 61 calls**, using **14.892111111 reserved CPU-hours**. Together those completed ledgers account for **$14.285454**, excluding earlier experiments such as #24–#27. These are model charges, not all-in compute/storage prices.

The #67 continuation uses the same cumulative **$90 operating ceiling, strictly below $100 extra, and 32 reserved CPU-hour ceiling**. Current reservations and reconciled charges are in the monitored progress block; the **$10 storage reserve remains unreconciled**. No new capacity was purchased. Cost per usable task is not yet established; bootstrap amortization, unsuccessful runs, controls and portability matter.

The principal unresolved mechanisms are source/import provenance, compiled-artifact rebuilding, test selection/parser coverage, verifier timeout cancellation and guaranteed owner-worker cleanup capacity. Longer timeouts recovered OpenMS acquisition but did not complete Scanpy controls at 1,200 seconds. NiBabel demonstrated one fresh clean selected-file task; DendroPy remains positive but unclean. Matchms raw redistribution is restricted, six original builds are absent, and cold-worker portability is only selectively tested. Historical counts are not a released task inventory.

### Review and evidence

The agent reviewed 32 research/follow-up issues and closed 27 completed questions. Five substantive follow-ups remain agent-owned: #29, #32, #56, #60 and #64; active reassessment is #67. The user reviews this overall summary and consolidated PR #63. No individual subissue review is requested.

[Reconciled task ledger](https://github.com/Open-Athena/biotasks/blob/488a22ab/experiments/33-unattended-validation/task-execution-ledger.json) · [Completed-run model accounting](https://github.com/Open-Athena/biotasks/blob/488a22ab/experiments/33-unattended-validation/model-cost-by-run.json) · [Delivery and modification rationale](https://github.com/Open-Athena/biotasks/blob/488a22ab/experiments/33-unattended-validation/conclusion.md) · [Issue review register](https://github.com/Open-Athena/biotasks/blob/043dd27e/experiments/33-unattended-validation/issue-review-2026-10-26.md). Detailed progress and artifact receipts remain in comments.
