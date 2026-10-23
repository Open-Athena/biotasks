# Issue 30: script-transport

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — local transport comparison

Checkpoint `9e0a51f7` ran under the shared heavy-work lock. Twenty cases passed in0.83seconds, peakRSS28,912KiB. The original actual Bash argument raises errno7 on the large payload; candidate delivery is exact with a maximum92-byte argument. Temporary test directory removed. This uses a local Docker-argv adapter, not a Docker daemon; shell diagnostic/introspection differences and inherited remote-process cancellation remain explicit. No live task recovery or model calls.
