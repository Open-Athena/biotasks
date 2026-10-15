# Reference preparation, run 009

One GLM-5.3 medium call, 163 seconds, no repair. **Static preparation review
passed; the scientific reference has not been executed.**

- [Readable plan](plan.md)
- [Worker export code](exports.py)
- [Source diff](source.diff)
- [Inspection](inspection.json), [receipt](run-receipt.json), [original-file manifest](artifact-manifest.json)

The worker selects per-cell clustering solutions, lineage annotation, UMAP and
identity/sample fields, plus the full per-cluster DE table. It excludes QC,
doublet diagnostics, feature-selection/PCA/graph intermediates and full-state
dumps. The full DE table covers the already named cluster-7 excerpt without a
separate duplicate file. Source narrative supports clustering, annotation,
embedding interpretation and marker discovery as the represented outcomes.

The export uses the native stored-result accessor documented by the notebook.
Inspection of [the helper at the source revision](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/src/scanpy/get/get.py)
confirms no cutoff is requested and stored per-group ranking is retained.
The installed execution version, numerical fidelity and runtime remain untested.
No task-specific code was manually changed.

Run from [checkpoint 9c118a8](https://github.com/Open-Athena/biotasks/commit/9c118a812e271b4be2a6b4b16ecf5fb0a7139ac1).
All 17 original files were retrieved and hash-verified. Schema, syntax, exact
source prefix, export identity and computed diff checks passed. Input is unchanged
from prior preparation runs. Reported usage: 7,377 prompt and 24,369 completion
tokens, including 22,639 reasoning tokens. Exactly one request, no repair;
no extra client token/byte caps and the existing 600-second request timeout.

The remote job and local clients are terminal. No scientific setup/execution,
sandbox, separate model review, construction, solver or viewer update. An
unchanged-prompt confirmation run is planned before concluding prompt iteration.
