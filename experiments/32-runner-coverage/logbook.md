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

### 2026-10-23 — Audit targeting grammar before MNE intervention

Executed the pinned selector on eight bounded command-string cases without running generated shell. It preserves broad mne/ scope, mistakes option path values for targets, misses dot scope, and appends paths to later echo/tee commands. Recorded exact source hash and input/output strings in pytest-targeting-audit.json. targeting-design.md defines an explicit changed-files comparison with conservative syntax support and separate reporting of reduced regression coverage. No task command, dependency or original result changed; no remote job or model call.

### 2026-10-23 — Standalone conservative pytest targeting candidate

Implemented a separate opt-in literal-command selector; 26 bounded checks pass, including exact default-off command preservation and the recorded MNE command shape. Selected outcomes declare reduced scope, explicit file/node targets are retained, and ambiguous shell/unknown options fail as unsupported. No generated command was executed; no model calls or remote jobs. Pipeline configuration/native/export wiring and frozen biological comparison remain required.

### 2026-10-23 — Wire opt-in policy into pinned package

Generated a three-file integration patch: default-off option, shared native/export selector with deleted-path filtering, and literal policy helper. Enabled unsupported commands are skipped before sandbox allocation even with validation disabled; direct export construction fails explicitly. Complete-package config/writer checks pass for default/on/off. Actual run-loop routing with controlled provider/sandbox/validator fixtures preserves selected native/export commands and cleanup; this is integration evidence, not native test outcomes. No external operations, models or remote jobs. PeakRSS49,676KiB, elapsed0.48s, temporary copy removed.

### 2026-10-23 — Freeze original MNE input and reconstruction barrier

Restored the public original phase (415,354bytes), verified its archive SHA and all170member hashes (813,564uncompressed bytes). Anonymous download used59,268KiB peakRSS; task-owned cache removed. A first local path-resolution error occurred before download and is retained separately. Selected PR14445as the earliest original validation ordinal, extracting source/test patches from the original saved shell scripts. Both scripts regenerate byte-for-byte through pinned upstream; both original stages exited124at600seconds. No source fetch or original-log regrading.

The shared selector chooses the two surviving changed test files instead of mne/, explicitly reducing scope. Inspection also finds all12recorded bootstrap BASH actions contain Assistant: tails and exit127; original smoke/fresh flags werefalse. These exact commands are preserved in a private replay payload, not stripped or repaired. Matching exit127alone would not prove successful installation. A faithful executable reconstruction remains prerequisite to live selection/completion comparisons. No model calls or new remote jobs.

### 2026-10-23 — Checkpoint frozen MNE replay

Prepared the previously executed Scanpy recorded-action driver for frozen MNE inputs, with only identity/output changes and a shorter3,900-second work deadline. Syntax-check four entrypoints, verify the replay helper byte identity, and regenerate the original Dockerfile exactly from the unchanged12actions. Maximum5allocatedCPU-hours plus prior0.22337 fits #32ceiling10; no model calls or per-task repair. Original smoke/fresh semantics and300-second command limits remain fixed. Retention/cleanup obligations are in mne-replay-protocol.md. Submission is a separate stage.

Submitted biotasks32-mne-recorded-001 from661d4071on existing reserved worker marin-tpu-v4-reserved-64-us-central2-b-20261019-0055-7c2d425d-worker-1. Payload hashes match preflight; zero models/new capacity. Full5CPU-hour reservation remains under #32ceiling with prior actual usage. Results, archive readback and owned-resource cleanup are pending; do not resubmit this handle.

### 2026-10-23 — SAMtools composite runner and identity contract

Read pinned PR1605test.pl/Makefile through public GitHub API; retained hashes and files privately. Native result helpers/summary executed on four synthetic outcomes:pass/fail/xfail/xpass counts and exit1preserved. Source repeats function headings across commands/thread variants, while make test also runs C/shell components. Pinned upstream detects allfour relevant command forms asunknown. Report why recognition-only or heading-keyed parsing cannot establish task validity; define identity/completion/composite-coverage requirements. No full harness execution, source repair, models or remote jobs. Fixture elapsed0.10s,peak17,984KiB.

### 2026-10-23 — MNE replay reaches full-suite smoke timeout

