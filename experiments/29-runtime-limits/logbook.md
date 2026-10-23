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
