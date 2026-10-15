# Specification 013: reference recipe ready for review and validation work

Operator assessment: this is a usable draft of the pinned reference recipe and
output schemas under the agreed middle ground. It is **not** an accepted final
solver contract or evidence of scientifically validated grading. Stop prompt
iteration here for user inspection; no downstream stage has run. Original model
outputs are unchanged.

- [Generated public draft](task-brief.md)
- [Generated coverage/fidelity review](review.md)
- [Generated validation handoff](validation-handoff.md)
- [Canonical prompt](../../../../src/biotasks/prompts/notebook-task-specification.md)
- [Exact input and stage boundary](../../specification-inputs/011/README.md)
- [Original-file identities](artifact-manifest.json)

Factory checkpoint: `6c5ee313c866bdb2c414103b2d11ed848161b5b7`. Verified the actual
initial API request against that canonical prompt and unchanged input 011.
GLM-5.3 medium completed in one request, 226.75 seconds (3 minutes 47 seconds),
with one artifact submission and no source-tool calls or submission repair.
Optional read-only inspection was available. No client token/byte/request-count
cap was added; existing time bounds remained. This single result does not
establish that future notebooks will need only one call.

## Why this is sufficient for the narrower drafting stage

The recipe retains the source inputs, filtering, doublet scoring without removal,
normalization, feature selection, graph/embedding, all four clustering solutions,
source-defined annotation map and DE calculation. Named versioned operations
and explicit source arguments define omitted behavior, without a promise of
implementation-independent equality. All three existing exports remain required.

Public output cardinalities are symbolic. Observed cell/cluster counts and label
ranges are confined to the private review. The per-cell and per-group/gene row
units are now distinguished correctly: the tables share cluster labels, not
per-group row counts. Source-defined mapping constants remain public methods.
The response neither replaces the original data nor narrows the scientific task.

The handoff asks unresolved comparison questions instead of claiming calibrated
tolerances, repeatability or universal software equivalence. The private review
explicitly keeps the recorded semantic-validation flag false. This resolves the
main blockers from runs 011–012 for purposes of drafting.

## Remaining wording and validation work

The per-cell schema says every cluster/lineage column has exactly one label per
cell, although it also correctly states that the source mapping can leave lineage
values missing. The normative mapping is explicit and the reference's observed
mapping is complete, so this does not prevent reviewing the recipe. Before final
solver instructions are frozen, distinguish non-null cluster assignments from
potentially missing lineage annotations and state how validation handles them.
Do not silently treat all annotations as non-null for every allowed variation.

Column descriptions of DE statistics are summaries; their exact definitions come
from the named pinned operation. Final packaging must supply the resolved
reference environment, not merely rely on the draft's illustrative package list.
These are handoff details, not claims that an alternative stack has been tested.

Executable validation remains necessary for repeatability, numerical comparison,
cluster/annotation alignment, embedding comparison, valid representation changes,
wrong-output controls and verifier/solver resource fit. Any acceptance rule must
be stated publicly before a solver attempt. The raw 10x storage layout and the
in-memory cells-by-genes representation should be distinguished when preparing
final input documentation. No manual edits were made to the generated task.

## Evidence and scope

Nine original small files, the complete event trace, and the sole raw response
were recovered and hash-verified against the archive manifest. The original
request matches the checkpointed prompt/input; full evidence remains archived.
No scientific rerun, construction, solver, Daytona sandbox or viewer update.
All owned jobs and local clients are terminal. The one-seed result supports this
workflow choice for review; cross-notebook generality remains untested.
