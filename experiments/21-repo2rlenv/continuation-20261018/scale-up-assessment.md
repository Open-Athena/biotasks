# Scale-up assessment: current evidence, not final campaign conclusions

As of 2026-10-19 19:34 UTC. Accepted/scored totals: 30/30. This assessment consolidates the first pass and continuation; the campaign remains open.

## Answers for a scale-up decision

**Recommendation: scale historical extraction first; treat GLM-authored routes as experimental until acceptance is automated.** These are qualitative judgments from this small, curated sample, not measured production yields. The detailed route/repository tables and task ledger below include both successful and unsuccessful outcomes and their causes.

| Question | Current answer | What would change the conclusion? |
| --- | --- | --- |
| Which pipelines should we scale? | Native PR-runtime has the strongest correctness evidence (6 accepted); native commit-runtime is promising (1 accepted). PR-diff works across languages (12 accepted) for similarity rewards only. Smith (5), Flow (2), R2E-Gym (1) and Scaler (3 within one family) have useful examples with material limitations. | A held-out batch using frozen reusable profiles and acceptance gates, with rejected candidates and duplicate source families included in the accounting. |
| Which repositories work? | Biopython: 5 correctness + 3 similarity tasks. scikit-bio: 10 correctness + 3 similarity. bedtools2 and DESeq2: 3 similarity tasks each, no accepted executable correctness tasks under the tested profiles. | Reusable C++/R build and test-parser support; broader Python source coverage. Unsupported profiles are not proof of unsuitable repositories. |
| Can free GLM be the author without per-task Codex fixes? | Sometimes at the instruction level: Tsallis retained its original GLM instruction without task-specific feedback. **No authored route has demonstrated unattended authoring plus acceptance.** Manual source review and control construction remain dependencies even when prose is unchanged. Historical extraction avoids author-model dependence altogether. | An unseen batch with no task-specific Codex edits, feedback, test writing or acceptance decisions; bounded free-GLM author/reviewer calls and frozen deterministic gates. Reusable setup is recorded separately; assisted cases cannot count as autonomous successes. |
| What does each approach cost per accepted task? | **Complete recurring costs remain unknown.** The cost ledger below gives attributable Daytona list-rate subtotals and separate solver bounds. GLM and allocated TRC/CoreWeave have zero incremental service charge under our arrangement. Missing lifetimes, review effort and credit/invoice data prevent production-price claims. | Complete phase-level attribution of generation, repairs, failed candidates, validation and storage, divided by accepted tasks. Report one-time engineering and solver evaluation separately, plus tokens, elapsed time and intervention rate. Zero admissions mean undefined cost per accepted task, not $0. |

**Scaling requirement:** the intended production workflow must run with the free GLM endpoint and reusable code, without Codex making task-specific repairs or admission decisions. Current assisted successes are evidence about feasibility, not proof that this requirement has been met. A high solver reward does not establish authoring quality, diversity or autonomous scalability.

## Which pipelines worked, which did not, and why

Here, **worked** means at least one independently accepted task under its declared reward contract. Exported files, successful builds, and passing reference solutions alone do not count. Functional correctness and patch similarity remain separate. Findings are interim until the bounded campaign is complete.

