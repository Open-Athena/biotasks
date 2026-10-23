# Issue 29: runtime-limits

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — control inventory

Derived all14unstarted commands and all original task/reconstruction member hashes from #28. Eight affected Matchms/OHIF exports require16commands for fresh paired results on reconstructed images; Scanpy's two timeout arms add4commands. Proposed first stage is20commands/$0model, at most32allocatedCPUh on existing reserved capacity, not submitted. Baseline image reconstruction must be inspected before claiming a pure timeout comparison. `control-plan.json` records exact inputs and `plan.md` distinguishes scheduling from timeout recovery.

## 2026-10-23 — reconstruction preflight

Verified the original bootstrap metadata for all three control repositories against original phase/member hashes. Matchms originals were read in place; only bootstrap metadata was copied locally, with no upload. OHIF/Scanpy public originals were restored anonymously; owned Xet cache removed. Syntax-only checks pass all 4/18/16 RUN bodies respectively, in 0.08 seconds / 18,496 KiB. This removes the specific MACS-style shell-syntax prerequisite for these three recipes, but does not establish build success or dependency/image reproducibility. No control or recipe executed.

## 2026-10-23 — exact Harbor override source

Read the historical Harbor0.6.6 wheel from PyPI, verified its published SHA256/1,120,578bytes and retained selected source/license. No installation/import. Verified the CLI verifier-only multiplier and effective timeout formula: multiplier4 turns original300seconds into1,200without changing task bytes or other stage limits. This resolves the override-support prerequisite; execution and complete controls remain outstanding.

## 2026-10-23 — selected control inputs and runner

Verified/extracted 90 original files for nine exports, then generated all 20 control commands without execution. Added explicit per-trial admission, 300-second cleanup reserve, task hash/mode checks, fresh output directories, original Harbor version requirement, and stop-on-wrapper-timeout behavior. Execution still requires an owning bounded supervisor, image reconstruction and archive/cleanup implementation. No model calls or remote jobs.

Read-only transcript alignment found Scanpy's original failed pip command retained in its saved Dockerfile. Recorded its original exit status and archive/member hashes. This makes a syntax-clean recipe insufficient evidence for executable reconstruction. No failed recipe command has been changed.

## 2026-10-23 — original Matchms reconstruction submitted

Submitted `/exedev/biotasks29-matchms-reconstruct-001` once on existing reserved TRC worker capacity. Four allocated CPUs, 16 GiB RAM/disk, 2,400-second maximum, zero retries/model calls/project credentials. Maximum 2.667 allocated CPU-hours is part of the first-stage 32 CPU-hour bound. Exact source/payload/worker checkpoint is in `reconstruction-submission.json`.

Original recipe receives an ownership LABEL immediately after FROM; all base/COPY/RUN bytes remain unchanged. Build resources are 1.5 CPU/6 GiB with 1,800-second deadline. An owned successful image is retained on the recorded worker for subsequent controls, with explicit removal after controls/archive or investigation termination. No control execution is part of this job. Initial local preflight failed before connection because the private output parent was absent; fixed directory creation and repeated read-only preflight before the sole submission.

## 2026-10-23 — reconstructed image verified; controls submitted

Original Matchms recipe completed successfully in one attempt, consuming 0.12724778 allocated CPU-hours. Downloaded and SHA-verified its 4,967-byte Iris output archive to ignored durable private storage. Build log records successful installation and 1,446 collected tests; this is not a task-validity result. No build containers remain. The uniquely labeled reconstructed image/cache stays on the recorded worker for controls and must be removed after control archive readback.

Submitted `/exedev/biotasks29-matchms-controls-001` once on that same worker, with the frozen eight-control schedule and unchanged 40 task files. Four allocated CPUs/16 GiB, 8,700 seconds maximum, no retries/model calls/credentials. The 9.667 CPU-hour maximum plus measured reconstruction remains within the 32 CPU-hour first-stage bound. Exact payload and checkpoint are recorded in `controls-submission.json`. No outcome is claimed until terminal archive/control records are read back.

## 2026-10-23 — live control progress and monitoring

Read-only controller inspection observed Matchms671 nop completing with reward 0, target 0/1 and regression tests 30/30, with no Harbor exception; oracle was running. This is provisional live evidence, not an archived pair. A later log-service request failed transiently; the observer now reports authoritative job state independently of log transport. Same handle remained running at 17:41:21Z; no restart or additional submission.

## 2026-10-23 — all Matchms pairs archived; cleanup verified

All eight original controls completed: four nop=0/oracle=1 pairs, four clean oracle commands and preserved regression tests on both sides. Verified the complete uploaded archive SHA, every recorded output hash and all 40 original task-file hashes. Raw archives are retained under ignored `inputs-private/controls-001`; the remote Iris archive has a seven-day TTL. Summary reads original rewards without regrading.

Control job cleanup removed its containers, labeled task images and shared volume. The subsequent one-attempt cleanup job removed remaining images carrying the reconstruction owner label, including inherited build intermediates, and verified both image/container lists empty. Tools were removed. No reconstruction image is retained. No active job remains; record final cumulative CPU accounting including cleanup separately.

