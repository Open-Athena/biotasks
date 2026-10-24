# Verifier cancellation and log integrity

## 2026-10-24: source-first question

Filed as an actual child of #33 after #40 reverified four historical VerifierTimeoutError trials with no reward and NUL holes in saved logs. Their cause is unproven. Start from recorded main 2a1950d2, inspect the exact pinned Harbor 0.6.6 package/source and cancellation/retry/log-copy boundaries before designing a bounded infrastructure-only fixture. No #41 runtime, reservation or model calls occurred. #40 public archival and local cleanup are complete. Original task settings remain unchanged.

## 2026-10-24: pinned source and fake-process checks

Acquired the exact previously pinned Harbor 0.6.6 wheel (SHA 30477bf6, 1,120,578 bytes), read 203 source/metadata/license files without installing/executing the package. Source shows an outer verifier wait_for, no inner Docker exec timeout argument, a helper that catches its internal TimeoutError but lacks cancellation/finally cleanup, two verifier attempts in the same environment, truncating output redirection and environment teardown at trial finalization.

Three checks execute unchanged selected native AST functions under fake process transport: outer cancellation calls neither terminate nor kill; the helper’s own timeout calls terminate; native retry makes two verifier calls without process termination in that fake transport. These are Python control-flow findings, not real Docker/daemon survival or proof of the historical hole cause. The exact Tenacity 9.2.1 version was verified from #39’s original freeze and staged privately for the checks; no global/project environment or original task dependency was changed. The first local check stopped because Tenacity was absent; its resource record/preparation note remain.

The two-case native fixture design is recorded in runtime-design.md. No fixture generation, Iris admission/submission or model calls occurred. Source/wheel/check-dependency copies stay under inputs-private until source/runtime archival and verified cleanup; no /tmp paths are used.
