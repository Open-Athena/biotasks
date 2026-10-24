# Verifier cancellation and log integrity

## 2026-10-24: source-first question

Filed as an actual child of #33 after #40 reverified four historical VerifierTimeoutError trials with no reward and NUL holes in saved logs. Their cause is unproven. Start from recorded main 2a1950d2, inspect the exact pinned Harbor 0.6.6 package/source and cancellation/retry/log-copy boundaries before designing a bounded infrastructure-only fixture. No #41 runtime, reservation or model calls occurred. #40 public archival and local cleanup are complete. Original task settings remain unchanged.

## 2026-10-24: pinned source and fake-process checks

Acquired the exact previously pinned Harbor 0.6.6 wheel (SHA 30477bf6, 1,120,578 bytes), read 203 source/metadata/license files without installing/executing the package. Source shows an outer verifier wait_for, no inner Docker exec timeout argument, a helper that catches its internal TimeoutError but lacks cancellation/finally cleanup, two verifier attempts in the same environment, truncating output redirection and environment teardown at trial finalization.

Three checks execute unchanged selected native AST functions under fake process transport: outer cancellation calls neither terminate nor kill; the helper’s own timeout calls terminate; native retry makes two verifier calls without process termination in that fake transport. These are Python control-flow findings, not real Docker/daemon survival or proof of the historical hole cause. The exact Tenacity 9.2.1 version was verified from #39’s original freeze and staged privately for the checks; no global/project environment or original task dependency was changed. The first local check stopped because Tenacity was absent; its resource record/preparation note remain.

The two-case native fixture design is recorded in runtime-design.md. No fixture generation, Iris admission/submission or model calls occurred. Source/wheel/check-dependency copies stay under inputs-private until source/runtime archival and verified cleanup; no /tmp paths are used.

## 2026-10-24: compiled native fixture and preflight checks

Generated two self-authored fixture tasks and a fixed-handle diagnostic payload. Native Harbor 0.6.6 and Tenacity 9.2.1 remain unchanged; both fixture deadlines are five seconds, with finite two-second and timeout thirty-second writers. No original task or biological score is involved. The writer records append-only PID/start-time/inode/offset events and in-container hole samples, so the probe can distinguish container behavior from later copying.

Four preflight checks passed: real finite local writer/event/inode integrity; false-positive boundaries for PID reuse/zombies/inode/offset; exact source-owned NUL publication paths/content; frozen resource/payload contract. This is not native Docker evidence. The full check is lightweight (small sleeping writer, approximately 20 KiB output, tiny classifier checks and payload hashes); its footprint is recorded. An initial nonblocking heavy-lock attempt returned busy; actual footprint classification allowed the unchanged small check to proceed without serializing lightweight work.

Before any effect, the unsubmitted payload was recompiled to isolate metadata-only build context and protect the shared public parent: one stopped owned reference container is never started, and owned image removal disables parent pruning. The public base is checked before/after; the guard is removed with other owned controllers. The public policy permits NULs only in the exact source-owned synthetic writer-log path with tightly validated ASCII-token content. All other binary/secret guards stay active.

No admission or remote submission yet. The eight-stage outer controller is reused with a diagnostic readback/publisher; native process outcomes are unproven until one bounded reserved-worker run.

## 2026-10-24: startup failure preserved; adapter-only correction

The first managed attempt biotasks41-cancel-07c39c2ac6 failed in the inherited supervisor constructor: its generic task-status initialization expected `tasks`, whereas this diagnostic config has `cases`. The exact SDK traceback and payload show failure before execute/validate/work, so no nested Docker objects or native fixture ran. Empty output alone is not the no-creation proof. The original journal remains incomplete; its explicit fallback disposition is archived, rather than fabricating successful normal stages. The attempt used 0.004358888864517212 allocated CPU-hours, now reconciled; unused cleanup reservation released with source-bound proof.

Failed-startup archive c6456193dfee27a7e18f6c985879e5639e62be8d83bd1da7ea997f59face622d has three objects, all anonymously read back with exact bytes/hashes. See runs/failed-startup-1 for manifest, receipt, disposition and original controller state. Package binaries are excluded; acquisition identities remain. Original local state/payload moved under private/failed-attempt-1, not overwritten or resumed.

