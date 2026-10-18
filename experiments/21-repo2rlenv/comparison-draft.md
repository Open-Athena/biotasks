# Interim comparison: Repo2RLEnv biological repository pilot

Status at 2026-10-18 04:19 UTC: eight accepted correctness/algorithmic tasks have eight completed blind attempts. Twelve additional PR-diff tasks across all four repositories are admitted only for native patch similarity; the three bedtools blind attempts have completed and nine remaining blind attempts are prepared. All24 native no-model controls passed0/1 and their24 exact sandboxes are independently absent. The experiment and final completion audit remain open.

The [route/cohort census](evidence/campaign-census-20261018/census.json) covers all 23 implemented methods through 68 repository/cohort scope entries; the planned Sec-bench recipe is excluded. Retained generation records map to 29 distinct execution units. Their retrospective target/candidate ceiling is 87/290, subject to applicability and operational budgets. A single total N frozen before launch is not demonstrated by the early manifests. These retrospective figures do not describe achieved tasks or an extension of candidate allowances.

## Accepted tasks and blind results

| Task/profile | Competency and lineage | Native blind result | Interpretation and limit |
| --- | --- | --- | --- |
| Portable scikit-bio PR2633 | Numerical stability in a scientific library | 1; 60/60 tests | Explicit compiled-runtime adaptation. Instruction supplies expected values and a numerical hint. |
| Fixture-adapted scikit-bio R2E-Gym | Same PR2633 historical problem | 0; 59/60 tests after 12 turns | Submitted source remained unchanged; no trial exception or repeat. Different generated instruction/profile, shared problem lineage. |
| Biopython LCC full-source adaptation | Local sequence-composition complexity/entropy | 1; 12/12 tests | A bounded library-function repair with synthetic mutation and supplied examples. |
| scikit-bio Esty interval | Singleton/doubleton variance formula | 1; 34/34 tests | Independent alternative and two meaningful incorrect controls tested. |
| scikit-bio observed_features | Count-vector richness alias | 1; 34/34 tests | Independent alternative and two meaningful incorrect controls tested; limited scientific complexity. |
| Three SCALER DNA edit-distance tasks | One synthetic algorithmic family | Each +1 under native -1/+1 grading | Three task instances, one family; no observed biological measurement. |
| Three bedtools PR-diff tasks | C++ source edits, formatting and platform behavior | 0, 0.784762, 0.380675; each reached 12 episodes | Six fresh runtime no-op/reference controls passed 0/1. Admission is only for continuous patch similarity: no compilation, functional correctness, biological-performance or pass@1 claim. |
| Three DESeq2 PR-diff tasks | R source edits for historical statistical-library changes | Pending | Six native similarity controls passed 0/1, all exact sandboxes independently absent; no R functional execution. |
| Three Biopython PR-diff tasks | Documentation and codon-alignment convenience API edits | Prepared | Six native similarity controls0/1; no functional or biological inference claim. |
| Three scikit-bio PR-diff tasks | ASCII sequence conversion, PR2633 underflow and GPU-dispatch edits | Prepared | Six native similarity controls0/1; shared PR2633 lineage and no GPU execution. |

[Acceptance and solver records](evidence/campaign-census-20261018/census.json) preserve individual task IDs and evidence links. The eight scored tasks are not eight independent biological problems: PR2633 is shared across profiles and SCALER instances share one family. Different reward contracts and repeated lineages prevent a meaningful pooled benchmark success rate.

