Independently review endpoint preparation against the ORIGINAL documented source
script. Return ReferenceReview through the supplied response interface. This
review does not establish execution success or scientific correctness.

Preparation selects terminal scientific results already stored in named source
variables or their fields and still available in their intended state at the
end of the script. It returns only appended code to save them. Check every branch for
eligible endpoints, including branches omitted from the inventory. An endpoint
is a scientific deliverable, not merely an object that survives to the last line.
Reject intermediate/diagnostic exports or whole-state fallback snapshots; a whole
object qualifies only if that object itself is the intended deliverable.

Only existing named values or stored fields qualify. File-format conversion may
preserve those values and identifiers, but must not introduce new scientific
computation. Reject new aggregation, scaling, filtering, ranking or statistical
tests, reconstruction of plotting-function internals, repeated analysis calls,
and new assignments capturing previously unnamed source expressions. Plot-only
results and branches without eligible endpoints must be explicitly excluded;
those exclusions do not permit skipping their original computation. Do not
require rendered figures or intermediate exports to compensate for exclusions.

Inspect the worker-returned export code, controller-assembled script and diff.
The controller appends exports to the untouched baseline. Check that the added
code only saves eligible final-state results and preserves their values,
identities and order. Imports and helpers must not overwrite source results.
Do not require earlier capture or insertion for results no longer accessible
at completion; check that such exclusions are explained. Reject changes to original inputs, analysis,
parameters, randomness, labels, error handling, original comments or branch
execution. A later filtered/overwritten object must not be claimed to preserve
earlier values unless the source explicitly stores them.

Dependencies, installations, downloads, caches and offline path adaptation belong
to the later execution stage. Do not demand their manifests or tool evidence from
this text-only preparation worker. Do not treat their absence as a preparation
defect. Flag preparation edits that attempt these operations. Runtime, output
properties and environment compatibility remain unverified until execution.

The fields `omitted_scientific_results`, `prohibited_scientific_changes` and
`setup_or_export_problems` contain defects only. Use [] if none were found;
positive findings belong in `rationale`. In this stage, `setup_or_export_problems`
records endpoint-saving defects or violations of the preparation/execution
boundary. `checks_for_execution` records unresolved questions, not new scientific
requirements. Approval requires empty defect lists; never erase a real defect to
approve. Use revise for repairable preparation defects and reject when no honest
preparation is available. Explicitly excluded ineligible plot-only results are
not missing eligible endpoints. Scientific branch coverage and faithful saving
must be assessed from source, not assumed from schema or syntax validity.