One attempt is terminalFAILED after448.093seconds,0.497881111CPU-hours. All12original BASH actions matched their expected127exits without repairs. The next original full-suite smoke command timed out at300.011seconds; its exact Docker call identity is verified from the archived container ID and command hash. Partial progress reached28%, which is not a completed test result. The guard prevented commit/fresh verification while timed-out work could remain active, then removed allownedcontainers/images/tools/checkout. No PR14445validation or task export occurred.

Verified23,940-byte archive4f4bfd35428e998776d628d84fe5d345479888b8b32a508e8f800d5faece959dand allretainedoutputhashes. No image remains. #32cumulative two-job usage is0.7212466663784451allocatedCPU-hours under10,zero models. A longer post-bootstrap allowance is a possible separate timing comparison; it has not been applied to this result.

### 2026-10-23 — Checkpoint MNE post-check timeout comparison

Prepared a separate replay with only the exact upstream smoke/fresh invocations extended 300→1,200 seconds. All 12 original recorded actions and source inputs remain unchanged, including invalid `Assistant:` tails and exit 127. The original failure/partial smoke record remains intact. Seven pure routing checks pass, including original action/commit limits unchanged; five entrypoints syntax-check. Preflight finds the same reserved worker healthy. One attempt reserves 5 CPU-hours; 0.72125 prior measured usage plus 5 fits the 10-hour issue ceiling. No models/new capacity. Native PR validation still requires a usable retained image and a separate comparison.

Submitted `biotasks32-mne-longcheck-001` from `4b3bc656` to the original reserved worker; payload hashes match preflight. Results/archive/cleanup pending.

Prepared bounded MNE timing archive readback. It verifies downloaded archive identity, original actions, source/commit/base-image parity with the earlier replay, original versus applied post-check timeouts, raw command output hashes and cleanup report. No live result is inferred while the handle is running.

### 2026-10-23 — SAMtools original runner evidence

Anonymously downloaded the previously verified public #28 SAMtools phase archive (896,539 bytes, SHA256 `b4f08783faf68a2d11b91c89192d019928b9fb968b9ba8b3cb6dbf872d420675`) into ignored private experiment storage; its temporary HF Xet cache was removed after verification. The original bootstrap `make test` record at ref `d4fd5c9d` completed with exit0 in46.995s. It contains523 per-test heading occurrences but only29 names; `test_sort` appears36times. Perl summary reports1,052 total /1,020 passed /0 failed /32 expected failure /0 unexpected pass; other make components follow. The raw member hash and parsed counts are recorded in `samtools-native-log-audit.json`. This confirms actual heading collisions, but it is bootstrap smoke, not PR1605 validation or a task control. No new jobs/model calls.

### 2026-10-23 — MNE 1,200-second smoke comparison remains incomplete

The bounded MNE longcheck failed after 1,297.112 seconds (1.441236 allocated CPU-hours). All 12 original bootstrap actions again matched exit 127 without edits. The only changed call was the exact post-bootstrap full-suite smoke command `cd /workspace && python -m pytest -v mne/`, with its client timeout raised from 300 to 1,200 seconds; it still exited 124 after 1,200.007 seconds. Partial pytest output advanced from 28% in the prior arm to 61% here, then stopped during `test_concatenate_epochs`. Neither percentage is a completed smoke result. No image was committed, fresh-image check or PR14445 validation ran, and no task was exported. The invalid `Assistant:` command tails and exit 127 remain a separate setup-quality concern.

The 37,825-byte archive was downloaded and SHA256-verified (`e3f981702dcdbbe84258933b4d1c4d9e88a869c919d2a9b403bc780866c3d1e1`). Readback confirmed source/ref/base-image identity, all original action hashes/exits, the sole 300→1,200 smoke timeout change, raw output hashes, and absence of owned containers, images, checkout and tooling. The archive's result filename remained `mne-recorded-result.json`; the local readback helper was corrected to read that name without modifying or rerunning the remote job. Three terminal #32 remote jobs now total 2.162482 allocated CPU-hours under the 10-hour ceiling, with zero model calls or new capacity. This longer timeout improves partial progress but does not recover the official pipeline boundary.
