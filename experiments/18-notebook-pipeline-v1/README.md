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

The simple offline intake viewer carries forward #17's Notebook → Task → Attempt organization, with pending states rather than invented tasks or traces. Reusing its full artifact and trajectory components remains pending until there are actual task/attempt records. The generated viewer includes author-only source text; keep it local until source terms are reviewed.

`protocol.json` records selected constraints and inspected harness revisions, not a working launch configuration. `runtime_verified: false` is intentional. No network/resource enforcement is implemented by the intake tool. The authoring prompt describes the target contract; it cannot enforce it.

## Current execution state

ZCode 0.16.9 from official release 3.14.5 successfully used the existing free GLM-5.3 service in a two-request infrastructure smoke; see `integration/zcode-smoke-001/`. The first bedtools conversion exhausted its 40-request authoring budget without producing a candidate. Its outcome and trace-retention limitation are recorded in `runs/author-bedtools-001/`. Scanpy authoring is the next original seed, using the staged observed PBMC3k counts and the exact context in `scanpy-intake-review.md`.

`campaign-budget.json` bounds authoring, repairs, references, controls and solver attempts. `zcode_smoke.py` is the remote authoring worker despite its original smoke-oriented filename: it accepts a checkpointed `run-spec.json` and `inputs.zip`, routes all ZCode model calls to the selected model through a capped proxy, and preserves outputs and traces. Node-level service guidance supplies private access at launch; the worker receives no credential in its prompt.

`harbor_worker.py` prepares pinned Harbor and Pi runtimes on remote CPU compute and runs the technical `integration/pi-offline-task/` fixture. `harbor_pi_remote.py` uses native Pi file/shell tools through `pi_remote.ts` and the tested Harbor transport in `biotasks.sandbox_tools`; inference stays outside the offline task. `retained_daytona.py` and `harbor_job.py` retain owned sandboxes until evidence has been exported and read-back verified, then delete only recorded owned IDs. The integration has not yet executed. It cannot count as a biological task or satisfy the required scientific success.

Remaining milestones: prove offline Pi and separate-verifier execution, natively validate biological references and grading controls, obtain baseline attempts including at least one full biological success, give every original seed a documented disposition, extend the explorer to real task/attempt evidence, and preserve the final campaign artifacts and report. Ten prepared sources do not imply ten generated tasks.

Model service use follows node-level guidance. Runtime endpoint addresses and credentials belong exclusively in private launcher state, never this experiment's public artifacts.
