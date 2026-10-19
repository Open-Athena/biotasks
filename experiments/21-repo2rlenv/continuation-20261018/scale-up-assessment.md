# Scale-up assessment: paused for methods clarification

## Living results and decisions — 2026-10-19 19:41 UTC

**Execution is paused at the user’s request while the methods and results are clarified. No new recipe, validation or solver runs will be started.** The experiment remains open. Consolidating the first pass and continuation: **30 task instances accepted after pipeline execution and Codex-assisted review, 30 verified single-attempt GLM scores, and 8 units meeting the three-task target.** These are 18 correctness/algorithmic and 12 patch-similarity tasks; related source families are not independent biological competencies. The complete ledger is below, including failures, unsupported cells and pending work. These are interim results; further execution is paused pending discussion.

**Current scale-up judgment:** native PR-runtime extraction is the strongest candidate for a computational-biology software corpus because it reuses real historical changes/tests without needing an LLM author. Native commit-runtime is promising with less evidence; its upstream default uses an LLM statement rewrite, whereas our accepted replay disabled synthesis. GLM-authored routes have useful examples, but none has yet demonstrated an unattended end-to-end authoring/acceptance pipeline without task-specific Codex assistance.

## Answers for a scale-up decision

**Recommendation: scale historical extraction first; treat GLM-authored routes as experimental until acceptance is automated.** These are qualitative judgments from this small, curated sample, not measured production yields. The detailed route/repository tables and task ledger below include both successful and unsuccessful outcomes and their causes.

| Question | Current answer | What would change the conclusion? |
| --- | --- | --- |
| Which pipelines should we scale? | Native PR-runtime has the strongest correctness evidence (6 accepted); native commit-runtime is promising (1 accepted). PR-diff works across languages (12 accepted) for similarity rewards only. Smith (5), Flow (2), R2E-Gym (1) and Scaler (3 within one family) have useful examples with material limitations. | A held-out batch using frozen reusable profiles and acceptance gates, with rejected candidates and duplicate source families included in the accounting. |
| Which repositories work? | Biopython: 5 correctness + 3 similarity tasks. scikit-bio: 10 correctness + 3 similarity. bedtools2 and DESeq2: 3 similarity tasks each, no accepted executable correctness tasks under the tested profiles. | Reusable C++/R build and test-parser support; broader Python source coverage. Unsupported profiles are not proof of unsuitable repositories. |
| Can free GLM be the author without per-task Codex fixes? | Sometimes at the instruction level: Tsallis retained its original GLM instruction without task-specific feedback. **No authored route has demonstrated unattended authoring plus acceptance.** Manual source review and control construction remain dependencies even when prose is unchanged. Native PR-runtime reuses historical issue/PR text rather than an LLM author per task; repository bootstrap still needs an explicit profile or a cached model-built environment. | An unseen batch with no task-specific Codex edits, feedback, test writing or acceptance decisions; bounded free-GLM author/reviewer calls and frozen deterministic gates. Reusable setup is recorded separately; assisted cases cannot count as autonomous successes. |
| What does each approach cost per accepted task? | **Complete recurring costs remain unknown.** The time ledger below gives partial recorded sandbox-minutes per accepted task and separate solver bounds. GLM and allocated TRC/CoreWeave have zero incremental service charge under our arrangement. Missing lifetimes, review effort and credit/invoice data prevent production-price claims. | Complete phase-level attribution of generation, repairs, failed candidates, validation and storage, divided by accepted tasks. Report one-time engineering and solver evaluation separately, plus tokens, elapsed time and intervention rate. Zero admissions mean undefined cost per accepted task, not $0. |

**Scaling requirement:** the intended production workflow must run with the free GLM endpoint and reusable code, without Codex making task-specific repairs or admission decisions. Current assisted successes are evidence about feasibility, not proof that this requirement has been met. A high solver reward does not establish authoring quality, diversity or autonomous scalability.

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


## Can the free GLM endpoint work without per-task Codex fixes?

GLM can produce usable authored instructions, but this experiment has **not demonstrated unattended GLM-only authoring plus acceptance**. The accepted set benefited from Codex orchestration, source inspection, repository/runtime adaptation, independent incorrect/alternative controls, and sometimes task-specific feedback. The new LCC normalization instruction became acceptable after GLM revised it using explicit source-review feedback about an invalid API example and an unsupported claim. Enspie retained its generated instruction without manual prose repair, but is a small alias/argument-forwarding task. These outcomes must not be labeled as a fully autonomous authoring pipeline.


