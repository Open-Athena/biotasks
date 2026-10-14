# Reference preparation, run 006

The updated terminal-result prompt produced a proposal on the first GLM-5.3
call; no repair was needed. **This is preparation output for inspection, not an
executed or scientifically validated reference.**

- [Readable plan and complete script](plan.md)
- [Complete edited script](reference.py)
- [Controller-computed diff](source.diff)
- [Exact prompt](prepare/system-prompt.md), [input](prepare/input.json) and [original response](prepare/artifact-stage/trace/1/response.json)

The worker proposes three CSV exports from existing stored results:

1. Per-cell Leiden cluster assignments and broad cell-type annotations.
2. Per-cluster marker-gene names, scores, p-values and adjusted p-values.
3. The existing named list of the top five marker genes for cluster 7.

It excludes intermediate matrices, QC diagnostics and plot-only results, and
does not export a full AnnData snapshot. No dependency manifest or input-staging
script was returned. Original input-loading code remains in the script.

JSON-schema and Python-syntax checks passed. The saved script matches the
original model response, and its computed diff matches the untouched baseline.
All 16 original preparation evidence files were retrieved and hash-verified.
[Inspection record](inspection.json) and [file manifest](artifact-manifest.json).
These checks do not establish endpoint completeness or scientific fidelity.

Two observations are recorded separately from the unchanged worker output: the
model altered three narrative comments despite the preservation instruction;
and the inventory uses `outputs/<filename>` while the script writes to
`/work/outputs/<filename>`, so its path base needs to be explicit for execution.
No task-specific correction was made, and no extra repair call was launched.

Run from [checkpoint 8f901f4](https://github.com/Open-Athena/biotasks/commit/8f901f4937bf1f46da68d7b1591f808cb956bbe0)
using the unchanged newer Scanpy conversion, GLM-5.3 medium reasoning, strict
JSON-schema responses, one creation and at most one structural repair, no extra
client token/byte caps and the existing 600-second request timeout. Preparation
took 348 seconds. Reported usage: 6,953 prompt tokens, 57,325 completion tokens,
including 50,672 reasoning tokens. [Run receipt](run-receipt.json).

The remote job finished successfully and the local monitoring client is terminal.
No task sandbox, biological input staging, generated-code execution, separate
model review, construction, solver attempt or viewer update occurred. Inspect
this output before advancing to another stage.