## 2026-10-23 — OHIF context omission

One unchanged OHIF reconstruction attempt returned Docker exit 0 (0.12388112 allocated CPU-hours), but verified logs show frozen-lockfile installation failure and missing Jest environment/zero listed tests. Exact pinned source readback confirms root `.dockerignore` excludes `platform/docs/`, while that workspace's package.json exists in Git. Original bootstrap uses docker cp rather than filtered Docker build context. No controls were launched on this unusable image and no lockfile/package repair was made. Submitted one scoped cleanup job for its owned image/cache; follow its original handle and record terminal removal/accounting.

OHIF cleanup completed in its sole attempt; `ohif-cleanup-result-001.json` verifies no reconstruction-owned images or containers remain and tools were removed. All five submitted #29 jobs are terminal; cumulative accounting is updated. Next investigate full-checkout context fidelity as a generic infrastructure comparison, not lockfile/dependency edits.

### Scanpy unchanged-recipe build checkpoint

Prepared one reconstruction attempt for the saved Scanpy903925920218f829f3cad4f9f4730c086267ee53record. The original failed system-pip RUN remains intact; no skip, dependency repair, retry or model call is added. Use the same bounded reconstruction procedure (ownership label only, build1.5CPU/6GiB/1,800seconds; job4CPU/16GiB/2,400seconds). Failed-image cache cleanup is explicitly forced only for this attempt's owned labels; a successful image is retained only pending the original control comparison/cleanup. The submit gate includes all prior measured #29 allocation0.5637022CPUhours and rejects exceeding the first-stage32CPUhour ceiling. This build tests whether timeout controls can be reached; it is not itself a timeout comparison.

### Scanpy reconstruction failure and cleanup-only recovery

The unchanged Scanpy attempt is terminal failed after63.984seconds (0.0710933allocatedCPUhours). Its SHA-verified11,538-byte archive contains the48,621-byte build log: step12fails at the saved `get-pip.py | python3.13` command with `externally-managed-environment`, before later venv creation. No controls ran and no recipe was repaired.

The wrapper then raised during cleanup while inspecting an image already removed as a dependency of another owned image; therefore no final result JSON was written. This is a separate harness cleanup failure, not a biological outcome. Preserved original source/logs, adapted the archive reader to report missing result evidence explicitly, and prepared a single bounded cleanup-only job for the exact Scanpy ownership label on the original reserved worker. No build/control/model rerun occurs. Closure/cleanup claims require this cleanup's terminal readback.

The cleanup-only job succeeded in8.751seconds (0.0048617CPUhours). It found no remaining images or containers with the exact Scanpy label: the original cleanup had removed them before its stale-image inspect exception. The209-byte cleanup archive was hash-verified and matches the logged record. All seven #29 jobs are now terminal; cumulative measured allocation0.6396572CPUhours, zero model calls. Original build failure and missing summary remain preserved separately. No Scanpy controls ran.

### Reconstruction semantics: recorded replay proposal

Pinned upstream source and original transcripts show that failed BASH commands remain in generated Dockerfiles, but the agent originally continued after their recorded exits. Regenerated all three saved Dockerfiles byte-for-byte from retained transcripts: Scanpy16BASH/oneexit1, OHIF18BASH/one nonexecuted INVALID, MACS16BASH/threeexit2/one INVALID. Scanpy's later venv setup and MACS's later installation commands therefore never run in Dockerfile replay, although they did in the original bootstrap. Full checkout copy versus `.dockerignore` remains the separate OHIF context difference.

Prepared a generic recorded-action executor that does not edit, omit or add BASH inputs; it continues only matching original exits and stops on drift/timeouts/exceptions. Five bounded helper checks pass; temporary files removed. This proposes a more faithful, model-free reconstruction boundary, not per-task recipe repair. No repository replay or remote job launched yet. `recorded-replay-protocol.md` states the first Scanpy arm, existing budget, resource caps, provenance limits and remaining live-driver prerequisites.

### 2026-10-23 — Checkpoint original-command Scanpy replay

Prepared a single bounded, zero-model replay of the frozen Scanpy transcript. The driver uses the original Docker executor, full checkout copy and exact source-bound clone/smoke/git/fresh-check logic; the only Docker call adaptations are previously authorized resource/network/ownership controls and deadline/cleanup instrumentation. Three synthetic smoke/git branches pass, separately from the five prior replay-helper checks. No original action is edited or omitted, and unexpected exits or timeouts stop the comparison. The image may be retained only for the scoped original Scanpy controls, with explicit ownership and cleanup condition. Submission and biological outcome are not yet claimed at this checkpoint.

Submitted frozen replay `biotasks29-scanpy-recorded-001` from checkpoint `3d3529cb`, one attempt on existing reserved worker `marin-tpu-v4-reserved-32-us-central2-b-20261023-1755-6e8581d8-worker-0` (base `c7c14a252d`). Prior terminal accounting remains 0.639657222562366 CPU-hours; the new attempt is not yet included in measured terminal accounting. Scope published in issue comment https://github.com/Open-Athena/biotasks/issues/29#issuecomment-6372496977.