The admitted Tsallis and Pielou tasks are positive examples of unchanged GLM authorship with no task-specific feedback. Their independently prepared controls and review were manual, so they do not yet meet the end-to-end automation requirement.

The latest unchanged R2E-Gym author instruction was a valid single paragraph, but source review found an unqualified metadata-mask claim incompatible with the boolean-True constructor case. The single call completed within the approved output ceiling; semantic acceptance still required independent review. Its roughly 5.9 minute job interval includes setup and archival and is one observation, not a production throughput estimate. See the [original output and review](https://github.com/Open-Athena/biotasks/blob/079b823ff699051511d8ff49082a89fd1a3ce394/experiments/21-repo2rlenv/continuation-20261018/skbio-r2egym-ascii-author-01/instruction-review.json). Some SWE-Flow outputs were stopped at document-format review without subsequent runtime acceptance checks; those outcomes alone do not establish scientific invalidity.

Treat absence of task-specific Codex edits or feedback as a separate acceptance criterion for scale-up. Preserve the current assisted results rather than relabel them. A qualifying new batch must use frozen repository profiles and code, the free GLM endpoint for any author/reviewer calls, native bounded repair loops, and deterministic automated acceptance checks. Invalid instructions, broken environments and inadequate graders should be rejected with reasons; manually repaired cases belong in a separate assisted cohort. Measure attempted inputs, accepted tasks, duplicate families, task-specific interventions, latency, all failed-candidate resource use, and native solver scores on an unseen input batch. This gate is not yet passed by any complete end-to-end authored route in this experiment.


### Task production versus Codex assistance

The accepted-task table labels provenance explicitly. **All 30 admissions involved Codex review/orchestration; none is evidence of an audited, unattended end-to-end pipeline.** This is not a measured 0% autonomous yield: a frozen unassisted cohort has not been completed.

- **H:** historical pipeline task, with a Codex-prepared portable/runtime profile and case-specific acceptance checks. The upstream fix/tests supply the task; this is an assisted deployment, not an unchanged stock export.
- **D:** native patch-similarity export; Codex performed controls/review. No author model is required.
- **U:** unchanged emitted bundle explicitly confirmed by its acceptance receipt (Esty and observed-features); Codex still designed acceptance controls.
- **G:** original GLM instruction retained with no task-specific author feedback (Enspie, Tsallis, Pielou); export/review/control work remains assisted.
- **F:** GLM revised the new LCC instruction using task-specific feedback written by Codex. This is assisted authoring, even though Codex did not directly rewrite its prose.
- **A:** explicit runtime/build/fixture adaptation by Codex (first LCC and R2E-Gym); original native bundle was not the admitted profile.
- **S:** programmatic Scaler instances from a hand-prepared family; Codex setup/review, not automatic scientific-family discovery.

These labels distinguish task-content feedback, runtime fixes and evaluation work; they should not be collapsed into either “all manual” or “fully automatic.” Unchanged instruction bytes alone do not establish unchanged packaging or automated acceptance.

## What “validated” means here—and who did it

**“Independently accepted” means checked separately from generation in this experiment, with Codex involvement. It does not mean externally audited, Codex-free, or exhaustively scientifically correct.** The reward is computed by code; deciding whether that code tests the right contract has involved Codex.

| Stage | Evidence / checks | Codex’s role | What it does not establish |
| --- | --- | --- | --- |
| Pipeline execution checks | Build succeeds; relevant test identities are collected; broken/reference behavior differs | Wrote or adapted repository/build/fixture profiles and orchestrated execution | Correct prose, adequate coverage or acceptance of every export |
| Instruction/source review | Compare the instruction’s claims/examples with pinned source and tests | Read source and made task-specific accept/reject decisions; sometimes supplied repair feedback | Automated acceptance; exhaustive specification coverage |
| Additional acceptance controls | Run baseline/reference and recorded alternative, partial or deliberately incorrect implementations; repeats where recorded | Wrote case-specific control implementations, selected cases and inspected raw results | A proof that all wrong submissions fail; all tasks do not have identical controls |
| Grading | Execute a deterministic test verifier or patch-similarity calculation | Set up runs and audited retained results; GLM/Codex judgment does not directly supply numerical reward | Similarity becoming correctness; unit tests proving general biological validity |
| Blind solve | One GLM attempt per admitted task, using the fixed solver limits, scored by that verifier | Orchestrated and checked artifact/grade identity; no task-specific solver repair | General model difficulty from one sample or an independent author-quality verdict |
| Marin compatibility | Schema checks, and paired native/Marin execution for explicitly listed profiles | Built/adapted conversion profiles and checked parity | Atlas admission or runtime validation of every task |
| Preservation | Hashes, archive readback, permissions and exact sandbox cleanup receipts | Implemented and checked the record keeping | Scientific correctness |

Example: the Stockholm reference passed, but a partial lowercase-only implementation also earned full reward despite a broader instruction. That candidate was rejected by additional Codex-designed checks. Conversely, unchanged Tsallis/Pielou GLM instructions were accepted after such checks; those are authoring successes with assisted acceptance. The deferred end-to-end grader-integrity diagnostic remains unexecuted.




## Time per task, cost and budget ledger

**Time is clearer than dollars under our free allocations, but two clocks must stay separate.** Wall time measures latency from candidate start to decision. Sandbox-minutes sum active sandbox lifetimes and measure a resource cost; four sandboxes for ten minutes consume forty sandbox-minutes. Neither measures Codex/human effort.

For a fully observed cohort, report `total generation + bounded repairs + acceptance wall time / candidates attempted`, and the same numerator divided by accepted tasks. Include failed candidates; with zero admissions the per-accepted value is undefined. Keep one-time repository setup and blind-solver evaluation separate. Complete end-to-end candidate/acceptance timings are **not yet reconstructed** for this campaign; replacing dollars with minutes cannot fill those missing phases.

**Direct matched example:** the Biopython native PR-runtime batch considered/emitted PR5317, PR5310 and PR5308 in one recorded 84.703-second sandbox lifetime. Two of these sources were later accepted (5317/5308). This is **28.2 sandbox-seconds per generated candidate** or **42.4 sandbox-seconds per ultimately accepted candidate for this generation stage only**. It excludes subsequent acceptance controls, profile engineering and solver evaluation, and is not a complete time-to-accepted-task estimate. The rejected PR5310 stays in the denominator. [Exact cohort/timestamps](https://github.com/Open-Athena/biotasks/blob/7f8e289/experiments/21-repo2rlenv/continuation-20261018/biopython-pr-runtime-native-01/controller-small-summary.json).

**Author latency example:** one R2E-Gym ASCII instruction job took **354.878 seconds (5.9 minutes)** including setup and archival, made one completed GLM call, and was rejected on source-contract review. Its per-attempt job time is known; time per accepted task is undefined because it produced zero admissions. This observation does not include the earlier historical contrast or manual review. [Performance receipt](https://github.com/Open-Athena/biotasks/blob/079b823ff699051511d8ff49082a89fd1a3ce394/experiments/21-repo2rlenv/continuation-20261018/skbio-r2egym-ascii-author-01/performance-summary.json).

### Partial resource-time ledger by approach

Converted directly from the existing exact-lifecycle attribution: 68 attributed workers out of 104 recorded terminated workers; 36 remain unassigned. These are **incomplete recorded sandbox-minutes divided by the full current admission count**, not isolated runtime, wall latency or fair throughput rankings. Missing model/acceptance phases and manual effort are not zero. Rows with no attributed lifetimes remain unknown. The smaller earlier selected-cohort dollar samples use different coverage and are superseded here as the headline comparison; their immutable receipts remain linked evidence.

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


## Proposed next design: PR mining plus a GLM performance filter

**Planning only; execution remains paused.** Two distinct products are possible:

1. **Similarity corpus:** `pr_diff` → structural/reference checks → one blind GLM solve → retain selected reward bands and lineage. This is cheap and avoids per-task authoring, but rewards patch similarity. Low similarity can reflect a valid alternative implementation; it is not proof of difficulty or functional failure.
2. **Correctness corpus:** cheap PR discovery and source/test eligibility → `pr_runtime` before/after contrast → blind GLM solve → retain useful difficulty bands under executable test rewards. Where GLM is used earlier to prioritize candidates, its diff score is a screening signal only; functional verification remains necessary before admission.

The first screening metric should be both **yield of runnable tasks** and **GLM reward at fixed solver settings**, not simply “keep every task GLM fails.” Inspect execution failures separately, deduplicate historical fixes before splitting, and retain a small distribution of easy/medium/unsolved tasks if the goal is an RL curriculum. One attempt gives noisy, model-specific evidence: our 2,048-output-token/12-turn/15-minute solver measures this constrained GLM setup, not intrinsic task difficulty. More attempts or a larger solver allowance would be a new decision, not an automatic continuation.

The scalable part should be fixed code and deterministic filters, with the free endpoint supplying only the model stages. A GLM review stage could propose specification/coverage concerns, but it should not directly supply reward or substitute for executable controls. Count task-specific Codex repairs and admission decisions explicitly; a proposed filter does not retrospectively make the current 30 tasks autonomous outputs.
