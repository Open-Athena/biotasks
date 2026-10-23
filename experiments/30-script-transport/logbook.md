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

## 2026-10-23 — fixed live-case selection and acquisition

Selected Matchms958 as the first recorded errno-7 validation exception by original batch order, and Matchms671 as a known-success control independently verified in #29. Selection was committed before acquisition. Both current PR metadata responses match the original base/head SHAs. Bounded pinned-ref compare diff fetches returned 424,646 and 5,430 bytes respectively. Raw patches stay under ignored private inputs. Original failed script/diff bytes were not retained, so a reconstructed-input comparison must not claim exact byte replay. No live transport rerun yet; no easier-case replacement.

### Frozen live inputs and complete-validator driver

Prepared the first original Matchms errno7 identity (958) and previous successful control (671) with unchanged upstream splitting/targeting/stage builders. PR958's post script is425,528bytes versus103,780bytes pre; PR671 stages are4,459/6,002bytes. All four pass Bash syntax checks and are hash-bound privately. Added all pinned parser dependencies so the comparison can import the complete unchanged validator and native parser dispatcher rather than replacing them with a fixture implementation.

The driver verifies sources and stage bytes, records executor calls, isolates each arm on the same image, and aborts/removes the arm on client timeout. Three offline orchestration checks pass through the full validator; no Docker or biological execution has occurred. The bounded build/supervisor/submission is the next prerequisite. No new model calls, remote jobs or per-task repairs were added. `live-driver-check.json` states the remaining live-cleanup limitations.

### Bounded live submission checkpoint

Added `live_supervisor.py` and `submit_live.py` for one exact handle `biotasks30-matchms-live-001`. The supervisor reuses #29's successful unchanged-recipe reconstruction procedure, changing only ownership labels and adding the frozen comparison before unconditional owned-resource cleanup. No image is retained afterward. The supervisor stops work at8,400seconds and reserves300seconds for cleanup inside the9,000second Iris deadline. The submission gate rejects any existing handle/active #30 job, verifies payload consistency against preflight, and uses isolated secrets on existing reserved capacity. Prior measured allocation plus this10CPUhour ceiling is below11CPUhours. No model calls or upstream repair code are present.

### Live comparison completed and archive verified

`/exedev/biotasks30-matchms-live-001` succeeded in180.655seconds, one attempt,0.2007278allocatedCPUhours. Original958 raises errno7; candidate958 reaches both stages but zero tests are collected because upstream targets two deleted test files. Both671arms preserve exact F2P/P2Psets(1/30). No additional fixes or model calls occurred. `harvest_live.py` verified the13,874-byte archive and every recorded stream; `diagnose_live.py` binds the deleted-target diagnosis and exact control parity. All owned resources are absent. Raw archive is retained in ignored `inputs-private/live-001`; no `/tmp` remains. Publish the qualified result and track targeting under #32; retain the issue open for user review.

Automatic approval review rejected issue closure, citing the retained keep-open instruction. No closure occurred; publication proceeds with an explicitly open review state.
