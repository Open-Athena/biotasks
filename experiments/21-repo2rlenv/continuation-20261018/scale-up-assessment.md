# Scale-up assessment: current evidence, not final campaign conclusions

The most promising current route for a scalable computational-biology software corpus is native PR-runtime extraction from supported Python repositories. It reuses historical changes and tests without requiring an LLM author. Native commit-runtime extraction is also promising but has only one newly admitted example. These are biological-software maintenance tasks; neither result establishes broad biological-analysis reasoning or production yield on unseen repositories.

GLM can produce usable authored instructions, but this experiment has **not demonstrated unattended GLM-only authoring plus acceptance**. The accepted set benefited from Codex orchestration, source inspection, repository/runtime adaptation, independent incorrect/alternative controls, and sometimes task-specific feedback. The new LCC normalization instruction became acceptable after GLM revised it using explicit source-review feedback about an invalid API example and an unsupported claim. Enspie retained its generated instruction without manual prose repair, but is a small alias/argument-forwarding task. These outcomes must not be labeled as a fully autonomous authoring pipeline.

## Which approaches worked, and why others did not

| Approach | Consolidated outcome | Scale-up judgment and main limitation |
| --- | --- | --- |
| Native PR-runtime | 6 accepted tasks across both Python repositories | Strongest current candidate for expansion after codifying reusable build/fixture profiles and automatic acceptance gates. No LLM author required. Historical source selection was curated and one instruction/oracle mismatch was rejected, so unattended discovery yield remains unmeasured. |
| Native commit-runtime | 1 accepted scikit-bio task; no accepted Biopython task | Promising historical extraction, weaker evidence than PR-runtime. Source filters, collection failures and legacy nonportable images reduced yield. Accepted case overlaps the PR2630 fix family. |
| Native PR-diff | 12 accepted patch-similarity tasks across all four repositories | Scales across languages with no author model, but rewards similarity to a reference patch rather than executable correctness. Use only where that objective is intended; no C++/R functional-task success is inferred. |
| SWE-Smith | 3 accepted tasks: Biopython 2, scikit-bio 1 | Usable source-grounded mutations, but source-contract hallucinations and weak graders are material problems. Strong and Robbins constant-answer controls passed native graders and were rejected. New LCC needed task-specific feedback. Biopython's candidate cap is exhausted at 2/3. Not ready for unattended expansion. |
| SWE-Flow | 2 accepted scikit-bio tasks, none in Biopython | Native instructions can work, but current successes are small aliases. Other outputs had malformed examples, incomplete specifications, timeouts or insufficient grader coverage. No evidence yet for reliable autonomous task authorship across repositories. |
| R2E-Gym | 1 accepted scikit-bio task, none in Biopython | Historical extraction is viable after explicit private-fixture adaptation. Biopython's bounded pool produced snapshot-path/bootstrap failures. The accepted example shares the PR2633 lineage and scored 0 on its single solve. |
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

## Which repositories worked

| Repository / cohort | Accepted instances | What worked | What remains unproven or failed |
| --- | ---: | --- | --- |
| Biopython | 8: 5 correctness, 3 similarity | PR-runtime and SWE-Smith; patch similarity | No accepted Flow, native commit, SWE-Gen/Next or R2E-Gym output. Compiled bootstrap, source-path handling, instruction quality and grader coverage caused failures. |
| scikit-bio | 11: 8 correctness, 3 similarity | PR-runtime, native commit, SWE-Smith, SWE-Flow and R2E-Gym; patch similarity | Repository fixtures/build profiles needed explicit handling. Several examples share source fixes or narrow alpha-diversity functions, limiting diversity. |
| bedtools2 | 3 similarity only | PR-diff | No independently accepted executable C++ correctness task; pinned native runtime test parsers lack the selected make/shell profile. Python-only recipes are unsupported. |
| DESeq2 | 3 similarity only | PR-diff | No independently accepted executable R correctness task; pinned native parser/profile does not support the selected R/testthat route. Python-only recipes are unsupported. |
| Synthetic DNA edit-distance family | 3 algorithmic | Scaler | One constructed family, not an additional observed-data repository or three independent biological competencies. |

