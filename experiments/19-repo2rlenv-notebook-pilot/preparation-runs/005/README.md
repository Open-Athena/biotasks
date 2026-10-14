# Reference preparation, run 005

The simplified preparation contract produced an accepted proposal on the first
GLM-5.3 call; no repair was needed. **This is preparation output for inspection,
not an executed or scientifically validated reference.**

- [Complete edited script](reference.py)
- [Controller-computed diff against the original conversion](source.diff)
- [Readable plan, dependencies and proposed staging](plan.md)
- [Python dependency declaration](pyproject.toml) and [input-staging script](stage-inputs.sh)
- [Exact prompt](prepare/system-prompt.md), [input](prepare/input.json) and [model response](prepare/artifact-stage/trace/1/response.json)

The worker proposes two endpoint artifacts: a full final `adata_annotated.h5ad`
and `rank_genes_groups_cluster7_head5.csv`. It replaces runtime DOI registry
retrieval with a registry for the staged original inputs, captures the existing
cluster-7 table return value, and appends the export code. The returned script
also contains small narrative-comment changes; the exact diff preserves them.
No generated file has been manually repaired.

Both the remote admission checks and a local check of the exact supplied JSON
Schema passed. The saved script is identical to the model's `reference_script`
field, Python syntax compiles without executing it, and the diff matches the
baseline and returned script. All 19 original evidence files were recovered and
SHA-256 verified. The local checks and notes are recorded in [inspection.json](inspection.json).

Points for subsequent review: the worker chose a full-state snapshot rather
than explicit tables for most endpoints; endpoint sufficiency and faithful
capture of plot-derived transformations remain unreviewed. Its exclusion
rationale also claims the source's pre-filter sample counts can be recomputed
from the final filtered object, although those represent different populations.
These notes do not alter the worker output. No separate model review has run.

Run from [checkpoint 67c3dbc](https://github.com/Open-Athena/biotasks/commit/67c3dbc4e07513f704dd498349a9f155d97458b5)
with the newer Scanpy notebook, GLM-5.3 medium reasoning and strict JSON-schema
responses. The contract returns a complete script and one endpoint inventory;
the controller computes the diff and file identities. The one-creation/one-repair
budget was retained, with no extra client token/byte caps and a 600-second request
timeout. The single response took about 392 seconds. Usage: 7,991 prompt tokens
and 60,528 completion tokens, including 52,078 reported reasoning tokens.
[Run receipt](run-receipt.json).

The remote job is terminal (`SUCCEEDED`). This indicates successful preparation
admission only. No generated setup, data download, notebook/reference execution,
scientific review, task construction, solver attempt or viewer update occurred.