| Approach | Consolidated outcome | Scale-up judgment and main limitation |
| --- | --- | --- |
| Native PR-runtime | 6 accepted tasks across both Python repositories | Strongest current candidate for expansion after codifying reusable build/fixture profiles and automatic acceptance gates. No LLM author required. Historical source selection was curated and one instruction/oracle mismatch was rejected, so unattended discovery yield remains unmeasured. |
| Native commit-runtime | 1 accepted scikit-bio task; no accepted Biopython task | Promising historical extraction, weaker evidence than PR-runtime. Biopython exhausted ten selected inputs, with recent search inputs rejected by unchanged metadata filters; this is selection failure rather than universal repository failure. Collection failures and legacy nonportable images also reduced yield. Accepted case overlaps the PR2630 fix family. A further Stockholm export failed acceptance because a lowercase-only implementation earned full reward under a general keyword-forwarding instruction. |
| Native PR-diff | 12 accepted patch-similarity tasks across all four repositories | Scales across languages with no author model, but rewards similarity to a reference patch rather than executable correctness. Use only where that objective is intended; no C++/R functional-task success is inferred. |
| SWE-Smith | 5 accepted tasks: Biopython 2, scikit-bio 3 | Usable source-grounded mutations, but source-contract hallucinations and weak graders are material problems. Strong and Robbins constant-answer controls passed native graders and were rejected. New LCC needed task-specific feedback; Tsallis and Pielou were accepted with their original GLM instructions and no task-specific author feedback, but manually prepared acceptance controls. Biopython's candidate cap is exhausted at 2/3. Not ready for unattended expansion. |
| SWE-Flow | 2 accepted scikit-bio tasks, none in Biopython | Native instructions can work, but current successes are small aliases. Other outputs had malformed examples, incomplete specifications, timeouts or insufficient grader coverage. No evidence yet for reliable autonomous task authorship across repositories. |
| R2E-Gym | 1 accepted scikit-bio task, none in Biopython | Historical extraction works with explicit fixture and import-mode profiles, but new ASCII contrast (4 F2P / 316 P2P) produced an unadmitted GLM instruction that incorrectly extends metadata-mask behavior to boolean `lowercase=True`. Stockholm was rejected by native entity bounds. Existing accepted PR2633 lineage scored 0 on its single solve. Profile engineering, source-contract agreement and acceptance automation remain scale-up limits. |
| Scaler | 3 accepted synthetic DNA edit-distance instances | Programmatic generation can scale instances within this hand-prepared family without author calls. It does not demonstrate automatic invention of new scientific families. Native −1/+1 rewards still conflict with Marin's recorded 0/1 score bounds. |
| SWE-Gen and SWE-Next | Exports and runtime controls, but 0 independent admissions | GLM-authored instructions added unsupported precision or M-step requirements not covered by native tests; Biopython SWE-Next also hit native source/path filters. Passing reference/baseline checks alone did not establish instruction–grader agreement. |
| R2E | 0 accepted after 10 candidates per Python repository | Sixty author responses across both cohorts failed through syntax errors, malformed content or missing test definitions. Candidate caps exhausted. Unreliable with the tested free-GLM configuration. |
| SETA Seed2Synth, SETA Evol, DataArc, TMAX, Endless Terminals | 0 accepted | Design/build attempts produced heading-only specifications, missing real newlines, invalid Python, missing tests and request timeouts. Endless exhausted 10 candidates; other named cohorts retain bounded work. These experiments do not support unattended expansion under the tested configuration. |
| Native code-instruct | Inconclusive | Supported output archives were empty despite completed jobs; candidate counts/content/usage remain unknown. Consume the original allowance conservatively rather than report a scientific zero-yield result. |
| Native equivalence-tests | Not admitted | Native caller requires a Docker backend unavailable in the tested TRC caller profile; the reference implementation is also visible to the learner. A separate adapter would be required. |
| Native CVE-patches | Biopython export, 0 admitted | Legacy local-only bootstrap images and missing fresh acceptance evidence; overlaps another historical fix. No scikit-bio advisory input; native C++/R test-parser support absent. |
| Tasksmith, Codemidas, FrontierSmith | Blocked under free-GLM baseline | Native model/provider allowlists do not support the approved endpoint. A separately evaluated provider adaptation would be required. No paid fallback was used. |
| CLI-Gym | Blocked for selected profiles | Native constructor requires a specific tests layout not matched by the selected Biopython/scikit-bio profiles. This is a profile limitation, not proof the repositories cannot work. |
| TerminalWorld | Input/terms gate unresolved | Recording reuse terms and fixtures remain unresolved; no generated-task outcome. Planned Sec-bench is unimplemented and excluded from executable methods. |


## Which repositories worked, and why

