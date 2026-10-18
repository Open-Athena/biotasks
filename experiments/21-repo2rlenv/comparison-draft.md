# Interim comparison — issue 21

Status: incomplete, 2026-10-17. This document organizes verified findings; it is not the final campaign funnel or a completion claim. Updated through the 2026-10-18 02:14 UTC result reconciliation; running jobs are not counted as completed outcomes. The [route matrix](applicability.csv) records route-specific applicability. Runs, candidate caps, failures and repeated lineages must be reconciled before calculating yield.

## Competencies and independent outcomes

| Cohort | What the task exercises | Evidence available | Limit of the finding |
| --- | --- | --- | --- |
| scikit-bio PR2633, portable PR-runtime profile | Numerical stability in a statistical biology implementation | Independently accepted; one blind GLM attempt scored 1 with 1/1 F2P and 59/59 P2P tests | Instruction includes expected values and a suggested numerical fix; one task is not a yield or general solver-performance estimate |
| Biopython LCC, full-source SWE-smith adaptation | Sequence complexity / entropy implementation | Independently accepted; one blind GLM attempt scored 1 with 12/12 tests | Explicit source-packaging and solver-tooling adaptations; bounded library-function task rather than an end-to-end biological analysis |
| SCALER synthetic DNA edit distance | Algorithmic sequence-distance reasoning | Three native tasks accepted; independent family oracle and native/Marin control comparison; all three fresh provider checks passed -1/+1 | One synthetic family, not three distinct competencies; all three single blind attempts scored native +1 |
| scikit-bio SWE-Next | PR2633 numerical-stability repair | Native export, six independent controls and fresh provider rewards 0/1 | Rejected generated instruction: extra M-step requirement is not distinguished by native coverage |
| scikit-bio fixture-adapted R2E-Gym | The same PR2633 numerical-stability repair | Independently accepted after six controls and fresh separate-context provider rewards 0/1 | One blind attempt scored 0: 59/60 tests pass, submitted source unchanged after 12 turns. Shared PR2633 lineage; not a new independent problem |
| scikit-bio SWE-gen | The same PR2633 repair at its exact PR head | Native export, six independent correctness controls and fresh separate-context no-op/reference runtime rewards 0/1 verified | Rejected: instruction requires guarded M-step updates, while E-step-only patch retains unguarded division and passes all 60 tests |
| scikit-bio Strong dominance, SWE-smith | Diversity-index function reconstruction | Baseline/reference/alternative/incorrect-constant/zero rewards 0,1,1,1,0 | Rejected: an incorrect constant passes all 34 native tests; no blind solve |
| Biopython GC-skew, SWE-flow | Windowed nucleotide-composition calculation | Original export failed build; idempotent license-bootstrap adaptation scored native no-op 0/reference 1 | Rejected: both incorrect zero-only implementations pass all 12 tests; no blind attempt |
| scikit-bio Esty confidence interval, SWE-smith | Singleton/doubleton variance formula | Baseline/reference/alternative/wrong-clipping/wrong-variance rewards 0,1,1,0,0 across 34 tests | Accepted; one blind attempt scored 1, all 34 tests passed, both solver sandboxes independently absent |
| Biopython QCP PR5317 | Collinear three-dimensional coordinate alignment | One SWE-gen export: native healthy 9/9, defective 8/9, nop 0/reference 1; corrected independent run02 preserved all six expected control rewards: 0,1,1,0,0,0 | Rejected at instruction/verifier review: ordinary-input precision claim near 1e-15 is not justified by the native comparison tolerances; original export and control scores retained |

Decisive evidence: [PR solver](evidence/pr-blind-solver-01/summary.json), [LCC solver](evidence/lcc-blind-solver-01/summary.json), [SCALER acceptance](evidence/scaler-native-acceptance/summary.json), [SWE-Next controls](evidence/swe-next-independent-01), [R2E-Gym controls](evidence/r2e-gym-independent-01), [SWE-gen review](evidence/history-export-review/swe-gen-skbio-01.json), [QCP submission](evidence/swe-gen-biopython-01/submission.json).

Eight accepted tasks have completed one blind attempt each: seven positive native rewards and one zero (R2E-Gym); grading contracts differ. They are selected, independently accepted tasks with different grading contracts; the three SCALER variants share one synthetic family. This is not a representative benchmark sample. Do not report a campaign-wide success rate or treat pending attempts as failures.

