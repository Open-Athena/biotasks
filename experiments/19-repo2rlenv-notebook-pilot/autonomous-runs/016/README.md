# COBRApy first attempt and source-code rejection decision

The first attempt used the same frozen factory as MDAnalysis 015:
`da37f25d940bf82406676a07205a491e12dcf346`. Preparation, setup, replay and
specification completed. Construction returned a blocked diagnostic candidate
whose rationale was to isolate a schema-validation failure. The pipeline recorded
`rejected` / `worker_declined`, with zero operator interventions. It did not reach
grading or a solver. This is not evidence of successful scientific task validation
or of the pipeline automatically detecting the missing-import defect below.

The setup worker added `import cobra` to the original source, which otherwise
uses `cobra.flux_analysis` without binding `cobra`. Dependency installation was
successful; the edit repaired source code. Preserve the original worker outcome,
including its incorrect claim that Jupyter automatically supplies that binding.
An earlier kernel import could explain the notebook's stored successful execution,
but that history has not been established.

After discussion, the user decided to reject notebooks requiring this kind of
source-code repair for now. `source-policy-decision.json` records that decision
separately from the original construction decline. The new general setup prompt
distinguishes missing installed packages from missing source imports, and a
controller guard refuses changed import statements before setup/reference
execution. Twenty focused setup tests pass, including import additions, removals,
alias changes, changed from-imports, and permitted path adaptation with original
imports. No new cloud run under this policy has been performed.

The pipeline had already terminated before a requested stop was needed. The host
finished successfully, all stage cleanup receipts passed, and fresh provider
inventory verified zero owned sandboxes. Original small receipts were recovered
with hash checks. No generated task was manually repaired or published.
