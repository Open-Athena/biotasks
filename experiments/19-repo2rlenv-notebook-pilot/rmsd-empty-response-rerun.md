# MDAnalysis rerun after empty-response recovery

The user requested a general retry for the malformed empty response that stopped
MDAnalysis attempt 015, followed by a fresh rerun. Preserve `autonomous-runs/015`
unchanged, including the original provider response and retrieval hash.

The generic artifact adapter now supports one explicit empty-response retry per
stage instance. It applies only after a received, otherwise complete assistant
response has no visible text, no tool calls or legacy function call, and no
refusal. The raw response and consumed request slot remain recorded. A canonical
notice asks the worker to continue from its existing conversation, retaining all
completed actions and feedback. The invalid assistant message is not sent back
as a tool call. The retry does not reset the deadline, turn/request allowance,
workspace or evidence. A second empty response remains a failure; partial calls,
refusals, filtered/length-limited responses and uncertain transport do not enter
this recovery path. Existing separately recorded context/output recovery is
unchanged. A one-call stage still has no spare turn for a retry.

The recovery notice is `src/biotasks/prompts/worker-empty-response-retry.md`; its
hash is part of the stage identity. Focused adapter, stage, setup and orchestration
checks pass (82 tests). No notebook-specific recovery rule or scientific edit is
introduced.

Attempt `autonomous-rmsd-017` starts from the same original pinned notebook using
`autonomous-cases/mdanalysis-rmsd/retry-config.json`; it reuses no generated task,
preparation, reference output or solver attempt. Keep the source-code-repair
rejection policy and existing 4 CPU/8 GiB/10 GiB, CPU-only, offline scientific
execution and ten-minute reference/solver settings. Campaign time remains two
hours plus cleanup; reserve $5 within the standing $100 aggregate authorization.
The ledger retains $1 each for the two completed additional examples, releases
$8 of conservative holds, and reserves $5 for this run (aggregate holds $97).
These are resource-based reservations, not provider invoices or a free-credit
assumption. New outcomes remain separate from both first attempts.
