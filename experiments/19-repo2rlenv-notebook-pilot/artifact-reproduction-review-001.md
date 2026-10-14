# Independent review of the artifact-reproduction proposal

2026-10-14. An independent reviewer with a fresh context reviewed the
[local proposal](artifact-reproduction-draft.md). The review covered the
design and primary-source documentation; it did not execute the pipeline.

Reviewed draft SHA-256:
`a5559739abc7e00c047ab12aaeae50fe4d18151bcbb764b88313ea7c28c4eea9`.
Checkout base: `3d92a14e0758e3854a14bf0e4549b424400ed527`.
The draft was uncommitted at review time; the hash identifies the reviewed text.
Line references below refer to that snapshot.

## Assessment

The reviewer supports the core approach: retain source provenance, execute all
scientific branches to obtain fresh artifacts, reject unsuitable sources, and
grade outputs deterministically. Direct bounded execution in Daytona is an
appropriate initial feasibility check. Detailed profiling can wait.

Recommendation: proceed after the clarifications below. The review does not
recommend mandatory notebook execution, cell markers or a new general framework.

## 1. Define the supported conversion features before implementation

Draft lines 296–321 name exporters and require faithful conversion but do not
define the admission checks that connect those requirements. An R document can
contain computation in a `purl=FALSE` chunk or an inline expression that the
export omits. The remaining script could still run successfully. Python export
can also retain magics that require notebook execution support. These are
documented limitations of [knitr extraction](https://pkg.yihui.org/rmarkdown-cookbook/purl)
and [nbconvert script export](https://nbconvert.readthedocs.io/en/latest/usage.html#executable-script).

Smallest proposed remedy: define a narrow set of supported execution features
for each initial format, inspect execution-affecting features before conversion,
and reject unsupported cases. This can work with plain scripts and needs no
mandatory cell markers or notebook runtime.

## 2. Clarify the GLM repair boundary before implementation

Draft lines 112–122 permit task-specific repairs, while lines 152–159 prohibit
repairing analysis logic. A worker could change a filtering threshold to resolve
an empty result, classify that as setup, and then generate a matching grader.

Smallest proposed remedy: explicitly distinguish allowed changes to environment,
paths, artifact exports and task packaging from changes to the source analysis.
Preserve the untouched converted baseline and record a diff and permitted
purpose for each subsequent change. Changing scientific computations to make
a candidate pass must not qualify as repair.

The proposal's explicitly documented input reductions are a separate design
choice; this finding concerns silently changing the analysis to rescue a run.

## 3. Review endpoint completeness before freezing a task

Draft lines 105–109 let GLM identify endpoints, then programmatically check the
declared branch-to-artifact map. That verifies the map's internal consistency,
not its completeness. If a trajectory-analysis result is mistaken for a
diagnostic plot, execution and grading can both pass while a scientific branch
is missing.

Smallest proposed remedy: explicitly review completeness against the original
document and scripts independently of the proposed map. Record source references
for included endpoints and reasons for excluding other apparent scientific
results. Freeze the inventory before generating the final contract. This can
be part of an existing review step and does not require a dependency-graph
framework.

## 4. Make valid-alternative checks concrete before freezing a grader

Draft lines 247–259 combine exact membership checks with numerical tolerances.
Two conforming implementations could produce values within tolerance but select
different members near a cutoff or tied rank. Exact membership could reject one;
overly loose comparisons could accept a consequential mistake such as omitted
normalization.

Smallest proposed remedy: state cutoff, tie, missing-value and identity rules in
the public contract. Wherever numerical portability is claimed, exercise an
independently computed conforming alternative and a consequential wrong-method
control for each branch. Reordering a copy of the reference tests representation
handling but does not establish software equivalence.

## 5. Choose the timing gate before a live pilot

Draft lines 217–232 acknowledge headroom but do not define it. A 590-second
reference could pass screening while leaving almost none of a 600-second solver
allowance for reasoning. Since solver success is optional, an unsuccessful blind
attempt would not resolve this admission-policy gap.

Smallest proposed remedy: choose a conservative reference deadline below the
solver allowance, define when the solver clock starts and what it includes,
and set finite setup, reference, verifier and repair budgets before execution.
Treat the initial headroom policy as something to evaluate, not a demonstrated
guarantee. This decision need not block writing the reusable infrastructure.

## Work that can remain deferred

Broader converter support, automatic checkpoint/input reduction and detailed
resource profiling can remain later improvements. The first experiment should
establish faithful extraction and defensible grading on a suitably small source.

## Author response — 2026-10-14

The findings above describe the original reviewed draft. The proposal has now
been revised as follows; the original findings and snapshot identity are retained.

| Finding | Change to the proposal |
| --- | --- |
| 1. Supported conversion features | [Section 7](artifact-reproduction-draft.md#7-convert-to-scripts-then-execute) defines narrow profiles for each source format, pre-export inspection, explicit transformation preconditions and a code coverage/order check. Unknown execution semantics are rejected. Plain scripts remain the working interface; notebook execution and cell markers are not required. |
| 2. Repair boundary | [Section 4](artifact-reproduction-draft.md#4-proposed-flow) freezes the source and untouched conversion, requires diffs with purposes, and distinguishes setup/export/packaging repairs from forbidden scientific changes. Following discussion with the user, v1 retains the source's original inputs and defers added reductions and new starting checkpoints. A candidate that exceeds the computation or resource limits is rejected. |
| 3. Endpoint completeness | [Section 2](artifact-reproduction-draft.md#2-what-counts-as-a-target) requires a separate GLM pass against the original source and scripts, with references for included endpoints and reasons for exclusions. The reviewed inventory is frozen before the final contract. This check reduces omission risk without claiming proof of completeness. |
| 4. Valid alternatives and grading | [Section 6](artifact-reproduction-draft.md#6-what-does-reproduce-mean) makes identity, missing-value, threshold and tie semantics public. Controls include missing-branch failures, consequential wrong results per branch, and independently computed conforming alternatives wherever numerical/software portability is claimed. Acceptance rules are frozen before blind solving. The user also agreed that plot endpoints use their underlying scientific data, with visual reproduction outside v1, and that valid-run variation requires a comparison validated against conforming results and meaningful mistakes. If any required endpoint lacks such a comparison, reject the notebook for v1 and preserve the reason. |
| 5. Timing and finite budgets | [Section 5](artifact-reproduction-draft.md#5-test-resource-fit-in-daytona-with-minimal-instrumentation) defines separate computation and solver clocks and finite setup, verification, repair, request and total-work budgets. Following discussion with the user, the five-minute reference proposal was replaced by a ten-minute computation limit. Total agent time remains a separate decision, with the current ten-minute allowance provisional; headroom for near-limit computations is still to be resolved before interpreting solver performance. |

These revisions make the design choices explicit; the final solver-time
allowance remains open. They have not been implemented, executed or independently
re-reviewed. No pipeline run, prompt change, viewer update or publication was
performed as part of these revisions.