The bedtools [control and admission evidence](evidence/prdiff-bedtools-provider-01/summary.json) is retained in [public snapshot 0572407a](https://huggingface.co/buckets/open-athena/biotasks/tree/research/21-repo2rlenv/2026-10-18/0572407a98fbfaa32ca28d6cdb5328ad37874fd341c258289cbc03b26a339c0e): 30 anonymously verified objects and 54 native archive members. All six exact sandbox IDs are independently absent. Its similarity scorer awards structural credit to reversed changes and some credit to unrelated edits; scores must retain their native meaning.


The [bedtools blind record](evidence/prdiff-bedtools-blind-01/summary.json) retains all three native similarity scores, 12 episodes per task and no trial exceptions. Input/output tokens were 139,693/9,104, 153,042/8,368 and 157,993/9,298 respectively; reasoning-token breakdown is unavailable. Per-response output stayed within 2,048 tokens. No separate final source-tree/diff artifact was declared by the native task; original trajectories, panes and verifier evidence are retained, with private API routing fields redacted only in public copies.

The [bedtools blind archive](https://huggingface.co/buckets/open-athena/biotasks/tree/research/21-repo2rlenv/2026-10-18/983e13046006974b901e040832b45291b9e05a808e3946dda3734bbca0786af9) has25 anonymously verified objects/33 native members; the [DESeq2 control archive](https://huggingface.co/buckets/open-athena/biotasks/tree/research/21-repo2rlenv/2026-10-18/2f84ba34c490e5a56616c1e8153ff450e998032e6e0e8814e3c2f3c4c2a220ad) has31/54.

## Rejected, unresolved and zero-export outcomes

| Route/profile | Evidence-based outcome | Scope of the finding |
| --- | --- | --- |
| scikit-bio Strong, SWE-smith | Incorrect constant passes all 34 native tests | Independent admission rejected; generator success is not verifier adequacy. |
| Biopython GC-skew, SWE-flow | Two incorrect zero-only submissions pass all 12 tests | Independent admission rejected despite native no-op/reference 0/1. |
| scikit-bio SWE-gen and SWE-Next | Native controls pass, but generated instruction adds an M-step requirement not distinguished by native tests | Original instructions are rejected; no blind attempt on either rejected task. |
| Biopython QCP, SWE-gen | Reference 9/9 versus baseline 8/9 and independent controls pass; instruction demands unsupported ordinary-input precision near 1e-15 | Original instruction rejected; native test tolerances do not justify the stated requirement. |
| Original Biopython PR/commit/CVE exports | Historical 1 F2P/54 P2P validation preserved; local-only base images, fresh task controls and valid-alternative acceptance unresolved | Three route exports share one historical fix. They remain outside pilot admission; this does not prove that a future portable adaptation cannot work. Exported P2P lists contain 54/50/50 tests respectively. |
| Native scikit-bio commit | One selected source: patched 6 tests pass, defective checkout cannot collect the newly introduced import; no native test-level F2P | Zero exports without filter bypass or test rewriting. Single-source calibration falls below the three-task target. |
| R2E authoring on each Python repository | Ten candidates and 30 responses per repository; zero exports | Native syntax/shape checks reject saved answers. Original outputs are retained without repairing generated code outside the protocol. |
| Broader Biopython R2E-Gym history | 2,000 records, 1,993 filtered, 7 materialization attempts, zero exports/model calls | Five native snapshot path-policy errors and two bootstrap failures. Truncated bootstrap stderr leaves two root causes unavailable. |
| Broader Biopython SWE-Next | Three additional PR inputs, two eligible; zero exports/model calls | One source filter and two snapshot path-policy errors. Prior PR5317 remains consumed; no allowance reset. |
| CodeInstruct on both Python repositories | Terminal authoring jobs with empty supported archives | Candidate counts, outputs and usage remain unknown. Each ten-candidate allowance is conservatively consumed; no zero-yield claim or automatic rerun. |
| SETA seed synthesis and evolution | Invalid/schema-incomplete responses and builder timeouts; zero exports | Some prepared inputs were never attempted. Saved designs, original responses and incomplete requests are distinct stages. |
| DataArc | One candidate, two completed responses and a third request without retained response; no accepted task | Raw export count is unavailable; no validated task or solver result. |
| TMax and Endless Terminals | Three/ten candidates and 12/34 responses respectively; zero exports | Native initial-test shape and repair checks reject the outputs. |

The [applicability matrix](applicability.csv), [census](evidence/campaign-census-20261018/census.json) and original summaries identify route-specific evidence and unknown values. Initial setup/capture failures remain separate from corrected attempts. Candidate repairs and adaptations are not additional independent problems, and a partially executed input pool is not an exhausted ten-candidate search.

## Backend, model and input limits

Tasksmith requires its native Anthropic author. CodeMidas accepts a literal proprietary-model allowlist and rejects a custom endpoint. FrontierSmith's native allowlist and direct Responses contract reject the GLM baseline before credential/API use. These are baseline model-client blockers; no paid fallback was used.

Native equivalence generation directly couples local Docker execution and model completion on its caller. The selected Iris profile has no Docker binary; the no-model backend probe therefore fails native availability. This is a measured profile limitation, not a proof that a future transport/colocation adapter is impossible. Its learner-visible reference is a separate curation limitation.

CliGym's native constructor requires test_paths exactly [tests], unlike the selected Biopython Tests/ and scikit-bio in-package profiles. C++/R shell/make/testthat dispatcher probes return empty maps; these synthetic parser probes do not establish repository-test execution. Only PR-diff has executed across all four repository languages. DESeq2 PR-diff controls do not execute R biological analyses.

TerminalWorld screened three public recording candidates, with two passing native screening and one excluded. Recording reuse terms and fixture gates are unresolved; no recording-based authoring ran. Missing eligible inputs are recorded separately from generation failure.

## Retained generation usage

This table reproduces the 33 evidence-linked generation/materialization records, not all campaign API dispatches. Earlier diagnostic requests, uncaptured requests and later solver usage are separate. Unknown means unavailable; responses are not necessarily dispatched-call counts. Output includes reasoning, and missing reasoning breakdown remains unknown. Candidate numbers refer to each row's recorded stage; mutation screening, authoring, source filtering and materialization are not interchangeable.

| Record | Recorded candidates | Exports | Preserved responses | Input tokens | Combined output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| swe-gen-skbio-01 | 1 | 1 | 1 | 4042 | 12034 | 11077 |
| swe-next-skbio-01 | 1 | 1 | 1 | 6388 | 25000 | 23740 |
| r2e-gym-skbio-fixtures-02 | 1 | 1 | 1 | 5661 | 7459 | 6508 |
| swe-gen-biopython-01 | 1 | 1 | 1 | 3347 | 13623 | 12557 |
| swe-next-biopython-01 | 1 | 0 | 0 | 0 | 0 | 0 |
| r2e-gym-biopython-01 | 0 | 0 | 0 | 0 | 0 | 0 |
| r2e-skbio-author-01 | 10 | 0 | 30 | 94162 | 1179584 | unknown |
| r2e-biopython-author-01 | 10 | 0 | 30 | 117063 | 955546 | 871634 |
| tmax-biological-02 | 3 | 0 | 12 | 54166 | 647644 | 601324 |
| endless-biological-02 | 10 | 0 | 34 | 130826 | 860060 | 768301 |
| parent-evolution-build-01 | unknown | 0 | 0 | unknown | unknown | unknown |
| code-instruct-biopython | unknown | unknown | unknown | unknown | unknown | unknown |
| code-instruct-scikit-bio | unknown | unknown | unknown | unknown | unknown | unknown |
| biopython-author-02 | 3 | 1 | 4 | 6816 | 472935 | 471638 |
| skbio-author-03 | 3 | 2 | 4 | 5145 | 321836 | 317647 |
| biopython-flow-author-01 | 3 | 1 | 6 | 19370 | 17209 | 14873 |
| skbio-flow-author-01 | 3 | 3 | 6 | 15933 | 39009 | 33651 |
| pr-diff-01/biopython/biopython | 10 | 4 | 0 | 0 | 0 | 0 |
| pr-diff-01/scikit-bio/scikit-bio | 10 | 3 | 0 | 0 | 0 | 0 |
| pr-diff-01/arq5x/bedtools2 | 10 | 6 | 0 | 0 | 0 | 0 |
| pr-diff-01/thelovelab/DESeq2 | 10 | 6 | 0 | 0 | 0 | 0 |
| biopython-pr-01 | 1 | 1 | 0 | unknown | unknown | unknown |
| biopython-commit-01 | 1 | 1 | 0 | unknown | unknown | unknown |
| biopython-cve-01 | 1 | 1 | 0 | unknown | unknown | unknown |
| skbio-pr-runtime-01 | 1 | 0 | 0 | unknown | unknown | unknown |
| skbio-pr-runtime-02 | 1 | 1 | 0 | unknown | unknown | unknown |
| seta-build-01 | 2 | 0 | 3 | 44016 | 266483 | 244540 |
| dataarc-build-01 | 1 | unknown | 2 | 15502 | 227667 | 217852 |
| scaler-dna-01 | 3 | 3 | 0 | 0 | 0 | 0 |
| skbio-commit-01 | 0 | 0 | 0 | 0 | 0 | 0 |
| skbio-commit-02 | 1 | 0 | 0 | 0 | 0 | 0 |
| r2e-gym-biopython-seqfeature-02 | 7 | 0 | 0 | 0 | 0 | 0 |
| swe-next-biopython-broader-02 | 2 | 0 | 0 | 0 | 0 | 0 |

The [reconciliation](evidence/interim-results-20261017/reconciled-subset.json) links each value to its exact source and records stage-specific counters that this compact table cannot display. Later admission decisions are overlaid in the census rather than rewriting historical generation summaries. Whole-campaign API usage, separate worker time and final funnels still require reconciliation; no cost-per-task or overall production yield is inferred.

The [retained controller timing inventory](evidence/controller-timing-reconciliation-20261018/campaign-controller-times.json) covers all75 server-retained issue-prefix jobs and75 finished attempt spans, totaling54884.529 seconds (15.2457 controller-hours). These spans overlap and exclude separate Daytona lifetimes; they are not campaign elapsed time, CPU utilization or billed time. Differently named/expired work is outside the prefix inventory.

## Interventions and Marin compatibility

| Intervention | What changed | Comparison boundary |
| --- | --- | --- |
| Free GLM compatibility | Adapted authoring ceiling 131,072 combined output tokens, explicit medium effort, 1,200-second request timeout | Native-limit failures retained. Solver remains one 900-second/12-turn/2,048-token attempt, native/unset effort. |
| Source/environment packaging | Full-source contexts, compiled-extension restoration, fixture roots and regular license bytes where recorded | Native source profiles and explicit adaptations remain distinct; none of these establishes general repository support. |
| Provider transport/tooling | Owned Iris/Daytona bridge, build-time tmux, explicit offline policy, recorded sandbox IDs | Runtime changes and original asset hashes retained; direct native Docker routes remain blocked where unadapted. |
| Evidence capture | Supported temporary archive recovery, original executable modes, append-only HF snapshots and anonymous hash/mode verification | Capture failures and superseded manifests remain preserved rather than relabeled successful. |
| Marin conversion | Explicit source-specific converters, pinned TaskSpec/runtime and native reward controls | No silent reward normalization or Atlas admission. |

At Marin pin 45a044387ccd95ab698b4a592056aadaff961540, [executed structure coverage](evidence/marin-structure-coverage/coverage.json) includes native/converted reward comparisons for PR-diff (3 cases), fractional PR-runtime (6), separate binary learner/verifier contexts (6), and three SCALER variants (12). These represent four structures, not all candidates. SCALER numeric parity passes, but pinned GradeResult range metadata remains 0/1 despite native -1/+1; conversion is not admitted without an explicit range-contract resolution. Temporary registry images do not establish public training-image availability. No Atlas admission or training readiness is claimed.

## Current accounting and remaining work

Estimates and holds are $908 of the approved $1,000 ceiling, with $92 remaining allowance. They retain conservative failed/controller reservations and are not verified invoices or credit balances. Both most recent controllers are terminal, and all three/six exact blind/control sandboxes are independently absent. Both capacity claims are released after verified public archive publication. Biopython/scikit-bio controllers are also terminal; their capacity claims await public archive verification. Existing free GLM is the only inference service used, without new GPUs or paid-model fallback.

The local retention audit maps 63 manifests: 62 match verified public receipts; one failed mode-descriptor manifest is explicitly superseded by a verified correction with identical object/member bytes and hashes. This is a local publication-history audit, not a fresh remote availability or universal source-integrity assertion. All three new PR-diff snapshots have independent anonymous-download receipts.

Complete the remaining selected PR-diff runtime controls and one blind attempt for each admitted task; preserve outputs and verify exact cleanup. Reconcile all terminal runs, model usage and controller/worker time, finish the full per-unit funnel and protocol deviations, and update the issue with conclusions and decisive immutable links. The present census and partial usage table do not close those requirements.

The strongest current expansion candidates are narrowly scoped correctness profiles that survive independent alternatives and incorrect submissions. PR-diff remains useful as a software-edit similarity exercise across languages, with its score meaning intact. Raw export volume provides little evidence of curation quality: several generated tasks fail independent contract checks, and multiple GLM routes return no native-valid exports. Broader expansion requires evidence appropriate to the intended reward and scientific competency.
