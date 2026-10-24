Add `biotasks validate plan/run/status` for existing Repo2RLEnv native-inline `pr_runtime` exports. Immutable plans bind task bytes/modes, execution settings and transport provenance; each PR has a fixed Iris job identity, cumulative CPU admission and recoverable journal. Verified archive readback gates exact-worker cleanup, while attempted empty outputs trigger stop-only retention for salvage.

The initial backend uses existing reserved Iris CPUs on POSIX/Linux x86-64, Harbor 0.6.6 and the original grading/timeouts. It supports serial native-inline validation, eligible local/HF evidence preservation and owned cleanup. Generation and recorded initializers remain separate; there are no model calls or task repairs. Public uploads require reviewed eligibility/notices and anonymous readback, and preserve shared public parent images during cleanup.

Validation:

- 41 offline tests cover installed worker resources and separate SDK dependency isolation, effect-boundary recovery, uncertain submissions, changed inputs, negative/empty outputs, partial public uploads, CPU budgets (including closing admission while reserved cleanup finishes), retention, archive bounds and prompt compatibility. Ruff lint/format, ty and hooks pass.
- Native Cobrapy #1482 reproduced nop 0/oracle 1 with a clean oracle command, including the final controller candidate. Scanpy #4389 reproduced its original apt prerequisite failure with controls unattempted. All ten task files/modes per reference remained unchanged; no environment repair was added.
- All three native workflows completed anonymous HF archival and empty owned-resource cleanup. Completed native reinvocations forbade transport and left 261 baseline / 143 final-run files and the budget unchanged. [Comparison, artifacts and limitations](https://github.com/Open-Athena/biotasks/blob/feedf6c1/experiments/44-validation-entrypoint/results.md).

The final host-only overrun path was verified with synthetic accounting; no overrun was induced on reserved workers.

Refs #44. The broader generation-to-validation handoff remains #45; these comparisons do not establish cohort portability, grader robustness or task-release readiness. Keep #33 and its research issues open for review.
