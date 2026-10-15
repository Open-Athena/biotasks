# Setup and offline reference: run 001

The first tool-enabled setup session passed its first complete offline reference
test. Source/export review and a separate read of the archived outputs found no
blocker for this stage on this notebook. No additional model session or prompt
change was needed after observing the result.

| Measurement | Observed |
| --- | --- |
| Model | GLM-5.3, medium effort |
| Model calls | 93 in one session, including tool-use turns |
| Complete reference tests | 1 of 2 allowed; no repair test used |
| Worker elapsed time | 725.6 seconds, including investigation and execution |
| Complete reference computation | 147.5 seconds, including imports and exports |
| Peak child-process RSS | 4.94 GiB; not aggregate sandbox memory |
| Sandbox ceiling | 4 CPUs, 8 GiB RAM, 10 GiB disk; no GPU |
| Offline execution | Provider policy plus representative outbound probes |
| Cleanup | Verified; separate readback found zero owned sandboxes |

The execution checkpoint is `e2da746ec48d48a0fe8445ee6a9b110e3055a1c3`.
Preparation run 010 and its exports were unchanged. Generated files below are
original worker outputs, not manually corrected versions.

## Inspect the inputs and outputs

- [Actual prompt](system-prompt.md), [configuration](configuration.json) and
  [original source provenance](provenance.json).
- [Generated setup dependencies](candidate/pyproject.toml),
  [input-staging recipe](candidate/stage-inputs.sh),
  [declared inputs](candidate/inputs.json) and
  [adapted analysis](candidate/analysis.py).
- [Source diff](trial/source.diff): cache location, offline loading of the same
  provider registry, and headless plotting setup. No scientific method,
  parameter, filter, annotation, branch or selected export changed.
- [Resolved environment](trial/environment.txt), [uv lock](trial/uv.lock),
  [input hashes](trial/inputs-before.json) and [native trial result](trial/result.json).
- [Worker's final report](outcome.json), [structural output inspection](output-audit.json) ([executed inspection source](inspection-source.txt))
  and [original-evidence manifest](artifact-manifest.json).

| Export | Rows | Bytes |
| --- | ---: | ---: |
| Cell clusters, lineage and UMAP | 17,041 | 1,098,166 |
| Full ranked genes by cluster | 398,259 | 28,207,516 |
| Stored differential-expression parameters | JSON object | 157 |

A separate read-only audit downloaded all three archived output files, checked
their original hashes, and streamed every CSV row. Required columns were present;
no fields were blank, numeric result fields were finite, and p-values were in
[0, 1]. The stored parameters specify the source's Wilcoxon test, comparison
against the rest and Benjamini–Hochberg correction. This is file integrity and
structural inspection, not independent scientific reproduction. The controller
also verified that all three staged inputs remained byte-identical and that the
submitted candidate matched the candidate that passed. Large original tables
and full raw campaign evidence remain in the configured artifact store; they are
not copied into Git. The manifest preserves their sizes and hashes.

## Review notes and limits

The original worker report remains unchanged. Its “~5.18 GiB” memory conversion
is incorrect: 5,175,376 KiB is 4.94 GiB. Its wording about “controller-staged” input
copies is also imprecise: GLM staged the files; the controller verified them.
The controller recorded a uv lock even though the generated project declares
minimum versions. Re-resolving those requirements later is not the same as
reusing this resolved environment.

The test recreated the virtual environment and working/output directories but
shared OS state and caches with exploration. Cold-image reconstruction and
repeat-run numerical stability are not established. The source warns about
duplicate observation names during concatenation, then explicitly calls
`obs_names_make_unique()`. Later specification review corrected the initial
interpretation of that warning: comparisons must preserve the source's exported
identifier scheme and sample attribution, rather than infer that final
identifiers remain duplicated. Do not treat
this one source as evidence of cross-notebook generality.

All scientific branches and the reviewed terminal exports ran within the agreed
limits. This is sufficient to finish the current setup/execution iteration.
Task construction, comparison tolerances, grader controls, independent solver
attempts and task release remain separate work. No viewer update was made.
