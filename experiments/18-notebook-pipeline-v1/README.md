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

## Next executable milestone

1. Verify isolated, unattended ZCode authoring against the existing GLM-5.3 service, preserving event traces and pinning primary and auxiliary models. Choose finite generation/repair budgets before calling it.
2. Establish Pi inference routing while task commands have no general network; prove denial with an executable probe. Inspect the pinned Harbor separate-verifier integration and resource accounting.
3. Begin with the small bedtools seed, resolve input lineage/terms and methodological boundaries, and generate one candidate. Validate with native reference and scientific negative/partial controls before any baseline solve. Keep all ten seeds in the panel.
4. Add task versions, stage records, timeout artifact recovery and real attempt data to the explorer. Extend to remaining seeds after the first complete path works.

Model service use follows node-level guidance. Runtime endpoint addresses and credentials belong exclusively in private launcher state, never this experiment's public artifacts.
