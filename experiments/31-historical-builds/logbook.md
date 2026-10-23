# Issue 31: historical-builds

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — verified archive and syntax findings

Restored1,746,306bytes anonymously with original SHA256 verified; removed owned Xet cache. Checkpoint `b9056df3` syntax-only inspection completed in0.10seconds/21,128KiB under the shared heavy lock. Seven original extension-removal pairs reproduced from retained logs; three saved Dockerfile RUN bodies fail bash syntax checks. Saved reconstruction and historical rebuild are separate prerequisites. No recipe/test/container/model executed; exact findings in `lifecycle-findings.json` and `findings.md`.

## 2026-10-23 — compiled mechanism fixture

Added and ran a synthetic shared-library comparison through exact pinned native/export shell builders. Twelve cases cover missing binaries, correct-revision rebuilds, stale-binary false positives and fail-closed multiline rebuild failure. Original source hashes are verified; only filesystem roots are remapped. No environment recipe or biological source was repaired. All assertions passed and owned temporary files were removed. This supports a generic lifecycle hook investigation but is not an integrated candidate, graded-verifier check or live MACS recovery. Next: wire an opt-in hook through validation and export with explicit failure guards, then select one immutable original removal case and establish a declared baseline reconstruction procedure.

## 2026-10-23 — opt-in candidate wiring

Added reproducible candidate patch with `replay_bootstrap_rebuild=False` by default. Enabled mode uses recorded bootstrap commands for native stages and exported verification; empty command records are rejected and exported metadata records the procedure. Native setup is fail-closed and completion markers/exit status are checked before parsing. Export begins rebuild with a zero reward so timeout cannot inherit a prior success.

First fixture execution caught an incorrect clean-command list index (IndexError before rebuild); corrected index 5 to 4 and retained failed resource record. Candidate then passed all 12 compiled cases, including unchanged default script equality, revision-specific binaries, stale-binary negative controls and multiline build failure. AST parsing and patch applicability checks pass. These checks do not execute full pipeline wiring. Exported reset handling still inherits permissive upstream behavior; graded-parser and full native-outcome checks remain prerequisites. No biological repairs, model calls or remote execution.

## 2026-10-23 — graded export and guarded reset

Executed the unchanged hash-verified upstream graded verifier on real unittest output from synthetic compiled code. Seven cases pass: nop, oracle, rebuild failure clearing old success, tracked success with nonzero overall command, invalid base, legitimately new test file replacing stale contents, and an obstructing directory at the new test path. Candidate initializes a zero verdict before setup and distinguishes missing test paths from Git errors. Native/export 12-case compiled check also passes after this change. No Docker, Harbor, model or biological repository execution. Full native outcome/configuration and live MACS comparison remain.

### Complete native outcomes and package integration

Six cases pass through the complete imported native validator and original parser dispatcher using an actual C/unittest fixture: unchanged upstream, disabled candidate, successful rebuild, pre-build failure, post-build failure and invalid test patch. Enabled rebuilding yields the exact expected F2P/P2P pair; failures stop before the affected test stage. Disabled outcomes and executed commands match upstream. The local adapter remaps `/workspace` and uses Bash without Docker; no live recovery is claimed. PeakRSS21.8MiB,0.61seconds; owned temporary directory removed.

Acquired the full pinned source package, verifying all353selected files against Git blob identities (2.42MBsource;6.91MBarchive). Applied the research patch to a disposable complete copy. Actual CLI option parsing, config loading, registered pipeline construction, task building and Harbor writing pass for default/on/off; missing rebuild commands and unknown options are rejected. A Python audit guard blocked external operations; none were attempted. An isolated6,675-byte, hash-verified tomli-w1.2.0wheel supplies the writer dependency without changing a shared environment or biological runtime. Other dependency versions are recorded; Rich14.2.0is below upstream's declared15.0floor, so this is not full locked-environment qualification. PeakRSS49.5MiB,0.46seconds; temporary copy removed.

Frozen MACS792as the earliest retained batch with extension removal on both sides, binding original metadata and log members. Its unchanged saved recipe has three default-shell syntax failures (also previously seen in Bash); deleted original image unavailable. No reconstruction command, dependency or PR input was repaired. This prerequisite prevents a live original/candidate MACS comparison under the current approach; the local mechanism evidence remains separate.

### 2026-10-23 — Checkpoint recorded MACS bootstrap replay

The same generic recorded-action method completed Scanpy's original command sequence in #29 without command repair. Prepared it for the original MACS archive/payload, with all 16 BASH actions including three expected syntax-error exits. Verified the source phase SHA and retained the frozen PR792 selection. This restores session continuation semantics without changing a repository command, dependency or test. The baseline image remains unproven until live replay and archived readback; no PR792 result is inferred. The first remote stage is bounded at 16 allocated CPU-hours with zero model calls, with at most eight hours for this first replay. See `macs-replay-protocol.md` for exact resources and ownership cleanup.

Submitted `biotasks31-macs-recorded-001` from checkpoint `5f3c2945` on existing reserved worker `marin-tpu-v4-reserved-32-us-central2-b-20261023-1755-6e8581d8-worker-1` (base `c7c14a252d`). No model calls; the original-versus-rebuild PR792 comparison has not started. Scope published and exact body/comment verified at https://github.com/Open-Athena/biotasks/issues/31#issuecomment-6372915293. The job handle, original input hashes and image-retention obligation are recorded in the handoff.

### 2026-10-23 — MACS actions replay; post-agent smoke times out

The first replay is terminal FAILED after847.296seconds (0.9414400000042386 allocated CPU-hours). All16 original BASH actions matched their exits, including the three syntax failures. The next original full-suite smoke command then reached its300-second timeout; the timeout guard refused the subsequent Git check and removed the sandbox. The command identity is independently verified from the archived Docker-run container ID and full smoke-call hash. Thus no image commit/fresh verification or PR792 validation occurred.

Partial smoke output reached86% progress, with the pinned parser finding4,333PASSED and249SKIPPED statuses; these are incomplete diagnostic counts, not a valid task or complete suite result. Archive85f12824ce8b008993685119be42bef5e7b647563964815aaf6e296119404b54 (56,528bytes) and every recorded output hash are verified. All owned containers/images and clone/tools are absent. No model calls or repairs. A distinct, checkpointed longer post-bootstrap smoke/fresh allowance can test this new timing barrier while keeping actions/source/test command/CPU/memory fixed; it is not silently applied to the failed run.

Published the verified smoke-timeout outcome and complete cleanup at https://github.com/Open-Athena/biotasks/issues/31#issuecomment-6373255554. Exact current body/comment, OPEN state and agent-generated label were read back and verified. The longer post-bootstrap allowance is a proposed separate comparison, not an alteration or retry of this evidence.