## Generation and execution limitations

- Biopython R2E-Gym scanned 2,000 first-parent history records under the narrow QCP profile, all source-filtered before model calls. This is not 2,000 generation attempts or a repository-wide incompatibility finding. A broader source-only scan found ten eligible commits after 133 records; this is source availability, with no builds or authoring. A sequence-feature profile is prepared within the unchanged first-pass allowance.
- Biopython GC-skew original export failed native builds on a symlink-only LICENSE assertion. A separately recorded idempotent bootstrap adaptation completed native no-op/reference grading with rewards 0/1; independent controls reject the native task because both incorrect zero-only submissions pass all 12 tests. Original failure, corrected export and independent controls are separately public. These are two export/build attempts for one saved candidate, not two generated problems.
- Esty confidence-interval control run01 failed worker-name schema validation before sandbox allocation. No controls or model calls ran. The corrected run02 retained all frozen inputs and passed five independent controls with rewards 0,1,1,0,0. Subsequent fresh runtime and final review accepted this task; its one blind attempt scored 1.
- Biopython SWE-Next rejected its first source candidate before model calls because the selected test change only reformats an existing expression. One of ten candidates is consumed; broader bounded source selection remains pending. See [source review](evidence/swe-next-biopython-01/source-filter-review.json).
- Endless biological adaptation exhausted ten candidates with 34 model responses and zero exports: two design parse failures and eight exhausted initial-test repair sequences. No task build or solver trial started. See [Endless evidence](evidence/endless-biological-02).

- TMax's selected biological cohort produced zero exports from three candidates and twelve model calls. All nine initial-test responses failed native test-shape validation. The preserved responses explain the validator outcome but do not establish whether the underlying formatting problem originated in the model or an earlier transport component. See [TMax evidence](evidence/tmax-biological-02).
- Biopython R2E exhausted ten candidates with thirty responses and zero exports: one malformed structured response, 24 Python syntax failures and five parseable modules without explicit test definitions. Preserved usage includes 117,063 input and 955,546 combined output tokens (871,634 reasoning). [Native audit](evidence/r2e-biopython-author-01/summary.json).
- Scikit-bio R2E exhausted its ten-candidate allowance with thirty authoring responses and zero exports. Preserve syntax and empty-comment failures rather than manually repairing the generated program and reporting it as native success. See [R2E audit](evidence/r2e-skbio-author-01).
- SETA Evol materialization timed out on its first builder request. No response was preserved; usage is unknown, not zero. Its second schema-valid saved design was unattempted. See [result](evidence/parent-evolution-build-01/result-summary.json) and [public preservation receipt](hf-parent-evolution-build-01-upload-receipt.json).
- The two Code-instruct cohorts have inconclusive capture failures. Actual attempted candidate counts and model usage are unknown. Their first-pass allowances are conservatively consumed; neither zero attempts nor ten observed attempts is justified. See [reconciliation](evidence/code-instruct-capture-diagnosis/candidate-budget-reconciliation.json).
- Non-Python repository inclusion produced PR-diff artifacts, but patch similarity does not establish executable C++/R task correctness. Native test-report compatibility still limits functional routes. Preserve unsupported-language/profile cases outside generation-failure denominators.
- TerminalWorld intake remains gated by recording reuse terms and missing fixtures. Model/backend constraints on Tasksmith, CodeMidas and FrontierSmith are separate from generation failures. The route matrix records these distinctions.

These observations support further evaluation of source-grounded software-repair tasks and careful investigation of structured authoring failures. They do not yet support ranking recipe productivity or a final expansion recommendation.

## Preserved model usage (partial)

The [reconciled subset](evidence/interim-results-20261017/reconciled-subset.json) links thirty-three generation/materialization rows, fourteen validation rows and eight solver rows to seventy-eight hashed source records, with three final rejections and three additional accepted-task reviews. It is not the complete campaign funnel: earlier diagnostics and other routes still need reconciliation. Response counts are preserved responses, not inferred request counts.

