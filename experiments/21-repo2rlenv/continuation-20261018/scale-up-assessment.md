# Scale-up assessment under the automatic-pipeline evaluation rule

## Living results and decisions — 2026-10-19 20:17 UTC

**Execution is authorized to resume under the automatic-pipeline rule below: no task-specific Codex fixes or feedback; final manual assessment is allowed.** The experiment remains open. Consolidating the first pass and continuation: **30 legacy task instances accepted/scored across mixed automatic and assisted profiles, with 8 legacy units meeting the three-task target. Automatic-output success counts are being reconciled under the clarified rule.** These are 18 correctness/algorithmic and 12 patch-similarity tasks; related source families are not independent biological competencies. The complete ledger is below, including failures, unsupported cells and pending work. These are interim results; legacy totals must not be read as automatic-only yield.

**Current scale-up judgment:** native PR-runtime extraction is the strongest candidate for a computational-biology software corpus because it reuses real historical changes/tests without needing an LLM author. Native commit-runtime is promising with less evidence; its upstream default uses an LLM statement rewrite, whereas our accepted replay disabled synthesis. GLM-authored routes have useful unchanged outputs; the comparison must distinguish task fixes/feedback from allowed final manual assessment. Automatic-only counts still require provenance reconciliation.

## Answers for a scale-up decision

**Recommendation: scale historical extraction first; treat GLM-authored routes as experimental until acceptance is automated.** These are qualitative judgments from this small, curated sample, not measured production yields. The detailed route/repository tables and task ledger below include both successful and unsuccessful outcomes and their causes.

| Question | Current answer | What would change the conclusion? |
| --- | --- | --- |
| Which pipelines should we scale? | Native PR-runtime has the strongest correctness evidence (6 accepted); native commit-runtime is promising (1 accepted). PR-diff works across languages (12 accepted) for similarity rewards only. Smith (5), Flow (2), R2E-Gym (1) and Scaler (3 within one family) have useful examples with material limitations. | A held-out batch using frozen reusable profiles and acceptance gates, with rejected candidates and duplicate source families included in the accounting. |
| Which repositories work? | Biopython: 5 correctness + 3 similarity tasks. scikit-bio: 10 correctness + 3 similarity. bedtools2 and DESeq2: 3 similarity tasks each, no accepted executable correctness tasks under the tested profiles. | Reusable C++/R build and test-parser support; broader Python source coverage. Unsupported profiles are not proof of unsuitable repositories. |
| Can free GLM be the author without per-task Codex fixes? | Sometimes at the instruction level: Tsallis retained its original GLM instruction without task-specific feedback. Some unchanged GLM outputs pass final assessment. Manual end assessment is allowed; task-specific fixes/feedback disqualify a recovered output from the automatic cohort. Native PR-runtime reuses historical issue/PR text rather than an LLM author per task; repository bootstrap still needs an explicit profile or a cached model-built environment. | Frozen pipeline/configuration, no task-specific Codex changes or feedback, and explicit post-run assessment of unchanged outputs. Record generic setup separately and retain failures. |
| What does each approach cost per accepted task? | **Complete recurring costs remain unknown.** The time ledger below gives partial recorded sandbox-minutes per accepted task and separate solver bounds. GLM and allocated TRC/CoreWeave have zero incremental service charge under our arrangement. Missing lifetimes, review effort and credit/invoice data prevent production-price claims. | Complete phase-level attribution of generation, repairs, failed candidates, validation and storage, divided by accepted tasks. Report one-time engineering and solver evaluation separately, plus tokens, elapsed time and intervention rate. Zero admissions mean undefined cost per accepted task, not $0. |

**Comparison requirement:** generation runs with the free endpoint and a fixed declared pipeline configuration. Codex may assess the final outputs, but may not repair candidates or feed task-specific fixes back to the author. A high solver reward does not establish quality or diversity.

## How the PR-related pipelines differ

**Yes: mining historical PRs with existing regression tests is the most promising first expansion from this sample.** The narrower recommendation is native `pr_runtime`, not every pipeline that takes a PR. It reuses an existing problem, fix and tests, so it asks the model to invent less. This is a prioritization judgment from six accepted cases, not proof of unattended throughput or broad biological reasoning.

