Independently review a generated reference preparation against the ORIGINAL
notebook narrative and untouched converted script. Return ReferenceReview via
the artifact submission tool. Do not merely check the proposed inventory for
internal consistency. This review does not establish execution success or
scientific correctness.

Look for every intended scientific analysis branch and endpoint, including
results expressed through plots. Underlying plot data is acceptable only when
it preserves consequential transformations, identities and labels. Identify
omissions even when the proposed branch map does not mention them. Explain
reasonable exclusions of incidental displays or styling.

Inspect the exact source diff and setup script. Permit environment reconstruction,
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
