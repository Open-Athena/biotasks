# Fixture-backed replay API: investigation option

Gonzalo explicitly included a "fake" API within scope on October 6, 2026.
For recorded AlphaGenome Atlas responses, the precise term is **replay API**
or **fixture-backed API**. Mock API is the broader testing term; a stub simply
returns predefined responses. A simulator computes new behavior and would need
separate scientific justification. This document is a design option, not an
implemented service or authorization to call the source API.

## Proposed boundary

A task could expose a small local service or Python client with the query
operations the solver actually needs. Preserve the supported request/response
semantics of the pinned Atlas client: variant identities, requested scorers,
optional tissue/gene filters, score dimensions, and metadata. Scope the claim
explicitly; do not call a small subset a complete emulator of Atlas.

Retrieve authorized real responses once, record requests, API/client/model or
score-version information where available, timestamps, hashes, and terms, and
verify read-back. Freeze responses as versioned fixtures. Never call fabricated
scores native reference evidence. Precomputed predictions are model-derived
inputs, not observed molecular measurements.

Canonicalize query keys without changing allele, assembly, coordinate, or scorer
meaning. Preserve the distinction between absent scores and zero scores. Handle
batch ordering, duplicate variants, filters, and documented errors explicitly.
Unsupported requests fail clearly; do not silently fabricate values or fall back
to live inference. No source API keys belong in solver-visible files.

A local service can hold fixture storage outside the solver filesystem and expose
only the permitted API. If fixtures are directly provided as task inputs instead,
accept that the solver can read them; grade the intended analysis, not a hidden
requirement to invoke an API. References, expected task answers, and graders stay
private in either design. With broad query access, record potential enumeration
shortcuts. Large interval queries need explicit response-size limits.

## Candidate Atlas task

For a bounded locus or variant list, retrieve selected score families, reconcile
variant/gene/tissue metadata, and produce a prioritization table explaining score
components. Validate numerical output, identities, missing values, and rankings
with declared tie handling. This tests analysis of model predictions; it does
not establish pathogenicity or experimental regulatory effects.

The official client exposes `query_variant`, `query_variants`, `query_interval`,
and `scorer_metadata`. Lookup does not require local model inference or a GPU.
Batch/interval methods expose worker settings; use one worker if later authorized
on this VM. No wall time, memory use, or response-size estimate has been measured.

## Source-use prerequisite

The pinned [AlphaGenome README](https://github.com/google-deepmind/alphagenome/blob/038d253a5ca2fec46f4874f592d9ec67984cb497/README.md#terms)
limits output/Atlas training use except where its terms explicitly permit
specified downloadable artifacts. The linked terms page could not be fetched
in this inspection. Artifact-specific use, redistribution, and downstream
training eligibility are unresolved. This is a preliminary source-terms reading,
not legal advice. Replaying an output does not change its eligibility. Inspect
permissive downloadable artifacts before considering a training-data route.

[Atlas API reference](https://www.alphagenomedocs.com/api/generated/alphagenome.atlas.atlas.AtlasClient.html)
was inspected on October 6, 2026. A completed Atlas notebook or analysis document
is still needed to make this a notebook-conversion example rather than authoring
an analysis from API documentation.
