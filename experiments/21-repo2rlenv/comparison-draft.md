# Interim comparison — issue 21

Status: incomplete, 2026-10-17. This document organizes verified findings; it is not the final campaign funnel or a completion claim. Updated through the 22:33 UTC archive verification. The [route matrix](applicability.csv) records route-specific applicability. Runs, candidate caps, failures and repeated lineages must be reconciled before calculating yield.

## Competencies and independent outcomes

| Cohort | What the task exercises | Evidence available | Limit of the finding |
| --- | --- | --- | --- |
| scikit-bio PR2633, portable PR-runtime profile | Numerical stability in a statistical biology implementation | Independently accepted; one blind GLM attempt scored 1 with 1/1 F2P and 59/59 P2P tests | Instruction includes expected values and a suggested numerical fix; one task is not a yield or general solver-performance estimate |
| Biopython LCC, full-source SWE-smith adaptation | Sequence complexity / entropy implementation | Independently accepted; one blind GLM attempt scored 1 with 12/12 tests | Explicit source-packaging and solver-tooling adaptations; bounded library-function task rather than an end-to-end biological analysis |
| SCALER synthetic DNA edit distance | Algorithmic sequence-distance reasoning | Three native tasks accepted; independent family oracle and native/Marin control comparison | One synthetic family, not three distinct competencies; blind attempts remain pending |
| scikit-bio SWE-Next and fixture-adapted R2E-Gym | The same PR2633 numerical-stability repair | Native exports and six independent correctness controls per export | Shared problem lineage; fresh solver runtime/final acceptance and blind attempts pending |
| scikit-bio SWE-gen | The same PR2633 repair at its exact PR head | Native export and six independent correctness controls verified | Fresh solver-runtime validation, final acceptance and blind attempt pending; E-step-only partial fix passes all 60 tests |
| Biopython QCP PR5317 | Collinear three-dimensional coordinate alignment | One SWE-gen export: native healthy 9/9, defective 8/9, nop 0/reference 1; independent controls submitted | Native export publicly preserved; independent acceptance and blind attempt pending |

Decisive evidence: [PR solver](evidence/pr-blind-solver-01/summary.json), [LCC solver](evidence/lcc-blind-solver-01/summary.json), [SCALER acceptance](evidence/scaler-native-acceptance/summary.json), [SWE-Next controls](evidence/swe-next-independent-01), [R2E-Gym controls](evidence/r2e-gym-independent-01), [SWE-gen review](evidence/history-export-review/swe-gen-skbio-01.json), [QCP submission](evidence/swe-gen-biopython-01/submission.json).

The two completed blind attempts both earned reward 1. They are selected, independently accepted tasks with different grading contracts, not a representative benchmark sample. Do not report a campaign-wide success rate or treat pending attempts as failures.

## Generation and execution limitations

- TMax's selected biological cohort produced zero exports from three candidates and twelve model calls. All nine initial-test responses failed native test-shape validation. The preserved responses explain the validator outcome but do not establish whether the underlying formatting problem originated in the model or an earlier transport component. See [TMax evidence](evidence/tmax-biological-02).
- Scikit-bio R2E exhausted its ten-candidate allowance with thirty authoring responses and zero exports. Preserve syntax and empty-comment failures rather than manually repairing the generated program and reporting it as native success. See [R2E audit](evidence/r2e-skbio-author-01).
- SETA Evol materialization timed out on its first builder request. No response was preserved; usage is unknown, not zero. Its second schema-valid saved design was unattempted. See [result](evidence/parent-evolution-build-01/result-summary.json) and [public preservation receipt](hf-parent-evolution-build-01-upload-receipt.json).
- The two Code-instruct cohorts have inconclusive capture failures. Actual attempted candidate counts and model usage are unknown. Their first-pass allowances are conservatively consumed; neither zero attempts nor ten observed attempts is justified. See [reconciliation](evidence/code-instruct-capture-diagnosis/candidate-budget-reconciliation.json).
- Non-Python repository inclusion produced PR-diff artifacts, but patch similarity does not establish executable C++/R task correctness. Native test-report compatibility still limits functional routes. Preserve unsupported-language/profile cases outside generation-failure denominators.
- TerminalWorld intake remains gated by recording reuse terms and missing fixtures. Model/backend constraints on Tasksmith, CodeMidas and FrontierSmith are separate from generation failures. The route matrix records these distinctions.

These observations support further evaluation of source-grounded software-repair tasks and careful investigation of structured authoring failures. They do not yet support ranking recipe productivity or a final expansion recommendation.

## Harbor and Marin compatibility

Harbor is the preserved native task format for executed exports. Marin conversion is a separate, evidence-backed assessment; export, conversion, runtime agreement and Atlas admission are distinct states.

SCALER demonstrates why numeric reward agreement is insufficient: its native -1/+1 values survive the converted runtime, but the pinned Marin result metadata still reports 0/1 bounds. [The range diagnosis](evidence/marin-scaler-runtime-01/score-range-diagnosis.json) records the exact pinned source and runtime evidence. This is an unresolved compatibility finding; silently normalizing the rewards would change the task contract.

The native/converted PR-runtime and LCC controls provide evidence for their specific tested structures and profiles. They do not establish admission or training readiness for other exports. Remaining structures and candidate bundles require their own assessment, including preservation of private grading assets, fixture lineage, environment behavior and native reward semantics.

## Still required for the final report

1. Finish or record bounded outcomes for remaining applicable repository/cohort routes, retaining exact source/profile revisions and shared lineage.
2. Complete independent acceptance and fresh solver-runtime checks for candidate exports; run one blind attempt on every accepted task.
3. Reconcile the full per-repository and per-cohort funnel, preserving unknown counts, candidate caps, adaptations and incomplete attempts.
4. Consolidate model usage, worker time, cost uncertainty, manual interventions and public artifact references.
5. Assess each distinct environment/verifier structure against the pinned Marin conversion/runtime; distinguish unsupported metadata from executed reward parity and Atlas admission.
6. Publish conclusions and expansion/adaptation recommendations only after the preceding evidence is reconciled. Negative and inconclusive outcomes are valid; unexecuted applicable work remains incomplete.
