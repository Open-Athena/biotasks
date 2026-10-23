# Issue 30: script-transport

## 2026-10-23 — initial investigation

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Baseline evidence is issue #28, research commit `ac44348e`; official source is Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. No model calls or remote executions. Initial source inspection and bounded local comparisons precede any live protocol.

## 2026-10-23 — local transport comparison

Checkpoint `9e0a51f7` ran under the shared heavy-work lock. Twenty cases passed in0.83seconds, peakRSS28,912KiB. The original actual Bash argument raises errno7 on the large payload; candidate delivery is exact with a maximum92-byte argument. Temporary test directory removed. This uses a local Docker-argv adapter, not a Docker daemon; shell diagnostic/introspection differences and inherited remote-process cancellation remain explicit. No live task recovery or model calls.

## 2026-10-23 — first real-Docker probe prerequisite failure

The original handle `/exedev/biotasks30-transport-001` is terminal FAILED. Its source checkpoint `96127f9e` and structured result show `FileNotFoundError: docker` before any container creation. The cleanup command also lacked the CLI; no Docker command launched. This is an infrastructure prerequisite failure, not transport evidence. Original result is preserved in `attempts/001/result.json`, with private receipt/observation in `run-private/biotasks30-transport-001/`.

A separate002probe adds only the same hash-pinned Docker CLI archive used by #28, with bounded streaming download and owned tool-file removal. The original/candidate executor bytes remain unchanged. Maximum cumulative allocation for the two probe jobs is2/3CPUhour, $0model; no new capacity. Current source preflights every submission and refuses overlap or duplicate handles. This is an explicit new infrastructure revision, not a hidden retry or a PR/model run.

## 2026-10-23 — cached tag prerequisite and immutable base

Probe002 is terminal FAILED before any container creation: Docker CLI verification succeeded, but `python:3.12-slim` was not a cached tag. It verifies zero owned containers remain and its downloaded tool files were removed. Result preserved in `attempts/002/result.json`. A missing tag does not prove the underlying image bytes are absent.

Probe003 uses the exact immutable controller image already pinned by #28 (`docker-tool.json`), inspecting by digest and performing at most one bounded120second pull of that same digest if absent. No mutable-tag lookup, package build or transport-candidate change. Shared base-image cache is retained; no task-specific image is built. All containers remain owned/labeled, capped and removed. Maximum cumulative three-job allocation is1CPUhour, model spend$0. These are separate explicit infrastructure revisions, not successful transport evidence or hidden retries.

## 2026-10-23 — real Docker mechanism and precise timeout follow-up

Probe003 is terminal SUCCEEDED and delivers the candidate's 1,080,000-byte payload with exact SHA256; the original raises errno7. Both executors preserve representative quoting/stdin/exit/cwd behavior. Both leave a Bash process entry after client timeout, but this first census did not record process state and cannot alone exclude a zombie. It removes both owned containers, verifies absence, and removes tool files; shared pinned base cache remains.

Read-only accounting verifies all three jobs terminal/one attempt each, with 0.04612722211413914 allocated attempt CPU-hours and zero model calls. A fourth explicitly checkpointed probe adds process state and two CPU-tick snapshots after timeout. It preserves both executor hashes and the image/client pins. Submission requires measured prior usage plus its 1/3CPUhour maximum to fit within the existing one-CPU-hour campaign ceiling; no extra budget/new capacity. Original003result remains unchanged.

## 2026-10-23 — final synthetic-probe evidence

Probe004 is SUCCEEDED: both original and candidate have runnable Bash processes with CPU ticks increasing after client timeout. Representative behavior and exact 1,080,000-byte candidate delivery pass. All four original handles are terminal/one attempt each; total allocated attempt CPU-hours 0.05441777772373624, $0 model calls/spend. All owned containers and downloaded tool files removed; shared immutable base cache retained. Raw result-log readbacks and payload/checkpoint bindings are preserved. Redundant parsed-result copies were removed only after equality with committed attempt records. Live PR comparisons remain required.
