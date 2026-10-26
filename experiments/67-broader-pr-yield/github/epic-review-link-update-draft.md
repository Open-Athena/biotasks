**Current status:** The bounded broader run is held at its CPU reservation guard after producing **26 new exports** and completing **7 positive / 6 clean** NiBabel control pairs. All admitted runs are retained and cleaned. **19 pending controls for existing exports and the AnnData/Biopython first runs remain unadmitted. This issue body is the primary overall summary.**

PR-to-task generation works for some repositories at low model cost, while environment reconstruction and validation reliability limit usable yield. Draft PR #63 automates discovery → upstream bootstrap/generation → export → independent controls → accounting, preservation and cleanup. It passes 186 tests and both CI checks; nothing is merged or released.

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
| DendroPy / phylogenetics | 27 / 72 historical PRs entered; 45 backlog; prior small-run results included; interrupted final batch | 8 | 1 | 0 | 0.175263 |
| NiBabel / neuroimaging | 577 / 812 historical PRs entered; 235 backlog; prior small-run results included | 20 | 8 | 7 | 1.001352 |
| **Recorded cohort total** | **Incomplete coverage** | **111** | **91** | **74** | **8.925354** |

The ten-repository history survey inventoried 23,285 PRs; 1,961 entered, 100 were omitted by discovery and 21,224 remained backlog. Zero exports can therefore reflect a blocked or unfinished pipeline. These rows do not predict tasks per repository. Subsequent control attempts improved the original 83-export subset to 82 positive/67 clean without creating new tasks. The repeated Cobrapy task adds cost, not a unique export. Earlier #27 separately produced two AnnData exports, one cleanly verified and one timed out; those are outside this table and are excluded from regeneration. The adapted MACS rebuild diagnostic is also separate from fresh-generation yield.

### Broader reassessment underway

The first two broader historical runs produced **26 new exports from 604 entered PRs**: NiBabel **19 / 577**, DendroPy **7 / 27**, at **$0.615186 / 19 original model calls**. Both generation archives and owner cleanup are verified. DendroPy reached its frozen overall native time limit; its interrupted-batch coverage was reconciled from the original append-only entry events, leaving **45 not entered**. Its seven exports await independent controls. NiBabel’s sealed archive was recovered through a bounded source-inventory verification adaptation, with no regeneration. Independent controls have resumed automatically under the same frozen plan; the tables show their verified results and the remaining queued repositories.

<!-- biotasks67-monitor-start -->
**Verified checkpoint — Oct 26, 04:37 PM EDT:** `budget_admission_hold`. The controller stopped before the next job was admitted; all admitted work is retained and cleaned.

| Repository | Stage | Entered / queued | Exports | Positive / clean controls | Settled OpenRouter USD |
| --- | --- | ---: | ---: | ---: | ---: |
| NiBabel | controls budget hold | 577 / 812 | 19 | 7 / 6 | 0.527772 |
| DendroPy | export ready | 27 / 72 | 7 | pending | 0.087414 |
| AnnData | not started | pending / 1529 | pending | pending | pending |
| Biopython | not started | pending / 2616 | pending | pending | pending |

Settled model cost for this reassessment: **$0.615186 / 19 original calls**; all admitted generation billing is reconciled. Shared ledger: **$2.811789 settled model cost**, **25.714 CPUh used / 0.000 reserved**; outstanding dollars include the existing storage reserve. Counts enter this block only from retained readbacks, with positive/clean controls requiring verified cleanup.
<!-- biotasks67-monitor-end -->

#67 now covers the four partially assessed repositories using complete historical inventories through October 17, 2026: **NiBabel 812, DendroPy 72, AnnData 1,531, Biopython 2,616**. After excluding the two known AnnData exports, **5,029 PR identities are queued**. Successive batches of at most 100 reuse the bootstrap cache and cumulative model allowance; there is no per-repository count cap. The monitor above records the active repository and stage; remaining work shares the original budget. New results enter the table only after reconciliation. Original failure modes are retained; no additional repair-model stage or task-specific fixes.

### Costs and limits

Completed history-wide #28 cost **$6.113565** OpenRouter, or **$12.088851 including September**. Completed incremental #33 work cost **$2.196603 / 61 calls**, using **14.892111111 reserved CPU-hours**. Together those completed ledgers account for **$14.285454**, excluding earlier experiments such as #24–#27. These are model charges, not all-in compute/storage prices.

The current campaign retains its **$90 operating ceiling, strictly below $100 extra, and 32 CPU-hour admission ceiling**. It stopped with **25.713971111 CPUh settled and zero reservations**: the next unchanged job needs **6.333333333 CPUh reserved**, which would total **32.047304444**. The **$10 storage reserve remains unreconciled**. No new capacity was purchased.

A [prepared amendment](https://github.com/Open-Athena/biotasks/blob/17e706e2/experiments/67-broader-pr-yield/cpu-budget-continuation-proposal.md) to **64 cumulative CPU-hours total is pending authorization**. It changes only that campaign allowance on existing reserved TRC workers; the monetary limit, per-job resources, native deadlines, model settings and no-repair policy stay unchanged. It would resume pending controls and the two already-frozen repository runs, without regenerating NiBabel or DendroPy. Cost per usable task is not yet established; bootstrap amortization, unsuccessful runs, controls and portability matter.

The principal unresolved mechanisms are source/import provenance, compiled-artifact rebuilding, test selection/parser coverage, oversized Docker command arguments, verifier timeout cancellation and guaranteed owner-worker cleanup capacity. Longer timeouts recovered OpenMS acquisition but did not complete Scanpy controls at 1,200 seconds. NiBabel has produced clean selected-file tasks; DendroPy’s earlier control was positive but unclean, and its new exports await independent controls. Matchms raw redistribution is restricted, six original builds are absent, and cold-worker portability is only selectively tested. Historical counts are not a released task inventory.

### Review and evidence

The agent reviewed 33 research/follow-up issues and closed 27 completed questions. Six substantive follow-ups remain agent-owned: #29, #32, #56, #60, #64 and #68; active broader reassessment is #67. The user reviews this overall summary and consolidated PR #63. No individual subissue review is requested.

[Reconciled task ledger](https://github.com/Open-Athena/biotasks/blob/488a22ab/experiments/33-unattended-validation/task-execution-ledger.json) · [Completed-run model accounting](https://github.com/Open-Athena/biotasks/blob/488a22ab/experiments/33-unattended-validation/model-cost-by-run.json) · [Delivery and modification rationale](https://github.com/Open-Athena/biotasks/blob/488a22ab/experiments/33-unattended-validation/conclusion.md) · [Issue review register](https://github.com/Open-Athena/biotasks/blob/46f7f7a5/experiments/33-unattended-validation/issue-review-2026-10-26.md). Detailed progress and artifact receipts remain in comments.



[Current fully cleaned checkpoint](https://huggingface.co/buckets/open-athena/biotasks/tree/research/67-broader-pr-yield/2026-10-26/3e54fbc08253b93a66471b83c8fbd6dec94071f261abf3f462c768fd7e4e59ed) · [Reviewed large-command transport finding](https://github.com/Open-Athena/biotasks/issues/68). The HF snapshot contains only own aggregate metrics and proof provenance; raw task/source/test traces remain private pending redistribution review.
