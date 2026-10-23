Can timeout and scheduling changes recover complete positive control pairs without repairing tasks? Follow-up to #28.

**Current findings:** The input inventory is complete: 14 original controls were unstarted. Fresh paired comparisons require 20 commands across nine existing exports: 16 Matchms/OHIF scheduling controls and four Scanpy timeout-arm controls. Task and reconstruction member hashes are recorded. No tasks have been regenerated or executed.

**Remaining work:** Next: inspect saved reconstruction recipes and runner timeout-override support, then checkpoint a bounded live comparison. Proposed first stage is $0 model calls and at most 32 allocated CPU-hours on existing reserved capacity; it has not been submitted. OpenMS checkout and MMseqs2 bootstrap comparisons remain separate later arms.

**Boundaries:** original baselines remain immutable; use only justified general changes and upstream’s built-in model calls, with no added per-task LLM/Codex repair loop. No remote/native jobs or model calls have been launched in this follow-up. Execution requires a checkpointed cumulative allowance; #28’s unused ceiling is not a fresh budget. A mechanism test does not establish task recovery or production readiness.

[Evidence](https://github.com/Open-Athena/biotasks/blob/3588e2b6123b87f58ff3c41a50fe562815160723/experiments/29-runtime-limits/plan.md) · [Full comparison scope and success criteria](https://github.com/Open-Athena/biotasks/blob/3588e2b6123b87f58ff3c41a50fe562815160723/experiments/29-runtime-limits/issue-scope.md) · [Logbook](https://github.com/Open-Athena/biotasks/blob/3588e2b6123b87f58ff3c41a50fe562815160723/experiments/29-runtime-limits/logbook.md). Detailed investigation updates are in comments.
