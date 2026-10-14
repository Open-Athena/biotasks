Independently review a generated reference preparation against the ORIGINAL
documented source script, whose comments retain the original notebook narrative. Return ReferenceReview via
the artifact submission tool. Do not merely check the proposed inventory for
internal consistency. This review does not establish execution success or
scientific correctness.

The fields `omitted_scientific_results`, `prohibited_scientific_changes` and
`setup_or_export_problems` are DEFECT LISTS. Use an empty JSON array `[]` when
none were found. Do not put positive findings, permitted changes, or sentences
such as "none detected" in those lists; put that evidence in `rationale`.
Approval requires all three lists to be empty. Never erase a real defect to
obtain approval: choose `revise` or `reject` instead. `checks_for_execution`
records unresolved observations to examine after execution, not new scientific
requirements or permission to change the source.

Look for every intended scientific analysis branch and endpoint, including
results expressed through plots. Underlying plot data is acceptable only when
it preserves consequential transformations, identities and labels. Identify
omissions even when the proposed branch map does not mention them. Explain
reasonable exclusions of incidental displays or styling.
Image files alone do not establish the scientific values behind a plot. Do not
require rendered image exports, a separate artifact for every intermediate, or
detailed profiling. Review the source's endpoint data and complete branch
coverage; several endpoints may share an artifact with an explicit mapping.

Inspect the exact source diff, dependency manifest, declared system packages and
input-staging script. Environment creation and package installation are controller
operations; input staging must not implement them. Permit environment reconstruction,
faithful input staging/path changes and exports of existing results. Reject
changed scientific parameters, formulas, algorithms, labels, random seeds,
added reductions/checkpoints, skipped branches, suppressed errors, precomputed
answers or exports that change analysis state. Setup must not execute analysis.
Inputs must be the original inputs used by the source. Preserve source-level
subsampling if present. A worker calling a change 'setup' does not make it so.

Check that dependencies, offline inputs/metadata/caches, fresh-process execution,
artifact paths, identifiers and export timing are coherent. Static inspection
can flag problems; it cannot invent measured resource use, schemas or results.
Record uncertainties as execution checks when they can only be resolved by a
run. A known setup/export defect requires revision. An inherent source defect
or policy conflict requires rejection. Approve only if the proposed reference
faithfully covers all source scientific endpoints with no known blockers.
