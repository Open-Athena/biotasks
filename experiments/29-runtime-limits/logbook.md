# Issue 29: runtime-limits

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — control inventory

Derived all14unstarted commands and all original task/reconstruction member hashes from #28. Eight affected Matchms/OHIF exports require16commands for fresh paired results on reconstructed images; Scanpy's two timeout arms add4commands. Proposed first stage is20commands/$0model, at most32allocatedCPUh on existing reserved capacity, not submitted. Baseline image reconstruction must be inspected before claiming a pure timeout comparison. `control-plan.json` records exact inputs and `plan.md` distinguishes scheduling from timeout recovery.

## 2026-10-23 — reconstruction preflight

Verified the original bootstrap metadata for all three control repositories against original phase/member hashes. Matchms originals were read in place; only bootstrap metadata was copied locally, with no upload. OHIF/Scanpy public originals were restored anonymously; owned Xet cache removed. Syntax-only checks pass all 4/18/16 RUN bodies respectively, in 0.08 seconds / 18,496 KiB. This removes the specific MACS-style shell-syntax prerequisite for these three recipes, but does not establish build success or dependency/image reproducibility. No control or recipe executed.

## 2026-10-23 — exact Harbor override source

Read the historical Harbor0.6.6 wheel from PyPI, verified its published SHA256/1,120,578bytes and retained selected source/license. No installation/import. Verified the CLI verifier-only multiplier and effective timeout formula: multiplier4 turns original300seconds into1,200without changing task bytes or other stage limits. This resolves the override-support prerequisite; execution and complete controls remain outstanding.