| Approach / documentation | Starting point and generated task | Author-model dependence | Our result |
| --- | --- | --- | --- |
| [pr_diff](https://huggingface.github.io/Repo2RLEnv/pipelines/pr_diff/) | PR description plus pre-change repository; compare the submitted patch to the merged patch | No author model; optional judge disabled here | 12 similarity tasks; does not prove functional correctness |
| [pr_runtime](https://huggingface.github.io/Repo2RLEnv/pipelines/pr_runtime/) | PR with source and regression-test changes; run the same hidden tests before/after the fix | No per-task author; upstream bootstrap can use an LLM and cache the environment | 6 correctness tasks; Codex supplied runtime profiles and additional acceptance checks |
| [SWE-gen / pr_to_env](https://huggingface.github.io/Repo2RLEnv/pipelines/pr_to_env/) | Explicit PR URLs; reverse implementation edits from the healthy PR head, retain its tests | Model judges substantiality and writes the instruction | 0 accepted; generated instructions and grader contract did not agree |
| [SWE-Next](https://huggingface.github.io/Repo2RLEnv/pipelines/swe_next/) | Mine merged PRs; compare merge commit to its first parent with post-change tests at original paths | Model writes an issue from the measured contrast and private diff | 0 accepted; instruction/coverage and source-profile failures |
| [Tasksmith](https://huggingface.github.io/Repo2RLEnv/pipelines/tasksmith/) | Agent investigates a PR, constructs its environment and private verifier, then reviews/repairs | Agentic authoring throughout, more engineering freedom than fixed mining | Blocked by the tested native provider/model support; no free-GLM success established |
| [commit_runtime](https://huggingface.github.io/Repo2RLEnv/pipelines/commit_runtime/) | Related route: mine commits rather than PRs; hidden regression tests and historical reference | Upstream default rewrites the statement with an LLM; our accepted replay explicitly disabled synthesis | 1 accepted; same source family as a PR-runtime case |
| [R2E-Gym](https://huggingface.github.io/Repo2RLEnv/pipelines/r2e_gym/) | Related route: mine first-parent commits with bounded edits and privately packaged tests/fixtures | One issue-author call after a successful execution contrast | 1 accepted with fixture-profile adaptation; not native PR-runtime |

SWE-Smith is a different source of tasks: it plants synthetic defects in a working repository rather than mining a historical PR. SWE-Flow removes functionality and asks for reconstruction. Neither should be counted as additional historical PR-mining evidence. Pipeline names and CLI recipe names differ; the links above identify the exact implementations tested at the pinned experiment revision, while the documentation site can evolve.

## Which pipelines worked, which did not, and why

Here, **worked** means at least one independently accepted task under its declared reward contract. Exported files, successful builds, and passing reference solutions alone do not count. Functional correctness and patch similarity remain separate. Findings are interim until the bounded campaign is complete.

| Approach | Consolidated outcome | Scale-up judgment and main limitation |
| --- | --- | --- |
| [Native PR-runtime](https://huggingface.github.io/Repo2RLEnv/pipelines/pr_runtime/) | 6 accepted tasks across both Python repositories | Strongest current candidate for expansion after codifying reusable build/fixture profiles and automatic acceptance gates. No LLM author required. Historical source selection was curated and one instruction/oracle mismatch was rejected, so unattended discovery yield remains unmeasured. |
| [Native commit-runtime](https://huggingface.github.io/Repo2RLEnv/pipelines/commit_runtime/) | 1 accepted scikit-bio task; no accepted Biopython task | Promising historical extraction, weaker evidence than PR-runtime. Biopython exhausted ten selected inputs, with recent search inputs rejected by unchanged metadata filters; this is selection failure rather than universal repository failure. Collection failures and legacy nonportable images also reduced yield. Accepted replay disabled instruction synthesis; upstream default uses an LLM rewrite. It overlaps the PR2630 fix family. A further Stockholm export failed acceptance because a lowercase-only implementation earned full reward under a general keyword-forwarding instruction. |
| [Native PR-diff](https://huggingface.github.io/Repo2RLEnv/pipelines/pr_diff/) | 12 accepted patch-similarity tasks across all four repositories | Scales across languages with no author model, but rewards similarity to a reference patch rather than executable correctness. Use only where that objective is intended; no C++/R functional-task success is inferred. |
| [SWE-Smith](https://huggingface.github.io/Repo2RLEnv/pipelines/repo_mutate/) | 5 accepted tasks: Biopython 2, scikit-bio 3 | Usable source-grounded mutations, but source-contract hallucinations and weak graders are material problems. Strong and Robbins constant-answer controls passed native graders and were rejected. New LCC needed task-specific feedback; Tsallis and Pielou were accepted with their original GLM instructions and no task-specific author feedback, but manually prepared acceptance controls. Biopython's candidate cap is exhausted at 2/3. Not ready for unattended expansion. |
| [SWE-Flow](https://huggingface.github.io/Repo2RLEnv/pipelines/repo_reconstruct/) | 2 accepted scikit-bio tasks, none in Biopython | Native instructions can work, but current successes are small aliases. Other outputs had malformed examples, incomplete specifications, timeouts or insufficient grader coverage. No evidence yet for reliable autonomous task authorship across repositories. |
| [R2E-Gym](https://huggingface.github.io/Repo2RLEnv/pipelines/r2e_gym/) | 1 accepted scikit-bio task, none in Biopython | Historical extraction works with explicit fixture and import-mode profiles, but new ASCII contrast (4 F2P / 316 P2P) produced an unadmitted GLM instruction that incorrectly extends metadata-mask behavior to boolean `lowercase=True`. Stockholm was rejected by native entity bounds. Existing accepted PR2633 lineage scored 0 on its single solve. Profile engineering, source-contract agreement and acceptance automation remain scale-up limits. |
| [Scaler](https://huggingface.github.io/Repo2RLEnv/pipelines/scaler/) | 3 accepted synthetic DNA edit-distance instances | Programmatic generation can scale instances within this hand-prepared family without author calls. It does not demonstrate automatic invention of new scientific families. Native −1/+1 rewards still conflict with Marin's recorded 0/1 score bounds. |
| [SWE-Gen](https://huggingface.github.io/Repo2RLEnv/pipelines/pr_to_env/) and [SWE-Next](https://huggingface.github.io/Repo2RLEnv/pipelines/swe_next/) | Exports and runtime controls, but 0 independent admissions | GLM-authored instructions added unsupported precision or M-step requirements not covered by native tests; Biopython SWE-Next also hit native source/path filters. Passing reference/baseline checks alone did not establish instruction–grader agreement. |
| [R2E](https://huggingface.github.io/Repo2RLEnv/pipelines/r2e/) | 0 accepted after 10 candidates per Python repository | Sixty author responses across both cohorts failed through syntax errors, malformed content or missing test definitions. Candidate caps exhausted. Unreliable with the tested free-GLM configuration. |
| [SETA Seed2Synth](https://huggingface.github.io/Repo2RLEnv/pipelines/terminal_synth/), [SETA Evol](https://huggingface.github.io/Repo2RLEnv/pipelines/task_evolve/), [DataArc](https://huggingface.github.io/Repo2RLEnv/pipelines/dataarc/), [TMAX](https://huggingface.github.io/Repo2RLEnv/pipelines/tmax/), [Endless Terminals](https://huggingface.github.io/Repo2RLEnv/pipelines/endless_terminals/) | 0 accepted | Design/build attempts produced heading-only specifications, missing real newlines, invalid Python, missing tests and request timeouts. Endless exhausted 10 candidates; other named cohorts retain bounded work. These experiments do not support unattended expansion under the tested configuration. |
| [Native code-instruct](https://huggingface.github.io/Repo2RLEnv/pipelines/code_instruct/) | Inconclusive | Supported output archives were empty despite completed jobs; candidate counts/content/usage remain unknown. Consume the original allowance conservatively rather than report a scientific zero-yield result. |
| [Native equivalence-tests](https://huggingface.github.io/Repo2RLEnv/pipelines/equivalence_tests/) | Not admitted | Native caller requires a Docker backend unavailable in the tested TRC caller profile; the reference implementation is also visible to the learner. A separate adapter would be required. |
| [Native CVE-patches](https://huggingface.github.io/Repo2RLEnv/pipelines/cve_patches/) | Biopython export, 0 admitted | Legacy local-only bootstrap images and missing fresh acceptance evidence; overlaps another historical fix. No scikit-bio advisory input; native C++/R test-parser support absent. |
| [Tasksmith](https://huggingface.github.io/Repo2RLEnv/pipelines/tasksmith/), [Codemidas](https://huggingface.github.io/Repo2RLEnv/pipelines/codemidas/), [FrontierSmith](https://huggingface.github.io/Repo2RLEnv/pipelines/frontiersmith/) | Blocked under free-GLM baseline | Native model/provider allowlists do not support the approved endpoint. A separately evaluated provider adaptation would be required. No paid fallback was used. |
| [CLI-Gym](https://huggingface.github.io/Repo2RLEnv/pipelines/env_repair/) | Blocked for selected profiles | Native constructor requires a specific tests layout not matched by the selected Biopython/scikit-bio profiles. This is a profile limitation, not proof the repositories cannot work. |
| [TerminalWorld](https://huggingface.github.io/Repo2RLEnv/pipelines/terminalworld/) | Input/terms gate unresolved | Recording reuse terms and fixtures remain unresolved; no generated-task outcome. Planned Sec-bench is unimplemented and excluded from executable methods. |


## Which repositories worked, and why

| Repository / cohort | Accepted instances | What worked | What remains unproven or failed |
| --- | ---: | --- | --- |
| Biopython | 8: 5 correctness, 3 similarity | PR-runtime and SWE-Smith; patch similarity | No accepted Flow, native commit, SWE-Gen/Next or R2E-Gym output. Compiled bootstrap, source-path handling, instruction quality and grader coverage caused failures. |
| scikit-bio | 13: 10 correctness, 3 similarity | PR-runtime, native commit, SWE-Smith, SWE-Flow and R2E-Gym; patch similarity | Repository fixtures/build profiles needed explicit handling. Several examples share source fixes or narrow alpha-diversity functions, limiting diversity. |
| bedtools2 | 3 similarity only | PR-diff | No independently accepted executable C++ correctness task; pinned native runtime test parsers lack the selected make/shell profile. Python-only recipes are unsupported. |
| DESeq2 | 3 similarity only | PR-diff | No independently accepted executable R correctness task; pinned native parser/profile does not support the selected R/testthat route. Python-only recipes are unsupported. |
| Synthetic DNA edit-distance family | 3 algorithmic | Scaler | One constructed family, not an additional observed-data repository or three independent biological competencies. |


## Automatic-pipeline comparison: generation versus final assessment

**The goal is to assess the automatic pipeline. Manual assessment of its final outputs is allowed; manual fixing is not.** A successful result is an unchanged output of a frozen declared pipeline configuration that passes the post-run assessment. Codex reading the result, judging quality, or writing separate diagnostic controls afterward does not by itself disqualify it. My earlier claim that manual assessment prevented an automatic-pipeline success was too strict and is superseded by this rule.

The pipeline may use its own bounded automatic repair loops. Codex must not edit a candidate’s instruction, learner source, reference solution, tests, verifier, fixtures, dependencies or runtime assets after a failure, nor supply task-specific author feedback. A task that needs such intervention is an automatic-pipeline failure; any historical assisted recovery remains separate evidence. Generic endpoint authentication, fixed resource limits, capture and cleanup are execution plumbing, recorded before a run. They must not alter the task’s intended content or behavior. Freeze repository profiles and input selection before the batch; a task-specific workaround discovered during the batch is not silently added to its successful outputs.

### How to read the existing 30-task ledger

The 30 previously accepted/scored tasks combine automatic outputs with assisted runtime recoveries and one known task-specific author-feedback revision. **They are not a total of 30 proven automatic-pipeline successes.** They remain preserved for provenance and solver evidence. We must assess unchanged original outputs separately; unknown provenance stays unresolved rather than being treated as either success or failure. Original target/candidate allowances are retained, including failed and uncertain requests.

| Existing evidence | Implication for the automatic comparison |
| --- | --- |
| Esty and observed-features acceptance receipts explicitly retain the emitted instruction/source/reference/grader bundle unchanged | These are evidence of unchanged pipeline outputs with final manual assessment. Review alone is allowed. Full run configuration/feedback lineage still needs to accompany the primary accounting. |
| Tsallis, Pielou and Enspie retained original GLM instructions without task-specific author feedback | Positive authorship evidence. Check the complete exported/runtime bundle before claiming unchanged end-to-end output; unchanged prose alone does not establish that. |
| New LCC instruction was revised by GLM using task-specific feedback written by Codex | Excluded from primary automatic-output success; retain the original failure and label the revised task assisted. |
| First LCC, R2E-Gym and portable historical profiles required explicit build/fixture/runtime work | Report the original pipeline outcome and adapted-profile evidence separately. Do not use a rescued runtime as proof that the original configuration worked. |
| PR-diff exports had declared offline/tooling adaptations; Scaler used a hand-prepared family | Report automatic generation under the exact declared inputs/profile, and identify the adaptation or family preparation. Do not infer unchanged stock-runtime success or automatic scientific-family creation. |

The task-table provenance letters remain descriptive: **D** native similarity export; **H** historical task with portable/runtime adaptation; **U** explicitly unchanged emitted bundle; **G** unchanged GLM instruction; **F** task-specific author-feedback revision; **A** explicit runtime/build/fixture adaptation; **S** instances from a hand-prepared Scaler family. Review/control preparation is recorded independently of these task changes.

### What “validated” means here

| Stage | Who/what performs it | Meaning for this comparison |
| --- | --- | --- |
| Native generation checks | The pinned pipeline builds/runs its own tests or before/after contrasts | Automatic pipeline evidence; successful export alone does not guarantee task quality |
| Final instruction/source assessment | Codex reads the completed unchanged output and its pinned source/tests | Allowed final assessment; may accept or reject, without fixing or giving feedback to generation |
| Additional diagnostic controls | Codex may prepare separate correct/incorrect/partial submissions and run the unchanged grader | Assessment evidence, not a task repair; record which checks were performed and their finite coverage |
| Blind GLM solve | Existing free GLM, fixed solver limits, deterministic original reward | Model performance on that exact task; no repair of the task or solver attempt |
| Marin checks | Recorded schema checks or explicit native/Marin runtime pairs | Integration evidence kept separate from original automatic task-generation yield |
| Hash/readback/cleanup checks | Programmatic accounting | Preservation and lifecycle evidence, separate from scientific quality |

“Independently accepted” in earlier records means evaluated separately from generation with Codex involvement; it does not mean an external human audit or exhaustive scientific correctness. The numerical reward is computed by code. Final manual assessment is permitted under the current experiment rule. The deferred end-to-end grader-integrity diagnostic remains unexecuted.


## Time per task, cost and budget ledger


**Time is clearer than dollars under our free allocations, but two clocks must stay separate.** Wall time measures latency from candidate start to decision. Sandbox-minutes sum active sandbox lifetimes and measure a resource cost; four sandboxes for ten minutes consume forty sandbox-minutes. Neither measures Codex/human effort.

For a fully observed cohort, report `total generation + bounded repairs + acceptance wall time / candidates attempted`, and the same numerator divided by accepted tasks. Include failed candidates; with zero admissions the per-accepted value is undefined. Keep one-time repository setup and blind-solver evaluation separate. Complete end-to-end candidate/acceptance timings are **not yet reconstructed** for this campaign; replacing dollars with minutes cannot fill those missing phases.

**Direct matched example:** the Biopython native PR-runtime batch considered/emitted PR5317, PR5310 and PR5308 in one recorded 84.703-second sandbox lifetime. Two of these sources were later accepted (5317/5308). This is **28.2 sandbox-seconds per generated candidate** or **42.4 sandbox-seconds per ultimately accepted candidate for this generation stage only**. It excludes subsequent acceptance controls, profile engineering and solver evaluation, and is not a complete time-to-accepted-task estimate. The rejected PR5310 stays in the denominator. [Exact cohort/timestamps](https://github.com/Open-Athena/biotasks/blob/7f8e289/experiments/21-repo2rlenv/continuation-20261018/biopython-pr-runtime-native-01/controller-small-summary.json).

**Author latency example:** one R2E-Gym ASCII instruction job took **354.878 seconds (5.9 minutes)** including setup and archival, made one completed GLM call, and was rejected on source-contract review. Its per-attempt job time is known; time per accepted task is undefined because it produced zero admissions. This observation does not include the earlier historical contrast or manual review. [Performance receipt](https://github.com/Open-Athena/biotasks/blob/079b823ff699051511d8ff49082a89fd1a3ce394/experiments/21-repo2rlenv/continuation-20261018/skbio-r2egym-ascii-author-01/performance-summary.json).

### Partial resource-time ledger by approach

Legacy mixed-provenance cost/time evidence, not automatic-only throughput. Converted directly from the existing exact-lifecycle attribution: 68 attributed workers out of 104 recorded terminated workers; 36 remain unassigned. These are **incomplete recorded sandbox-minutes divided by the full current admission count**, not isolated runtime, wall latency or fair throughput rankings. Missing model/acceptance phases and manual effort are not zero. Rows with no attributed lifetimes remain unknown. The smaller earlier selected-cohort dollar samples use different coverage and are superseded here as the headline comparison; their immutable receipts remain linked evidence.

| Approach | Accepted | Recorded sandbox-minutes | Partial sandbox-minutes / accepted |
| --- | ---: | ---: | ---: |
| `code_instruct/native` | 0 | Unknown | Undefined: 0 accepted |
| `commit_runtime/native` | 1 | 21.94 | 21.94 (incomplete) |
| `commit_runtime/r2e_gym` | 1 | 19.45 | 19.45 (incomplete) |
| `cve_patches/native` | 0 | 1.30 | Undefined: 0 accepted |
| `env_repair/cli_gym` | 0 | Unknown | Undefined: 0 accepted |
| `equivalence_tests/native` | 0 | Unknown | Undefined: 0 accepted |
| `equivalence_tests/r2e` | 0 | 204.27 | Undefined: 0 accepted |
| `optimization_synth/frontiersmith` | 0 | Unknown | Undefined: 0 accepted |
| `pr_diff/native` | 12 | Unknown | Unknown |
| `pr_runtime/native` | 6 | 28.06 | 4.68 (incomplete) |
| `pr_runtime/swe_next` | 0 | 16.02 | Undefined: 0 accepted |
| `pr_to_env/swe_gen` | 0 | 15.71 | Undefined: 0 accepted |
| `reasoning_synth/scaler` | 3 | 2.09 | 0.70 (incomplete) |
| `repo_mutate/swe_smith` | 5 | 90.38 | 18.08 (incomplete) |
| `repo_reconstruct/codemidas` | 0 | Unknown | Undefined: 0 accepted |
| `repo_reconstruct/swe_flow` | 2 | 47.82 | 23.91 (incomplete) |
| `task_evolve/seta_evol` | 0 | 20.16 | Undefined: 0 accepted |
| `tasksmith/tasksmith` | 0 | Unknown | Undefined: 0 accepted |
| `terminal_reconstruct/terminalworld` | 0 | Unknown | Undefined: 0 accepted |
| `terminal_synth/dataarc` | 0 | 54.04 | Undefined: 0 accepted |
| `terminal_synth/endless_terminals` | 0 | 73.14 | Undefined: 0 accepted |
| `terminal_synth/seta_seed2synth` | 0 | Unknown | Undefined: 0 accepted |
| `terminal_synth/tmax` | 0 | 72.82 | Undefined: 0 accepted |

Dollar interpretation: existing free GLM and allocated TRC/CoreWeave have zero incremental service charge under our arrangement. Daytona credits/invoices remain unverified; the recorded 2-vCPU/4-GiB/10-GiB list-rate equivalent is $0.16668/hour, not confirmed spend. The $2,000 ceiling and $1,323 conservative estimates/holds leave $677 of reservation headroom; this is not a billing total. Full recurring cost per accepted task, including all failures and required review, remains unknown. [Budget](https://github.com/Open-Athena/biotasks/blob/7e17c1124c7dc91cea29a87c0fd1925447090e47/experiments/21-repo2rlenv/continuation-20261018/budget.json), [source lifecycle attribution](https://github.com/Open-Athena/biotasks/blob/f0f86b04d8e7fda2f8e49f970a173a32d454f013/experiments/21-repo2rlenv/continuation-20261018/route-compute-attribution.json).

Supporting evidence: [updated methods assessment](https://github.com/Open-Athena/biotasks/blob/13a24d9a592006564624cf62f719969102cf9c2f/experiments/21-repo2rlenv/continuation-20261018/scale-up-assessment.md), [reproducible partial time ledger](https://github.com/Open-Athena/biotasks/blob/13a24d9a592006564624cf62f719969102cf9c2f/experiments/21-repo2rlenv/continuation-20261018/time-per-task-partial.json), and [pause/endpoint receipt](https://github.com/Open-Athena/biotasks/blob/13a24d9a592006564624cf62f719969102cf9c2f/experiments/21-repo2rlenv/continuation-20261018/user-pause-20261019.json).
