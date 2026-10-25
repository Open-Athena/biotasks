# Completed resource bounds with handled solver timeouts

The original strict auditor is unchanged. This companion changes only its requirement for an exception-free native outcome: it also accepts a completed, dispatched solver wrapper with return code zero, retries explicitly zero and a 600-second `AgentTimeoutError` verified against the original hash-matched Harbor result. Other exception types, non-solver errors, incomplete processes, enabled retries and mismatched original results are refused.

Every original constraint on completed serial stages, native intervals, exact resources, original archive/root readback, original/fresh seven-owner cleanup and pinned no-snapshot Harbor backend is retained. The conservative bound is unchanged: price two complete resource profiles for the full approved 7,500 seconds ($1.384500), retain $2. This is resource exposure bookkeeping, not a successful solver result, scientific approval, actual invoice or assumed free credits.

Six unit tests exercise the additional gate and refusals. [Exact code delta](profile-delta.diff) and [static validation](static-validation.json) are preserved. The original strict profile remains available; any live ledger reconciliation needs the complete original evidence and fresh cleanup proof. No model or sandbox was launched to develop this helper.
