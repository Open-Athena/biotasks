# Verifier cancellation and log integrity

## 2026-10-24: source-first question

Filed as an actual child of #33 after #40 reverified four historical VerifierTimeoutError trials with no reward and NUL holes in saved logs. Their cause is unproven. Start from recorded main 2a1950d2, inspect the exact pinned Harbor 0.6.6 package/source and cancellation/retry/log-copy boundaries before designing a bounded infrastructure-only fixture. No #41 runtime, reservation or model calls occurred. #40 public archival and local cleanup are complete. Original task settings remain unchanged.