### 2026-10-23 — Prepare OpenMS checkout option

The separate acquisition candidate exposes `bootstrap.checkout_timeout_seconds` (strict positive integer, default 60) and forwards it from both bootstrap entry paths to the final checkout call. Clone/fetch commands and their 300/120-second limits are unchanged. Synthetic subprocess checks show exact default command/timeout parity, only 60→300 on checkout for the comparison, and unchanged error propagation; actual Pydantic validation rejects invalid option values. This is not a real checkout or recovered-PR result. A remote comparison still needs its own input/resource checkpoint and will stop before any bootstrap agent. Keep the original OpenMS ref `5edf83948816aee51225949dd0e613bd40f69c47` and original controller's 1 CPU/4 GiB when preparing that comparison. Current Scanpy replay remains separate and live.

### 2026-10-23 — Scanpy recorded replay completes; prepare original controls

`biotasks29-scanpy-recorded-001` is terminal after 380.406 seconds (0.4226733332210117 allocated CPU-hours). All 16 recorded actions matched their original exits, including the failed system-pip command; no action was edited. Original smoke/fresh checks remain false, ending with three collection errors. Archive `02853993ed555e40a7ebb1e94c73612c1c56ab38915e5040e936a4823ae0e224` is verified locally with output hashes. Owned containers, source context and tooling are absent; the one owned image is explicitly retained for pending controls. Cumulative measured #29 allocation is 1.0623305557833778 CPU-hours, zero model calls.

Prepared the unchanged 10-file Scanpy PR4389 export for the predeclared 300/1,200-second nop/oracle comparison. The supervisor is the executed Matchms controls path with only identities, repository inputs and output directory changed. The original task runner, grading contract, Harbor version, CPU/memory and internal retry semantics are unchanged. No controls outcome yet; see `scanpy-controls-protocol.md` for bounds and retention.

Submitted `biotasks29-scanpy-controls-001` from checkpoint `65cfc8b5` on the retained image's worker. Four original controls are pending; maximum allocation 9.6667 CPU-hours. Published replay evidence and control scope in https://github.com/Open-Athena/biotasks/issues/29#issuecomment-6372683096 and verified exact body/comment readback plus OPEN state and label. One owned image remains intentionally until control archive readback and cleanup.

### 2026-10-23 — OpenMS acquisition comparison checkpoint

Prepared two acquisition-only arms at original ref `5edf83948816aee51225949dd0e613bd40f69c47`: original checkout60 and configurable checkout300. Each runs in a fresh original-controller image at the original 1 CPU/4 GiB; clone/fetch/source commands remain fixed, with no repository build, bootstrap agent or credential. The original controller system Git/CA/curl prerequisites are retained. Outer job2CPU/8GiB/30GiB/4200s and a 3900s work deadline are bounded separately; cleanup kills the whole container before archiving or starting another arm. Budget admission includes the live Scanpy controls' full maximum as a reservation. No live OpenMS acquisition claimed at this checkpoint; see `openms-checkout-protocol.md`.

Submitted `biotasks29-openms-checkout-001` from `8d081003` on existing reserved worker `marin-tpu-v4-reserved-32-us-central2-b-20261023-1755-6e8581d8-worker-1`, base `c7c14a252d`. The independent Scanpy controls remain live. The admission record includes 9.6667 CPU-hours for those controls, 1.06233 already measured and 2.3334 maximum for OpenMS. Published/verified protocol comment https://github.com/Open-Athena/biotasks/issues/29#issuecomment-6372786615; issue remains open. Acquisition results and cleanup are pending, not inferred from submission.

### 2026-10-23 — OpenMS checkout barrier reproduced and crossed

`biotasks29-openms-checkout-001` completed both fresh-container arms in 226.653 seconds, 0.1259183332655165 allocated CPU-hours. At the same frozen ref and 1 CPU/4 GiB, the original 60-second checkout again raised `TimeoutExpired`. The 300-second arm completed checkout in 77.8991 seconds with HEAD equal to the frozen ref, tree `5793234fa6458623138bdc1eecda4e83c8f20c7e`, and empty tracked-file status. Both report Git 2.47.3; clone/fetch timeouts and commands are unchanged. Shared cache/network/order effects remain a limitation, but the successful checkout itself exceeded the original bound. This is acquisition-only recovery, not bootstrap/PR/task recovery.

Archive `07468d27c3942c5eb992a256f20498af482477eae07646aaea1877319c1c5024` (9,938 bytes) was downloaded and verified with all output hashes. Both owned containers and their checkouts are absent; downloaded tools are removed and cleanup has no errors. Cumulative measured #29 allocation is 1.1882488890488943 CPU-hours across nine terminal jobs. The separate Scanpy control handle remains active; its maximum reservation is unchanged.
