# Issue 32: runner-coverage

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — parser fixtures and deterministic reject sample

Checkpoint `3ce0df02` parser comparison passes12expected-status fixtures plus two exact-source targeting checks in0.04seconds/20,244KiB. ANSI SGR stripping recovers synthetic colored statuses, but partial logs remain parseable and need an independent completion gate. No original task regrading. Sample frozen before acquisition: PR263,1605,371,250,1735,204. All six current public diffs acquired under2MiB cap; all still score zero with the pinned function recognizer. Four add net Perl test invocations. Original diff bytes were not retained, so current-source hashes and descriptor path agreement are reported rather than exact historical equality. Raw fixture-bearing diffs stay local; public findings contain paths/hashes/metadata only.

## 2026-10-23 — completion gate

Checkpoint `7e54cb90` runs seven synthetic sandbox-result cases through exact original/candidate native validation functions. The pinned validator accepts all seven; six contain nonzero execution or missing output markers. The candidate rejects those six and preserves the complete pair. Check completes in 0.04 seconds / 15,228 KiB. This confirms a control-flow mechanism, not an original task regrade; parser normalization must not be used alone to claim recovery from timed-out logs.

## 2026-10-23 — native/export parser parity

Extended the SGR candidate to the standalone exported pytest parser as a separate minimal patch. Leaving it native-only would allow discovery to recognize colored statuses while exported grading still misreads them. Verified exact upstream standalone source hash, and exercised all 12 expected-status cases in both native and exported parser variants. Plain-output baseline parity and colored candidate parity pass; no test IDs are renamed. Completion remains a separate gate and no historical task was regraded. Resources are recorded in `parser-export-resources.txt`; no model/remote calls or temporary inputs were needed.

### Cross-issue live targeting evidence

#30's frozen Matchms958 comparison removes transport errno7 but still collects zero tests. The test patch deletes two paths that the unchanged target selector passes to pytest. The exact diagnosis and log hashes are pinned at `4862b97e:experiments/30-script-transport/live-diagnosis.json`. No input was repaired and no extra #32 run was launched. Add this frozen case to the general diff-aware targeting comparison; do not infer recovery before execution. The issue body and marked comment were read back exactly after publication.

### General deleted-target candidate and frozen live checkpoint

Added a generic diff-metadata selector used only for native/export target commands. It leaves reset/inventory paths unchanged, does not inspect PR identity, and ignores deletion-like text inside hunks. Ten path fixtures, four runner fixtures and two frozen real-patch selection checks pass (21.6MiB peakRSS,0.05seconds; temporary directory removed). Same frozen Matchms958 now selects six surviving test files;671remains byte-identical in command selection.

Prepared a one-attempt paired comparison with stdin transport fixed in both arms, original parser/validator, same source/test patches and same reconstructed image. No command edit per PR, extra LLM call, dependency repair, parsing change or completion-gate candidate is applied. Full imports, eight frozen stage hashes and four new Bash syntax checks pass. Checkpoint/submit scope and cumulative10CPUhour ceiling are in protocol.md. No live recovery claim before outcome and independent-control evidence.

### Deleted-target live comparison completed

The one-attempt job succeeded in201.029seconds (0.2233656allocatedCPUhours), with zero model calls and verified owned-resource cleanup. The14,928-byte archive and all call hashes were read back privately. Original selection reproduces missing-file/zero-collection failures. Surviving-target selection removes that error, exposing `ModuleNotFoundError: chemap`: precollects0items/6errors and postcollects45items/5errors, both interrupted during collection. No tests are credited as passing merely because they were collected, and no task is recovered. PR671preserves exact native F2P/P2Psets(1/30). No dependency repair, parser/completion change or additional run was applied. Raw evidence is retained under ignored `inputs-private/live-001`; remote archive TTL7days. `target-live-diagnosis.json` binds the conclusion to output hashes.

### 2026-10-23 — Actual shell execution exposes inner-exit gap

Five actual Bash/Git fixture cases show that both the original validator and outer-completion candidate accept synthetic F2P/P2P output when the test command exits 2, 124 or 137. The final marker echo masks that inner status as outer exit0. Earlier scripted-sandbox checks only exercised nonzero outer exits/missing markers and remain valid within that scope; they do not prove runner completion. No original task or reward was regraded. `inner-exit-results.json` and `inner-exit-diagnosis.md` preserve this counterexample. The temporary fixture was removed; no remote job/model call. The completion candidate is explicitly not ready for a live acceptance claim until inner status and setup failure handling are addressed consistently with exported grading.

### 2026-10-23 — Strict pytest completion and export reward checks

Prepared a separate combined candidate for explicit pytest commands: fail-closed native setup, preserved inner test status with newline-safe ordered markers, SGR parsing, and zero exported reward on incomplete pytest exits. Ordinary pytest exit1 remains valid for expected pre-fix failures. Non-pytest commands are explicitly skipped by this experimental strict gate; broader runner support remains unresolved, not silently claimed.

Six real pytest/Bash/Git native fixture cases and five standalone-export cases pass. The expected complete pair keeps1F2P/2P2P and nop/oracle0/1. Interrupted, explicit-exit124 and SIGKILL logs receive0 rather than the prior SGR-only grader's0.5; no original task reward is changed. Five protocol-malformation cases and explicit unsupported-runner behavior also pass. Initial harness global-Git-config failure and candidate missing-newline failure are recorded separately; the final harness uses an isolated temporary Git config and the candidate guarantees marker separation. Final runtime2.46seconds, peakRSS43,824KiB, no model/network/remote work; temporary directories removed. Live biological comparison still remains.

Published the outer-only counterexample, revised pytest-specific candidate, actual-shell/export checks and remaining limits at https://github.com/Open-Athena/biotasks/issues/32#issuecomment-6373173844. Exact body/comment readback and OPEN state/label are verified. Earlier completion evidence is retained and explicitly qualified; no original task reward was regraded.
