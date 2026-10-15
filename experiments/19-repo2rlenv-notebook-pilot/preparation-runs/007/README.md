# Append-only reference preparation, run 007

GLM-5.3 returned an append-only proposal on its first call, with no repair, in
71 seconds. **Original-source preservation passed; endpoint selection still
needs revision/review. This is preparation output, not an executed reference.**

- [Worker-returned export code](exports.py)
- [Readable plan and exclusions](plan.md)
- [Controller-assembled reference script](reference.py)
- [Computed diff](source.diff)
- [Exact prompt](prepare/system-prompt.md), [input](prepare/input.json) and [model response](prepare/artifact-stage/trace/1/response.json)

The controller assembled the reference as the untouched original script, two
newlines, then the returned export code. Exact prefix preservation, export-code
identity, combined Python syntax, the supplied JSON Schema and the computed diff
all passed checks. All 17 original preparation evidence files were downloaded
and SHA-256 verified. [Inspection record](inspection.json),
[file manifest](artifact-manifest.json), [run receipt](run-receipt.json).

The worker proposes a full annotated AnnData file, a CSV containing every
per-cell annotation column, and a per-cluster differential-expression CSV.
Static inspection flags the first two: the whole-state export is justified by
all branches ending in one container, rather than source evidence that the whole
container is itself the intended deliverable; and the per-cell CSV includes QC
and doublet diagnostics. These choices appear inconsistent with the intended
terminal-only selection rule. The appended-code interface fixes accidental
source editing, but does not ensure correct endpoint selection. The response
is preserved unchanged; no manual correction or additional repair was applied.

Run from [checkpoint b1a0463](https://github.com/Open-Athena/biotasks/commit/b1a0463b6974aa4231d56fadec598e46ebf5bdc9)
with the unchanged newer Scanpy conversion, GLM-5.3 medium reasoning, strict
JSON-schema responses, one creation and at most one structural repair, no extra
client token/byte caps and the existing 600-second request timeout. Reported
usage: 7,111 prompt tokens and 12,873 completion tokens, including 11,281
reasoning tokens. This single run is not a controlled latency comparison.

The remote job and local submission/monitoring clients are terminal. No task
sandbox, input download, generated setup/analysis, independent model review,
construction, solver or viewer update occurred. Inspect the output before
advancing.
