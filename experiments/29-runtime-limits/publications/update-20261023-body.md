Can timeout and scheduling changes recover complete positive control pairs without repairing tasks? Follow-up to #28.

**Current status:** Inputs are inventoried for 20 control commands across nine existing exports: 16 Matchms/OHIF scheduling controls and four Scanpy timeout-arm controls. The three saved reconstruction recipes pass syntax checks. Exact Harbor 0.6.6 source confirms that its verifier-only timeout multiplier can change 300 seconds to 1,200 seconds without editing task files. Neither check establishes a successful image build or recovered task.

**Next:** checkpoint and execute the controls-only runner. The proposed first stage uses existing reserved capacity, at most 32 allocated CPU-hours and no model calls; no jobs have been submitted. Original images were deleted, so reconstruction drift must remain explicit. OpenMS checkout and MMseqs2 bootstrap comparisons are later, separate arms.

**Boundaries:** preserve original task bytes and baselines; no per-task repairs or additional LLM repair loop. Record the runner's internal timeout retry in scheduling bounds. Execution requires a checkpointed cumulative allowance; #28's unused ceiling is not a fresh budget.

[Plan and verified prerequisites](https://github.com/Open-Athena/biotasks/blob/cb3e394aa11ff02c03649edb058d9184962bd1ab/experiments/29-runtime-limits/plan.md) · [Recipe checks](https://github.com/Open-Athena/biotasks/blob/cb3e394aa11ff02c03649edb058d9184962bd1ab/experiments/29-runtime-limits/reconstruction-findings.json) · [Comparison scope](https://github.com/Open-Athena/biotasks/blob/cb3e394aa11ff02c03649edb058d9184962bd1ab/experiments/29-runtime-limits/issue-scope.md). Detailed logs remain in comments and the linked research branch.