| Generation run | Candidates | Exports | Preserved responses | Input tokens | Combined output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| swe-gen-skbio-01 | 1 | 1 | 1 | 4042 | 12034 | 11077 |
| swe-next-skbio-01 | 1 | 1 | 1 | 6388 | 25000 | 23740 |
| r2e-gym-skbio-fixtures-02 | 1 | 1 | 1 | 5661 | 7459 | 6508 |
| swe-gen-biopython-01 | 1 | 1 | 1 | 3347 | 13623 | 12557 |
| swe-next-biopython-01 | 1 | 0 | 0 | 0 | 0 | 0 |
| r2e-gym-biopython-01 | 0 eligible (2000 history records filtered) | 0 | 0 | 0 | 0 | 0 |
| r2e-skbio-author-01 | 10 | 0 | 30 | 94162 | 1179584 | unknown |
| r2e-biopython-author-01 | 10 | 0 | 30 | 117063 | 955546 | 871634 |
| tmax-biological-02 | 3 | 0 | 12 | 54166 | 647644 | 601324 |
| endless-biological-02 | 10 | 0 | 34 | 130826 | 860060 | 768301 |
| parent-evolution-build-01 | unknown | 0 | 0 | unknown | unknown | unknown |
| code-instruct-biopython | unknown | unknown | unknown | unknown | unknown | unknown |
| code-instruct-scikit-bio | unknown | unknown | unknown | unknown | unknown | unknown |

SETA Evol's row covers materialization only: one builder request was dispatched, no completed response was preserved, and the second saved design was unattempted. Its candidate-build count is not comparable to generator candidate counts. Both Code-instruct allowances are conservatively consumed, but actual attempts and exports remain unknown. Reasoning tokens are included in combined output totals; unavailable breakdowns remain unknown. These rows do not justify cost-per-task or whole-campaign yield estimates.

## Harbor and Marin compatibility

Harbor is the preserved native task format for executed exports. Marin conversion is a separate, evidence-backed assessment; export, conversion, runtime agreement and Atlas admission are distinct states.

SCALER demonstrates why numeric reward agreement is insufficient: its native -1/+1 values survive the converted runtime, but the pinned Marin result metadata still reports 0/1 bounds. [The range diagnosis](evidence/marin-scaler-runtime-01/score-range-diagnosis.json) records the exact pinned source and runtime evidence. This is an unresolved compatibility finding; silently normalizing the rewards would change the task contract.

The [structure reconciliation](evidence/marin-structure-coverage/coverage.json) confirms four representative structures were executed: PR-diff patch similarity (three matching controls), portable PR-runtime fractional F2P/P2P grading (six), LCC separate-context binary grading (six), and SCALER numeric grading (twelve across three tasks). The corrected PR-diff runtime already passed; the earlier harness failure is preserved separately. Its similarity reward is not functional correctness, and its temporary image is not a published training image.

The three scikit-bio history exports share byte-identical grader and wrapper code with the tested LCC structure. This reduces duplicate structure-level work but does not establish candidate runtime readiness, acceptance or Atlas admission: source images, fixtures, allowed files and task contracts differ. Fresh candidate runtime probes are prepared and await capacity. Any subsequently exported task with a distinct structure still requires representative conversion and execution.

## Still required for the final report

1. Finish or record bounded outcomes for remaining applicable repository/cohort routes, retaining exact source/profile revisions and shared lineage.
2. Complete independent acceptance and fresh solver-runtime checks for candidate exports; run one blind attempt on every accepted task.
3. Reconcile the full per-repository and per-cohort funnel, preserving unknown counts, candidate caps, adaptations and incomplete attempts.
4. Consolidate model usage, worker time, cost uncertainty, manual interventions and public artifact references.
5. Assess each distinct environment/verifier structure against the pinned Marin conversion/runtime; distinguish unsupported metadata from executed reward parity and Atlas admission.
6. Publish conclusions and expansion/adaptation recommendations only after the preceding evidence is reconciled. Negative and inconclusive outcomes are valid; unexecuted applicable work remains incomplete.

Controller timing observation: [twenty retained Iris task records](evidence/controller-timing-reconciliation-20261018/controller-times.json) total 3.6901667 controller wall hours, all terminal at capture. This excludes other historical jobs and separate Daytona workers, and is not verified billed usage. Fresh SWE-gen runtime evidence is [publicly verified](hf-swegen-provider-01-upload-receipt.json); SWE-Next runtime controls also passed 0/1 with cleanup verified, but final instruction acceptance is rejected. Campaign estimates/holds are $683 of the approved $1,000 ceiling; credits and actual charges remain unverified.

