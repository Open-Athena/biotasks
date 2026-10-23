# Recorded bootstrap replay comparison

The original agent executes each BASH action through `DockerSandbox.exec` (`bash -lc`, 300-second timeout) in a persistent container. A failed action is recorded, and the loop continues. The generated Dockerfile instead emits every BASH action as a separate `RUN`, including failed actions; Docker then stops at the first nonzero exit. Dockerfile `/bin/sh` and build-context `.dockerignore` handling also differ from the original Bash executor and full `docker cp` checkout. These are reconstruction differences, not additional model decisions.

`prepare_recorded_replay.py` binds original transcripts, bootstrap metadata and command hashes for Scanpy, OHIF and MACS. It regenerates all three saved Dockerfiles exactly from their transcripts. Scanpy records one exit-1 action followed by eight more BASH actions. MACS records three exit-2 syntax errors followed by further commands. OHIF has no nonzero BASH exits but its Docker build excludes a workspace that the original container copy included. INVALID actions did not execute upstream and are not shell commands in the replay. No READ_FILE/LIST_DIR or other state-changing action needs reconstruction in these three transcripts.

## Intervention and boundaries

Replay every recorded BASH input byte-for-byte, in order, in a persistent container using the pinned original executor. Include failed commands; do not delete syntax tails, quote version constraints, insert installs, shorten commands, change test targets, or call a model. Compare each exit code with its original recorded value. Stop on any mismatch, exception or client timeout; remove the entire owned sandbox before any later work. Matching exit codes alone does not prove matching filesystem state, dependency versions, command success or environment readiness.

Start from the original repository commit and base-image reference, copy the full checkout as upstream does, and record actual image identity. Reuse pinned clone/executor/post-bootstrap logic where possible, binding all adapted infrastructure. The only container adaptations are the authorized CPU/memory/network caps, ownership labeling, deadlines and cleanup. Preserve upstream smoke and fresh-image checks and report their outcomes separately; do not reinterpret false flags as ready. Scanpy and MACS originally had false smoke/fresh flags, while OHIF had true flags.

This is a separate reconstruction comparison against failed Dockerfile replay, not a rewrite of original evidence and not a fresh generation run. A model-free replay may expose dependency drift or another failure; there is no automated or manual repair fallback. New reconstructed images cannot be represented as the deleted original image bytes.

## First proposed live arm

Start with the frozen Scanpy transcript (16 BASH actions), using one reserved TRC job with 4 allocated CPUs, 16GiB RAM, 16GiB disk and a 7,200-second total limit (8 allocated CPU-hours). Use 1.5CPU/6GiB per replay sandbox, the original 300-second command bound, a work deadline at 6,600 seconds and at least 300 seconds for cleanup. Do not start another action when its full timeout cannot fit. Count this attempt against #29's existing 32-CPU-hour first-stage ceiling, including all earlier measured attempts; no new capacity or model spend. OHIF and MACS need separate bounded checkpoints; MACS cannot silently consume #29's allowance.

Retain an owned image only for an explicitly recorded subsequent control comparison; otherwise remove it and all owned containers/cache. Preserve raw outputs privately with checksums and verified archive readback. Before controls, inspect reconstruction evidence and keep the original tasks, Harbor version, CPU/memory bounds and planned timeout arms unchanged. No claim of recovered controls follows from replay completion alone.

## Current validation

The replay helper passes two actual Bash continuation/state checks, an actual unexpected-exit stop, and synthetic client-timeout and executor-exception stop checks. The helper never resumes after a timeout, but it does not itself terminate remote processes: container removal is the caller's responsibility. No repository replay, remote job, image commit or control has been launched under this protocol yet. Live driver, source/context parity, resource admission, post-bootstrap checks and unconditional cleanup must be checkpointed before execution.
