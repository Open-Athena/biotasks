# Issue 29: runtime-limits

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — control inventory

Derived all14unstarted commands and all original task/reconstruction member hashes from #28. Eight affected Matchms/OHIF exports require16commands for fresh paired results on reconstructed images; Scanpy's two timeout arms add4commands. Proposed first stage is20commands/$0model, at most32allocatedCPUh on existing reserved capacity, not submitted. Baseline image reconstruction must be inspected before claiming a pure timeout comparison. `control-plan.json` records exact inputs and `plan.md` distinguishes scheduling from timeout recovery.