| Repository / cohort | Accepted instances | What worked | What remains unproven or failed |
| --- | ---: | --- | --- |
| Biopython | 8: 5 correctness, 3 similarity | PR-runtime and SWE-Smith; patch similarity | No accepted Flow, native commit, SWE-Gen/Next or R2E-Gym output. Compiled bootstrap, source-path handling, instruction quality and grader coverage caused failures. |
| scikit-bio | 13: 10 correctness, 3 similarity | PR-runtime, native commit, SWE-Smith, SWE-Flow and R2E-Gym; patch similarity | Repository fixtures/build profiles needed explicit handling. Several examples share source fixes or narrow alpha-diversity functions, limiting diversity. |
| bedtools2 | 3 similarity only | PR-diff | No independently accepted executable C++ correctness task; pinned native runtime test parsers lack the selected make/shell profile. Python-only recipes are unsupported. |
| DESeq2 | 3 similarity only | PR-diff | No independently accepted executable R correctness task; pinned native parser/profile does not support the selected R/testthat route. Python-only recipes are unsupported. |
| Synthetic DNA edit-distance family | 3 algorithmic | Scaler | One constructed family, not an additional observed-data repository or three independent biological competencies. |


## Can the free GLM endpoint work without per-task Codex fixes?

GLM can produce usable authored instructions, but this experiment has **not demonstrated unattended GLM-only authoring plus acceptance**. The accepted set benefited from Codex orchestration, source inspection, repository/runtime adaptation, independent incorrect/alternative controls, and sometimes task-specific feedback. The new LCC normalization instruction became acceptable after GLM revised it using explicit source-review feedback about an invalid API example and an unsupported claim. Enspie retained its generated instruction without manual prose repair, but is a small alias/argument-forwarding task. These outcomes must not be labeled as a fully autonomous authoring pipeline.


The admitted Tsallis and Pielou tasks are positive examples of unchanged GLM authorship with no task-specific feedback. Their independently prepared controls and review were manual, so they do not yet meet the end-to-end automation requirement.