## Requirement for scaling without per-task Codex fixes

Treat absence of task-specific Codex edits or feedback as a separate acceptance criterion for scale-up. Preserve the current assisted results rather than relabel them. A qualifying new batch must use frozen repository profiles and code, the free GLM endpoint for any author/reviewer calls, native bounded repair loops, and deterministic automated acceptance checks. Invalid instructions, broken environments and inadequate graders should be rejected with reasons; manually repaired cases belong in a separate assisted cohort. Measure attempted inputs, accepted tasks, duplicate families, task-specific interventions, latency, all failed-candidate resource use, and native solver scores on an unseen input batch. This gate is not yet passed by any complete end-to-end authored route in this experiment.

## Cost interpretation

The $2,000 campaign ceiling and current $1,163 estimates/reservations are an execution ledger, **not money known to have been spent**. The $908 historical component retains conservative holds, including earlier controller reservations; $255 is continuation reservations, leaving $837. Actual invoices and Daytona credit balance are unverified. Existing GLM and the user's allocated TRC/CoreWeave CPU have zero incremental charge under the approved access, but author latency, token throughput and development/review effort still matter.

The measured continuation samples in `compute-cost-samples.json` use exact retained sandbox start/stop timestamps and the [Daytona list rates](https://www.daytona.io/pricing) checked October 19: $0.0504/vCPU-hour, $0.0162/GiB RAM-hour and $0.000108/GiB storage-hour. Charging all 10 GiB conservatively gives $0.16668/hour for 2 vCPU / 4 GiB / 10 GiB. Credits and the advertised free storage are not deducted. The four sample subtotals are **partial generation/independent-validation compute costs**, including listed failed/rejected runs and capture retries, but excluding first-pass allocations, blind solves, Marin integration, storage outside those lifetimes and Codex/human labor. They are not full per-task production prices.

| Approach | Newly accepted tasks in measured continuation sample | Recorded sandbox hours | Partial compute subtotal / accepted task |
| --- | ---: | ---: | ---: |
| Native PR-runtime | 5 | 0.3834 | $0.0128 |
| SWE-Smith | 1 | 0.4769 | $0.0795 |
| SWE-Flow | 1 | 0.1790 | $0.0298 |
| Native commit-runtime | 1 | 0.1227 | $0.0205 |

Full per-accepted-task costs for these routes remain unestablished; the small direct-compute subtotals do not price the assistance needed to reach acceptance. PR-diff, R2E-Gym and Scaler require equivalent full lifecycle attribution before quoting a measured end-to-end cost per accepted task. For routes with zero admissions, cost per accepted task is not estimable from this run, rather than $0. Unsupported/unexecuted routes have no runtime cost estimate. The required scalable metric is `(generation + all rejected candidates + automated validation + storage + required review) / independently accepted tasks`, reporting solver-evaluation cost and one-time engineering separately. Free-model token/latency usage should accompany that metric.

Evidence basis: [combined task/candidate ledger](consolidated-ledger.json), [recorded first-pass route findings](../applicability.csv), [native PR review](biopython-pr-runtime-native-01/independent-static-review.json), [original LCC instruction review](biopython-smith-author-cw-01/independent-review.json), [LCC GLM revision review](biopython-smith-review-cw-01/independent-review.json), [Flow instruction review](skbio-flow-author-cw-01/independent-review.json), [Biopython Flow failures](biopython-flow-author-cw-01/independent-review.json), [sandbox-lifetime cost calculations](compute-cost-samples.json), and [conservative budget ledger](budget.json). Assessments of scalability are inferences from these bounded runs, not measured production guarantees.
