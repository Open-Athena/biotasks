# Reference preparation, run 010

One GLM-5.3 medium call, 208 seconds, no repair. **Static preparation review
passed, confirming run 009 with the same prompt and input.** No scientific
reference execution has occurred.

- [Readable plan](plan.md)
- [Worker export code](exports.py)
- [Source diff](source.diff)
- [Inspection](inspection.json), [confirmation comparison](confirmation.json)
- [Run receipt](run-receipt.json), [original-file manifest](artifact-manifest.json)

The worker selects per-cell clustering solutions, broad lineage annotation,
UMAP coordinates and cell/sample identifiers, plus the full ranked DE table.
It adds the stored DE parameters as interpretation context. QC/doublet
diagnostics, feature-selection/PCA intermediates and full-state dumps are excluded.
The named cluster-7 marker excerpt is explicitly covered by the full DE table.

Both runs 009 and 010 passed static review against source goals and code.
They use different filenames and serializers, and only 010 writes a separate
parameter file, but cover the same scientific results. The system prompt,
complete input and serialized API request are byte-identical. This supports
stopping prompt iteration for this seed, not a claim of generality across seeds.
No generated code was manually corrected or executed.

The direct DE export preserves stored arrays and rank order. The notebook-pinned
[Scanpy implementation](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/src/scanpy/tools/_rank_genes_groups.py)
defaults to no optional expression-fraction output and stores ordinary method,
grouping and reference parameters. This supports the static export review;
execution must still verify the installed version, output schemas, numerical
fidelity, serialization and runtime.

Run from [checkpoint 341f38c](https://github.com/Open-Athena/biotasks/commit/341f38c3ae6cb2798c34b20ecc30857a4d5d9f55).
All 17 original files were retrieved and hash-verified. Schema, combined syntax,
exact original-source prefix, export identity and computed diff checks passed.
Reported usage: 7,377 prompt and 31,306 completion tokens, including 29,176
reasoning tokens. Exactly one request, no repair; no extra client token/byte
caps and the existing 600-second request timeout.

Remote job and local clients are terminal. The initial retrieval preceded the
archive's appearance in the log service; a second read of the same completed
job recovered all evidence. No additional model call, sandbox, scientific
setup/execution, separate review worker, downstream stage or viewer update.
