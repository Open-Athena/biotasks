# Reference preparation, run 008

GLM-5.3 completed one call in 193 seconds, with no repair. Structural checks
passed. **Endpoint selection still needs review; the reference was not executed.**

- [Readable plan and exclusions](plan.md)
- [Worker-returned export code](exports.py)
- [Computed source diff](source.diff)
- [Controller-assembled reference](reference.py)
- [Exact prompt](prepare/system-prompt.md), [input](prepare/input.json) and [response](prepare/artifact-stage/trace/1/response.json)

The worker proposes five CSVs: cell annotations, gene annotations, UMAP
coordinates, differential-expression results and the existing cluster-7 top-five
marker list. It no longer exports the complete AnnData object. However, it copies
all cell/gene annotation columns, including QC diagnostics and feature-selection
intermediates. Its evidence for those tables still invokes survival to script
completion rather than the scientific endpoint criterion. The narrower selection
rule was only partially followed. Original generated output is preserved unchanged.

JSON Schema, combined Python syntax, exact original-source prefix, export-code
identity and computed diff checks passed. All 17 original preparation files were
retrieved and SHA-256 verified. See the [inspection](inspection.json),
[manifest](artifact-manifest.json) and [receipt](run-receipt.json).
These checks do not establish scientific correctness or executability.

Run from [checkpoint c41bc9d](https://github.com/Open-Athena/biotasks/commit/c41bc9d9f642dba73b3146af94718b947236e23e)
with the unchanged newer Scanpy conversion, GLM-5.3 medium, strict JSON-schema
responses, one request and no automatic repair. No extra client token/byte caps;
the existing request timeout is 600 seconds. Reported usage: 7,249 prompt tokens
and 27,689 completion tokens, including 25,314 reasoning tokens.

Remote worker and local clients are terminal. The first retrieval saw only part
of the log archive; a second read of the same completed job recovered all files.
No additional model call, manual output fix, scientific setup/execution, sandbox,
independent model review, downstream stage or viewer update occurred.