The latest unchanged R2E-Gym author instruction was a valid single paragraph, but source review found an unqualified metadata-mask claim incompatible with the boolean-True constructor case. The single call completed within the approved output ceiling; semantic acceptance still required independent review. Its roughly 5.9 minute job interval includes setup and archival and is one observation, not a production throughput estimate. See the [original output and review](https://github.com/Open-Athena/biotasks/blob/079b823ff699051511d8ff49082a89fd1a3ce394/experiments/21-repo2rlenv/continuation-20261018/skbio-r2egym-ascii-author-01/instruction-review.json). Some SWE-Flow outputs were stopped at document-format review without subsequent runtime acceptance checks; those outcomes alone do not establish scientific invalidity.

Treat absence of task-specific Codex edits or feedback as a separate acceptance criterion for scale-up. Preserve the current assisted results rather than relabel them. A qualifying new batch must use frozen repository profiles and code, the free GLM endpoint for any author/reviewer calls, native bounded repair loops, and deterministic automated acceptance checks. Invalid instructions, broken environments and inadequate graders should be rejected with reasons; manually repaired cases belong in a separate assisted cohort. Measure attempted inputs, accepted tasks, duplicate families, task-specific interventions, latency, all failed-candidate resource use, and native solver scores on an unseen input batch. This gate is not yet passed by any complete end-to-end authored route in this experiment.


### Where Codex is still in the loop

The relevant scale-up test is whether reusable code plus the free endpoint can produce **accepted tasks without task-specific Codex intervention**. An unchanged GLM instruction is a narrower success; it does not automate source review or establish that the grader measures the instruction.

| Route / family | Current accepted instances | Remaining manual dependence in this experiment | Autonomous scale-up established? |
| --- | ---: | --- | --- |
| Native PR-runtime / commit-runtime | 6 / 1 | Curated historical inputs, repository/build profiles, instruction review and acceptance controls | No; strongest candidates to automate, with no author-model requirement |
| PR-diff | 12 | Input selection and reward-contract review | No unattended discovery yield measured; similarity objective only |
| SWE-Smith | 5 | Source-contract review and task-specific incorrect/alternative controls; the new LCC also required feedback to GLM | No; unchanged Tsallis/Pielou authorship is useful but narrower evidence |
| SWE-Flow | 2 | Source review and acceptance controls; small alias tasks limit diversity | No |
| R2E-Gym | 1 | Fixture/import profiles and instruction–source agreement review; later ASCII author output was rejected | No |
| Scaler | 3 | Hand-prepared scientific family and grading contract | Repeatable instances within that family; automatic family creation not shown |
| Remaining authored routes | 0 | No accepted output from which to establish a production workflow | Not demonstrated; distinguish exhausted candidates, pending work and provider/profile blockers below |

Do not interpret this as a measured 0% autonomous yield: a held-out, frozen, unassisted end-to-end cohort has not yet been completed. Reusable engineering can be amortized; task-specific Codex decisions must be counted as interventions and kept outside claims of a free-GLM-only pipeline.


## Cost per task and budget ledger

The $2,000 campaign ceiling and current $1,323 estimates/reservations are an execution ledger, **not money known to have been spent**. The $908 historical component retains conservative holds, including earlier controller reservations; $415 is continuation reservations, leaving $677. Actual invoices and Daytona credit balance are unverified. Existing GLM and the user's allocated TRC/CoreWeave CPU have zero incremental charge under the approved access, but author latency, token throughput and development/review effort still matter.

The measured continuation samples in `compute-cost-samples.json` use exact retained sandbox start/stop timestamps and the [Daytona list rates](https://www.daytona.io/pricing) checked October 19: $0.0504/vCPU-hour, $0.0162/GiB RAM-hour and $0.000108/GiB storage-hour. Charging all 10 GiB conservatively gives $0.16668/hour for 2 vCPU / 4 GiB / 10 GiB. Credits and the advertised free storage are not deducted. The four sample subtotals are **partial generation/independent-validation compute costs**, including listed failed/rejected runs and capture retries, but excluding first-pass allocations, blind solves, Marin integration, storage outside those lifetimes and Codex/human labor. They are not full per-task production prices.

| Approach | Newly accepted tasks in measured continuation sample | Recorded sandbox hours | Partial compute subtotal / accepted task |
| --- | ---: | ---: | ---: |
| Native PR-runtime | 5 | 0.3834 | $0.0128 |
| SWE-Smith | 1 | 0.4769 | $0.0795 |
| SWE-Flow | 1 | 0.1790 | $0.0298 |
| Native commit-runtime | 1 | 0.1227 | $0.0205 |

A [deduplicated historical lifecycle inventory](https://github.com/Open-Athena/biotasks/blob/f0f86b04d8e7fda2f8e49f970a173a32d454f013/experiments/21-repo2rlenv/continuation-20261018/worker-cost-evidence-inventory.json) now contains 104 terminated Daytona sandboxes with complete timestamps, totaling 14.00 recorded sandbox-hours. Route/phase attribution and provider-direct solver lifetimes remain to be reconciled; this is not a complete billing export.

The [partial route-cost reconciliation](https://github.com/Open-Athena/biotasks/blob/f0f86b04d8e7fda2f8e49f970a173a32d454f013/experiments/21-repo2rlenv/continuation-20261018/route-compute-attribution.json) attributes 68 of those 104 workers to 14 routes using exact sandbox IDs and explicit generation, contrast, export and additional-stage provenance; 36 remain unassigned. It includes failures within attributed runs and preserves null per-task costs for routes with no admissions. These expanded historical subtotals still omit some generation/validation lifetimes and must not be read as production prices.

For the final comparison, report **generation and acceptance cost per accepted task = all attributable candidate generation, repair and validation costs, including rejected candidates, divided by independently accepted tasks**. Report blind solver evaluation and Marin conversion/validation separately, then an all-in subtotal where coverage is complete. Also report author tokens, elapsed time and task-specific interventions per accepted task: a free endpoint removes its monetary charge, not its capacity cost. With zero admissions, report spend and zero yield; a finite cost per accepted task is undefined. Unrecorded labor or missing provider lifetimes remain explicitly unknown rather than zero.

### Per-approach cost ledger (partial evidence)

**Full cost per accepted task is not yet established for any route.** The table exposes what is attributable today rather than treating missing records as free execution. Dollar amounts are Daytona list-rate equivalents, not verified charges. The denominator is the current 30-task admission ledger; the retained 104-worker cost inventory includes the latest Pielou validation and Smith continuation lifetimes but still omits some provider-direct solver lifetimes; the numerator covers only attributed lifetimes, so these ratios must not be used as production quotes or to rank approaches. The smaller continuation-only samples above use different coverage and denominators.

| Approach | Accepted tasks | Attributed sandbox compute subtotal | Partial subtotal / accepted task |
| --- | ---: | ---: | ---: |
| `code_instruct/native` | 0 | Not attributed | Not estimable: 0 accepted |
| `commit_runtime/native` | 1 | $0.0609 | $0.0609 (incomplete) |
| `commit_runtime/r2e_gym` | 1 | $0.0540 | $0.0540 (incomplete) |
| `cve_patches/native` | 0 | $0.0036 | Not estimable: 0 accepted |
| `env_repair/cli_gym` | 0 | Not attributed | Not estimable: 0 accepted |
| `equivalence_tests/native` | 0 | Not attributed | Not estimable: 0 accepted |
| `equivalence_tests/r2e` | 0 | $0.5675 | Not estimable: 0 accepted |
| `optimization_synth/frontiersmith` | 0 | Not attributed | Not estimable: 0 accepted |
| `pr_diff/native` | 12 | Not attributed | Not established |
| `pr_runtime/native` | 6 | $0.0779 | $0.0130 (incomplete) |
| `pr_runtime/swe_next` | 0 | $0.0445 | Not estimable: 0 accepted |
| `pr_to_env/swe_gen` | 0 | $0.0436 | Not estimable: 0 accepted |
| `reasoning_synth/scaler` | 3 | $0.0058 | $0.0019 (incomplete) |
| `repo_mutate/swe_smith` | 5 | $0.2511 | $0.0502 (incomplete) |
| `repo_reconstruct/codemidas` | 0 | Not attributed | Not estimable: 0 accepted |
| `repo_reconstruct/swe_flow` | 2 | $0.1328 | $0.0664 (incomplete) |
| `task_evolve/seta_evol` | 0 | $0.0560 | Not estimable: 0 accepted |
| `tasksmith/tasksmith` | 0 | Not attributed | Not estimable: 0 accepted |
| `terminal_reconstruct/terminalworld` | 0 | Not attributed | Not estimable: 0 accepted |
| `terminal_synth/dataarc` | 0 | $0.1501 | Not estimable: 0 accepted |
| `terminal_synth/endless_terminals` | 0 | $0.2032 | Not estimable: 0 accepted |
| `terminal_synth/seta_seed2synth` | 0 | Not attributed | Not estimable: 0 accepted |
| `terminal_synth/tmax` | 0 | $0.2023 | Not estimable: 0 accepted |

For a scalable free-GLM workflow, report three separate quantities: recurring cost per automatically accepted task (including rejected candidates and bounded repairs), one-time engineering/profile setup, and blind-solver evaluation cost. Task-specific Codex repair is an intervention and disqualifies a case from the autonomous cohort; it cannot be hidden as free authoring. The remaining accounting work must attach complete model usage and execution lifetimes to those phases, or explicitly mark unrecoverable gaps.

Full per-accepted-task costs for these routes remain unestablished; the small direct-compute subtotals do not price the assistance needed to reach acceptance. PR-diff, R2E-Gym and Scaler require equivalent full lifecycle attribution before quoting a measured end-to-end cost per accepted task. For routes with zero admissions, cost per accepted task is not estimable from this run, rather than $0. Unsupported/unexecuted routes have no runtime cost estimate. The required scalable metric is `(generation + all rejected candidates + automated validation + storage + required review) / independently accepted tasks`, reporting solver-evaluation cost and one-time engineering separately. Free-model token/latency usage should accompany that metric.



Evidence basis: [task ledger](consolidated-ledger.json), [candidate ledger](target-tracker.json), [partial route cost attribution](route-compute-attribution.json), [measured continuation costs](compute-cost-samples.json), [solver compute upper bounds](solver-compute-upper-bounds.json), [budget reservations](budget.json), and the per-run source and acceptance links above. These are bounded experimental observations, not production yield or price guarantees.
