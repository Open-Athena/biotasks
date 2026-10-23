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

### 2026-10-23 — Checkpoint longer post-bootstrap checks

Prepared a distinct MACS arm with smoke/fresh-image allowances 300→1,200 seconds only. All recorded actions, commands, input/source hashes and CPU/memory remain fixed. A phase/operation/exact-command routing helper passes seven checks and logs upstream/applied limits. The complete driver diff is retained. The first sandbox was removed, so this arm must replay the immutable actions again; it is not a model or task regeneration. One attempt is capped at10CPU-hours, with baseline0.94144 included under #31's16-hour ceiling. No model calls or new capacity. See `macs-longcheck-protocol.md`; submission and outcomes remain separate stages.

Submitted `biotasks31-macs-longcheck-001` from `01108ef0` on existing reserved capacity. Payload hashes match preflight; one attempt, no model calls, no new capacity. The separate ten-CPU-hour reservation plus measured baseline remains below the sixteen-hour ceiling. Collect this handle rather than resubmitting; archive verification and any retained-image cleanup remain outstanding.

### 2026-10-23 — Longer MACS post-bootstrap checks complete

The distinct timing arm succeeded in1,402.477seconds,1.558307778allocatedCPU-hours. All16recorded actions matched; only smoke/fresh check limits changed300→1200. Both checks exited0after414.48/431.94seconds (Docker wall time), each with4,924passed/348skipped. Input payload and actual base-image ID match the failed300-second arm; mutable installed dependencies remain a reconstruction caveat. This establishes a usable reconstructed current-ref image, not PR792validity.

Verified64,572-byte archivef9f94f9de6eb3d71fd8ded2fe55b600fe45d653878b5c5b450d65db5b1fad1fcand recordedoutputhashes. Ownedcontainers/tools/checkout are removed. Imagesha256:979804eec3d64fffcff3cabf5eda15b04c6a4e1143051bf024ff66ac05312797remains on the submitted worker solely for the frozen original-versus-rebuild comparison, then must be removed. Total #31usage2.499747777779897CPU-hours under16,zero models. Original failed replay remains immutable.

### 2026-10-23 — Freeze MACS native comparison inputs

Extracted PR792source/test patches from the exact original archived stage commands. Both original stages regenerate byte-for-byte, and candidate default-off matches. Enabled stages differ only through the declared rebuild insertion, preserving literal recorded rebuild commands. Original postscript78,455bytes and enabled78,768remain below128KiB, so transport stays unchanged. Freeze selected eighttestpaths,originalparser and600-second stage budget; do not combine #32interventions. Prepared atmost10CPU-hour live reservation under #31remaining budget; no job submitted yet. Native harness, archive/readback and subsequent controls remain required.

### 2026-10-23 — Checkpoint native MACS comparison driver

Implemented actual original/candidate validate_pr execution with unchanged argv transport, parsers, eight test paths and 600-second stage timeout. Separate 1.5-CPU/6-GiB containers share the verified reconstructed image. Four scripts regenerate exactly, default-off parity and source hashes verify; four no-Docker guard fixtures cover ordinary failure, client timeout, insufficient allowance and changed-stage rejection. Fixtures were removed. A full 3,600-second arm allowance must fit before starting; per-operation deadline checks preserve original timeouts. Ownership cleanup is independent of the deadline and retains only the original reconstruction image pending archive readback. Preflight confirmed headroom on the same reserved worker. Maximum 10 CPU-hours plus prior 2.49975 fits the 16-hour ceiling. No model calls or new capacity. Native outcomes remain pending.

Submitted `biotasks31-macs-native-001` from `52f57a92` on the original retained-image worker. Payload matches preflight. Results, archive readback and comparison-container cleanup pending; original reconstruction image remains retained.

Prepared bounded native-comparison archive readback. It verifies the Iris archive digest/size, each extracted member, reported output hashes, frozen stage command hashes and 600-second limits, native outcome records when present, and cleanup claims. Raw logs stay private; no result or success is inferred before the live job reaches terminal state.

### 2026-10-23 — MACS PR792 native comparison terminal

One successful Iris attempt used0.716219 CPU-hours. Verified 16,173-byte archive SHA256 `a049a6b75afeab4a4507836b9e7ac5ee5691fa386f374044e0605c2b095d1409`; both separate containers and tools are removed, no cleanup errors. Original pre/post each have3 pytest collection errors involving `__spec__`. Rebuild pre has one collection error: missing `MACS3.Signal.CallerExecution`, which the PR source patch adds and its frozen test patch imports. Rebuild post collects and passes364 tests with29 skipped. Both validators return failed,0 F2P,0 P2P; no positive task or export controls. Upstream outer stage exit0 masks inner collection failure. No command repair or regrading. The reconstruction image remains for explicit cleanup; cumulative allocation3.215967 CPU-hours, zero model calls.

Prepared a cleanup-only job for the original MACS reconstruction image. It gates on terminal native comparison, verified archive readback, no positive F2P, no exported controls, and exact image tag/ID/owner on the original worker. Only labeled images are eligible and any container using the image blocks removal. Syntax checks pass; submission and remote cleanup are still pending.
