# Reviewing observed endpoint coverage

Status: the first pass inspected all eight reference artifacts in 11.10 seconds,
with original hashes unchanged. Both model calls hit the 32,000-token output
limit; no proposal was accepted and no separate review ran. Unedited structural
evidence and request accounting are in [run 001](coverage-runs/001/summary.json).

The continuation keeps the same evidence and scientific scope. It requests concise
structured output and uses low reasoning effort rather than medium. Four proposal
and three review requests remain; the first pass's two requests are retained in
the nine-request coverage allowance. No truncated tool call is accepted.

This stage consumes an immutable successful reference run. It does not rerun
the analysis, execute generated code, create a Daytona sandbox or invoke a
solver. Its result is an endpoint proposal and separate review, not a frozen
grading contract or a claim of scientific validation.

1. Retrieve the declared output files from the prior private archive. Check
   their sizes and SHA-256 hashes against both the pinned inventory and archive
   manifest. The private archive location is supplied through the Iris process
   environment, never a public configuration or model prompt.
2. Inspect CSV/TSV files with streaming row/column counts, missing and nonfinite
   values, numeric ranges, bounded distinct counts and ordered column hashes.
   Inspect HDF5 encodings, dataset shapes and bounded previews without loading
   full matrices. No soft/external links are followed. Unknown formats are
   explicitly unsupported. Recheck file hashes after inspection.
3. GLM proposes scientific endpoints from the original narrative and scripts,
   executed diff and observed profiles. It distinguishes scientific endpoints
   from shared preprocessing and incidental displays, accounts for every
   scientific branch, and separates reference storage from proposed portable
   solver outputs. Prior worker descriptions are claims to check, not facts.
4. A separate GLM call reviews completeness and evidence against the original
   source. Known omissions, unsupported claims or scientific scope changes
   block approval. A proposal can instead request further reference work or
   reject the candidate. All outputs and failures remain preserved.

The configuration allows six proposal requests and three review requests,
including structured-output recovery. Combined with the successful reference
campaign's seven requests, the maximum is sixteen of the eighty-request pipeline
allowance. This pass has no semantic repair loop and does not reset prior usage.
The existing two-hour Iris job ceiling applies; retrieval/environment setup is
bounded to thirty minutes and structural inspection to ten minutes. The worker
uses two CPUs and 4 GiB RAM on already authorized reserved capacity. No additional
Daytona reservation is needed. GLM remains the approved free endpoint.

HDF5 inspection uses the same pinned h5py and NumPy versions recorded by the
reference environment, in a separate small environment. It follows the documented
[HDF5 group traversal](https://docs.h5py.org/en/stable/high/group.html) and
[dataset metadata interfaces](https://docs.h5py.org/en/stable/high/dataset.html).
CSV inspection is capped at one million rows, 256 columns and one million stored
distinct-value hashes across columns. An exceeded cap fails explicitly. Previews
and structural summaries do not establish whole-array scientific properties.

`coverage_proposed` means both workers support advancing to contract drafting.
It does not establish that representation choices or numerical tolerances have
passed executable controls. Missing plot statistics may require faithful export
work; derivable results must be labeled unverified until computed and checked.
Subsequent construction still needs reference, no-op, missing-branch,
wrong-method/result and independently conforming checks before freezing grading.
