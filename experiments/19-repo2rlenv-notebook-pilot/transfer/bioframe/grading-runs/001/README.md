# Bioframe grading 001 — incomplete, not a release candidate

The unchanged-prompt transfer campaign timed out during the repair stage. Its
recorded result is `incomplete` / `TimeoutError`, with no completed repair,
final grader or final review. No Harbor solver or publication ran. The stage
record spans **6,889.51 seconds (114 min 49.5 s)**; the configuration reserves
five minutes of its two-hour campaign window for cleanup. There were **244 GLM
requests**: independent implementation 82, grader 32, probes 124, review 1,
repair 5. This is not evidence of reliable two-hour task production.

The reference has 40,557 rows; the answer-isolated independent implementation
produced 40,572. Fifteen input coordinate keys occur in multiple peak records
with conflicting fold-change annotations. The reference collapses these keys;
the independent implementation retains both records. Their shared rows agree
numerically. The public question calls for distinct intervals and one row per
retained sub-interval but does not resolve the conflicting annotation values.
The notebook itself executed successfully: this is a generated contract and
validation problem, not a demonstrated failure of the source notebook.

The first grader submission rejected the extra records. The controller required
the independently executed output to pass, despite not having established that
it was scientifically correct. In response, the worker broadened its comparator
and addendum to admit additional annotation values when the reference value is
also present. That candidate passed five basic controls and nineteen independently
authored probes. The review requested revisions to formatting claims, check
attribution and validation explanations, while explicitly excusing the
unverifiable additional values as a controller-forced accommodation. The repair
never completed within the working window.

Those passes do not establish a sound comparison rule: preserving correct
answers while adding unsupported values is not sufficient justification for an
accepted alternative. `operator-inspection.json` records the release hold
separately from the original execution result. Neither the task question nor any
solution, grader or probe was manually repaired. Original submitted candidates,
controls, prompts and review are retained unchanged.

A later factory version stops an unresolved independent comparison before
further grader calibration, rather than making that output an answer target.
It also asks construction to make identity/multiplicity rules explicit and
requires probes/review to challenge unsupported additions. These are general
changes; their model behavior still needs a fresh run.

The full 1,316-file campaign archive passed remote download verification. This
Git snapshot retains 88 small original files with their original hashes. Three
recorded input payloads were rebuilt losslessly from the original components and
verified against the original archive hashes; recovery methods are recorded in
`artifact-manifest.json`. The bounded diagnostic log transfer did not recover the
entire archive. Full model/tool traces and large outputs remain in the configured
private archive. Unsubmitted sandbox working files were removed with the sandbox;
recorded tool requests/results preserve the failed repair attempt, but there is
no completed repair artifact to inspect.

The worker reported successful cleanup. A separate provider lookup confirmed
**zero owned Daytona sandboxes**, and the Iris job is terminal. Budget reservations
are not an invoice; no measured billing claim is made here.