Final acceptance review rejects the unchanged SWE-gen and SWE-Next scikit-bio instructions for expanding the M-step requirement beyond native regression coverage ([SWE-gen](evidence/history-final-acceptance/swe-gen-skbio-01/review.json), [SWE-Next](evidence/history-final-acceptance/swe-next-skbio-01/review.json)). The E-step-only case remains an observed full native reward, not a failure of the supplied reproducer. The portable PR-runtime task has a narrower instruction and remains accepted. [QCP review](evidence/qcp-final-acceptance/review.json) rejects an unjustified ordinary-input precision contract; no new offset-control score is claimed. These rejected originals need no blind solver attempt.

Four added source-authoring rows join saved candidate records to native exports: Biopython SWE-smith authored1/3 and exported1 (four prior mutation attempts, three contrasts); scikit-bio SWE-smith authored2/3 and exported2; Biopython SWE-flow authored3/3 and exported1, with two incomplete instructions rejected before export; scikit-bio SWE-flow authored3/3 and exported3. These are stage counts, not four independent end-to-end yield estimates, and exclude earlier token-limit diagnostic calls. Source hashes and preserved response usage are in the linked subset.

R2E-Gym blind result: native binary reward0, no trial exception,12 agent episodes,185345 input/163776 cached-input/7703 combined output tokens. All per-episode reported completion counts are within2048. Source remained byte-identical to the defective input; only the underflow regression failed, with59/60 tests passing. Both sandboxes independently absent. This is a scored unsuccessful attempt, not a task-validity failure or an infrastructure-exception claim. The native commit-runtime profile for alternate scikit-bio fix71912 is prepared and tested at the input boundary, but remains unsubmitted.

The [broader Biopython PR intake](evidence/biopython-broader-pr-intake/intake.json) preserves metadata and full diffs for PR5308/5316 (shared location-hashing issue5193) and PR5358 (Clustal header compatibility), selected through the existing bounded history intake. Test/assertion additions are visible, but native PR entity filters, packaging and runtime contrasts remain unexecuted. These are not new generation attempts or exported tasks.

Esty and observed_features fresh provider controls passed 0/1 with matching checksums and all four sandboxes per probe independently absent. These runtime controls add no generated candidates or blind attempts.

Esty is now independently accepted with its emitted bundle unchanged: the stated interval formula, native ten-vector/all-zero tests, alternative factored variance and two incorrect controls agree; fresh separate-context controls0/1 and all four sandbox deletions are verified. Its one blind attempt scored 1 in six agent episodes, passing all 34 tests; both solver sandboxes independently absent. This makes seven accepted tasks and seven completed blind attempts, including the R2E-Gym zero. observed_features is also accepted after final instruction review, meaningful incorrect/alternative controls and fresh0/1 runtime checks. Its single blind attempt scored1 with34/34 tests in seven episodes; both sandboxes independently absent. Eight accepted tasks/eight scored attempts. Estimates/holds$723/$1000 include two prepared source-run reservations.

Native scikit-bio commit calibration71912 completed after a transport-only launcher correction: one candidate, zero exports, native skip no_fail_to_pass. Patched checkout passed six tests; defective checkout failed collection on the newly imported _build_dmatrix helper, so no test-level F2P identities were extracted. No filter bypass or source/test rewrite; exact worker ID independently absent. Source profile remains a single-source calibration below the three-task target. Broader Biopython SWE-Next input preparation now selects three additional public PRs (5308/5316 hashing share issue5193 lineage;5310 molecular-weight empty-input validation is separate). Exact native merge metadata mapping and unchanged fixture bytes verified; native builds/contrasts/authoring have not run. Previous PR5317 source-filter outcome remains consumed. Estimates/holds$743/$1000.

Broader Biopython history runs completed with zero exports before any GLM authoring. SeqFeature R2E-Gym screened2000 records:1993 filtered,seven materialization attempts, five native historical-snapshot path-policy failures and two Docker bootstrap failures. Broad SWE-Next considered three PRs:PR5308 native-source-filtered, two eligible contrasts failed the same historical path policy. Original PR5317 considered allowance retained (four total SWE-Next PR inputs), no resets or automatic reruns. The image LICENSE/fixture packaging fix does not alter the older Git-archive snapshot policy; exact offending member is not logged. Both exact worker IDs independently404. Separate remote catch-all capture failed, but supported controller captures retain original contrast config/stdout/stderr and source history. Public bounded native-evidence snapshots are prepared, with source checkouts reconstructable from pins and private/duplicate bulk captures excluded. These are materialization-compatibility findings, not GLM-quality results.
