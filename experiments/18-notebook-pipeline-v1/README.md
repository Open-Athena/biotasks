# Notebook-to-task v1

Research for [issue #18](https://github.com/Open-Athena/biotasks/issues/18), based on main `2a1950d239f1ada467c35393991dac87debe35f7`. This branch is permanent research, not a proposed merge into main.

The first implementation prepares authoring workspaces from hash-verified local notebook sources. It supports Jupyter v4 and R Markdown, removes Jupyter outputs/attachments/metadata, preserves code and narrative, and renders the packaged `notebook-task-v1` prompt. It never executes seed code or calls a model. Source code itself may contain example answers, so these workspaces are author-only, never solver inputs. Prior output directories cannot be overwritten; missing/mismatched inputs remain in the panel with explicit failures.

## Reproduce intake

Use the repository's locked environment. Populate an external cache with the ten exact documents linked in `seeds.json`, named by their `source_sha256` (without an extension). Do not put source documents, credentials, or prepared workspaces in Git. Source redistribution remains under review. This preparation can use previously inspected source bytes; the hash comparison establishes their identity.

```sh
uv run --locked python -m biotasks.notebook_pipeline \
  --manifest experiments/18-notebook-pipeline-v1/seeds.json \
  --protocol experiments/18-notebook-pipeline-v1/protocol.json \
  --cache /tmp/biotasks-18-source-cache \
  --output /tmp/biotasks-18-intake-001
uv run --locked python experiments/18-notebook-pipeline-v1/build_explorer.py \
  --intake /tmp/biotasks-18-intake-001/intake.json \
  --output /tmp/biotasks-18-intake-001/index.html
```

The offline explorer shows Notebook → Task → Attempt states from `campaign.json`, including unsuccessful conversions and unaccepted candidate versions. Its prepared trajectory view reuses the earlier explorer's prebuilt atif-lens component and Pi converter at the exact revision in `explorer-assets/reuse-manifest.json`; the converter records the current Pi version and preserves pending-call/completion evidence. No solver trace is displayed until one actually exists. Bundled viewer assets are unmodified, with the upstream license retained. The generated viewer includes author-only source text; keep it local until source terms are reviewed.

`protocol.json` records selected constraints and inspected harness revisions, not a working launch configuration. `runtime_verified: false` is intentional. No network/resource enforcement is implemented by the intake tool. The authoring prompt describes the target contract; it cannot enforce it.

## Current execution state

ZCode 0.16.9 from official release 3.14.5 successfully used the existing free GLM-5.3 service in a two-request infrastructure smoke; see `integration/zcode-smoke-001/`. The first bedtools conversion exhausted its 40-request authoring budget without producing a candidate. Its outcome and trace-retention limitation are recorded in `runs/author-bedtools-001/`. Scanpy produced two candidate versions using the observed PBMC3k counts. Both authoring sessions ended at the 40-request cap. Candidate v2 passed 12 author-side grader cases. The first native trial failed task-name schema validation; after a recorded metadata-only packaging correction, the native reference earned 1.0 in the separate offline verifier in 7.299 seconds of reference execution. All four subsequent native grading controls matched their expected rewards. The accepted task then earned full credit on its first GLM/Pi baseline in 60.709 seconds, with no retry; see `scanpy-acceptance.json` and `runs/scanpy-baseline-001/`. The full 664815-byte trajectory was recovered with hash verification; its compact ATIF view is retained in Git and embedded in the offline explorer. See `runs/repair-scanpy-002/`.

`campaign-budget.json` bounds authoring, repairs, references, controls and solver attempts. `zcode_smoke.py` is the remote authoring worker despite its original smoke-oriented filename: it accepts a checkpointed `run-spec.json` and `inputs.zip`, routes all ZCode model calls to the selected model through a capped proxy, and preserves outputs and traces. Node-level service guidance supplies private access at launch; the worker receives no credential in its prompt.

`harbor_worker.py` prepares pinned Harbor and Pi runtimes on remote CPU compute and runs either the technical `integration/pi-offline-task/` fixture or a biological candidate reconstructed from preserved authoring sessions. `restore_authoring.py` verifies archived inputs and overlays; the worker refuses a task that differs from the reviewed file manifest in its run specification. `harbor_pi_remote.py` uses native Pi file/shell tools through `pi_remote.ts` and the tested Harbor transport in `biotasks.sandbox_tools`; inference stays outside the offline task. `retained_daytona.py` and `harbor_job.py` retain owned sandboxes until evidence has been exported and read-back verified, then delete only recorded owned IDs. Four integration launches are recorded under `integration/pi-offline-001/` through `pi-offline-004/`. The last confirmed free GLM inference, offline task execution, and native Pi read/write/edit, but Bash had a cwd mapping error and the separate verifier image lacked its executable entry point. Both defects have been corrected. Scanpy native validation subsequently verified the separate verifier packaging; the first biological baseline also verified the corrected Pi Bash mapping. All three sandboxes created across those launches were deleted after artifact read-back. The smoke budget is exhausted. These technical runs cannot count as biological tasks or satisfy the required scientific success.

Remaining milestones: complete the other original seeds and baseline attempts for any accepted tasks, finish explorer validation, and preserve the final campaign artifacts and report. The two methylKit authoring sessions produced an incomplete, unaccepted package; its missing expected assets, strand mismatch and reproduced NaN grading bypass are preserved in `runs/author-methylkit-002/`. Seven original seeds have prepared authoring bundles; COBRApy authoring is in progress. Bedtools conversion failed with preserved evidence. One accepted task and one full solve do not complete the panel. Ten prepared sources do not imply ten generated tasks.

Model service use follows node-level guidance. Runtime endpoint addresses and credentials belong exclusively in private launcher state, never this experiment's public artifacts.

Author workers now restrict inherited CPU affinity to at most four CPUs. Earlier resource probes established memory enforcement but revealed an unlimited CPU cgroup quota; their allocation requests do not prove compliance. Disk-quota enforcement remains unresolved. See `author-affinity-check.json` for a local inheritance check; remote probes remain authoritative.
