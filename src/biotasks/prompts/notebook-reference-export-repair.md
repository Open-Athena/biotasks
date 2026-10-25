Repair only the appended export code after a recorded runtime export failure.

## Input

`baseline_script` is the unchanged converted scientific source. `source` and
`conversion` identify it. `runtime_validation.previous_plan` is the frozen
endpoint selection and original export code. `runtime_validation.feedback`
contains the controlled failure, observed layout and source/export locations.
Use those observations rather than inventing values, shapes or representations.

## Output

Return one JSON object containing only `export_code` and `explanation`.
`export_code` is the complete replacement append-only export block, not a patch
or the original script. Explain the observed error and the serialization fix.
The controller keeps the original endpoint inventory, paths, descriptions,
source evidence, exclusions and other plan metadata unchanged. Do not restate
those fields in your response.

If the observed problem cannot be fixed faithfully within this frozen scope,
return `export_code: null` and explain the blocker. Do not invent replacement
results or change the endpoint selection to make a repair possible.

Save the same selected scientific results to the same declared output paths.
Correct serialization, indexing or access to the existing terminal objects.
Preserve identifiers and scientific values. Do not change the scientific source,
recompute an analysis, select new results, omit required results, stage data,
install dependencies or recreate information computed only inside a plot.

This is the existing single repair attempt, not another creation or validation
campaign. There are no tools or runtime execution here. The execution worker
must retest the replacement within its remaining allowance; successful JSON or
compilation is not evidence that the scientific reference ran successfully.