The diagnostic constructor now supplies an empty generic task-status list and removes that unused report field. Native Harbor, finite/timeout writer settings and resource limits remain unchanged. A fifth preflight check instantiates the actual Diagnostic with the compiled config and verifies no filesystem side effects or config mutation. All five checks pass (2.15 seconds, 0.13 CPU-seconds, 24,896 KiB RSS; lightweight). The corrected fixed handle is biotasks41-cancel-e206de2c48. Its maximum main allowance is 0.9956411111354828 CPU-hours, the remainder of the original one-hour total; the timeout is shortened accordingly. No new monetary allowance, model call, task repair or capacity.

## 2026-10-24: native Compose fixture rejection preserved

The corrected constructor reached native Harbor and verified all 203 pinned source files plus Tenacity 9.2.1. Docker Compose rejected our unnecessary `build: null` override (`services.main.build must be a string`) during environment startup. Neither writer ran; the timeout case was correctly skipped after the finite prerequisite failed. This is a fixture configuration failure, not negative cancellation evidence. Its 14-object runtime snapshot 8ce7ed30f3abc57ab536b9bf5d4896ec664f470b6096bc3108889c90c6f49ec9 has verified anonymous readback; owned cleanup is empty and shared public base unchanged. All eight controller stages completed, and a completed reinvocation left 14 stage/budget files unchanged. runs/compose-failure-1 preserves this distinct result, input plan, policy and lifecycle.

Removed only our null build field: upstream's prebuilt Compose file already has no build field. Native Harbor/dependencies, writer code/durations, verifier deadlines and resource limits remain unchanged. The fixed-handle seed now also hashes the compiler so future template changes are explicitly bound. Five checks pass, including parsed Compose absence of a build override. New fixture handle biotasks41-cancel-9789693f9b receives only 0.9394044444296095 main CPU-hours; all prior actuals sum to 0.06059555557039049. No additional monetary allowance, models, task repairs or capacity.

## 2026-10-24: native component observations, original conjunction retained

The final fixture run verified all 203 native Harbor source files, Tenacity 9.2.1, unchanged input files and independent task-container limits (1 CPU, 6 GiB, no network). Finite writer passed with one start/end, fixture reward 0 and no NULs. The timeout trial returned VerifierTimeoutError with no reward and two writer starts/no natural ends. At retry start (5.859766 seconds), the first PID was alive in S state with matching start ticks and the same log inode; its descriptor offset was 60,416 while the new descriptor reset to zero. Eleven in-container samples measured NUL holes (peak 59,392 bytes, first 5.906751 / last 10.912932 seconds). The final saved log contains zero NULs. The fixed-record offsets are consistent with the new writer eventually filling the initial gap.

The predeclared full-mechanism conjunction requires final raw NULs, so it remains false. Post-run component-observations.json separately records measured survival/transient holes without changing that criterion or claiming historical Scanpy causation. This is neither negative survival evidence nor reproduction of persistent saved holes. Raw final bytes, ordered events and sampled intermediate counts/hashes are preserved; full intermediate byte snapshots were not captured.

The final main attempt used 0.07706388884120517 CPU-hours; all three managed attempts sum to 0.13765944441159567 / 1 CPU-hour. Native lifecycle, anonymous runtime HF readback and owned cleanup are complete; the shared public base is preserved. No emergency cleanup, models, biological control reruns, new task exports or paid capacity. Summary/source archival and local duplicate cleanup remain to finish.

## 2026-10-24: final preservation and cleanup complete

Final summary/source snapshot d559744f8cd8db8c6dc3d298b8d05896ac5c6167a894d8bac85dfbfcedf9eb78 has three objects/95 members, all verified by anonymous readback. Removed 6,941,023 owned duplicate bytes only after archive/public acquisition gates, including extracted package sources and prior attempt payload copies. Canonical runtime/startup/final archives and exact final compiled payload remain with explicit retention/cleanup conditions. No task-owned /tmp paths, remote resources or transfer caches remain. Completed invocation after cleanup left all fourteen stage/budget files unchanged and submitted nothing. All #41 preservation gates are complete; issue remains open for review, historical causation unproven.
