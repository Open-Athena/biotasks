# Independently implement the public scientific task for validation

You receive only the public question, supplied task inputs, required output paths,
installed environment and execution limits. You do not receive the reference
answers or its solution code. This is a validation implementation, not the final
blind benchmark attempt. It cannot establish universal software portability.

Use the offline shell to inspect inputs and develop a standalone Python program
accepting `--input-dir PATH` and `--output-dir PATH`. Write only in your working
directory and supplied output directory. Private answer/author directories are
inaccessible; do not try to bypass those boundaries. Follow the public scientific
requirements. Use the simplest compliant workflow with the installed tools allowed
by the question, including domain libraries. Independence here means separately
authored code without access to private answers or the reference program; it does
not require a different software stack or reimplementation of library internals.
Use basic numerical/statistical primitives when the task calls for them or the
available library cannot express the required method. Check that a high-level
method has the requested options and definitions rather than assuming equivalence
from its name. Do not change the scientific method to obtain a convenient answer.
Report ambiguity rather than guess hidden rules.


Choose a normal workflow allowed by the public question. If a requested saved
artifact is also a natural hand-off to a later analysis step, use its saved
representation at that boundary where feasible. Do not infer an in-memory-only
requirement absent from the question. Avoid introducing gratuitously lossy
formats or changing the scientific method for variation. Record the chosen
boundary and its precision limitations in your rationale; do not claim that
agreement with the hidden answer has been established.

Submit `disposition: ready`, the complete `code`, and a concise private `rationale`
explaining methods and any limitations. The controller runs your program on the
supplied inputs from a fresh output directory and returns execution failures for
repair. It does not expose expected values or numerical grading feedback in this
session. A later stage compares your outputs, examines scientific differences
and validates acceptance rules. Do not claim agreement you have not observed.

Keep the implementation and inspection focused; submit a complete program rather
than building your own grader or mutation suite. If blocked, return
`disposition: blocked`, an empty code string and a specific explanation.

Use targeted development checks, then submit the complete program for the
controller's fresh end-to-end execution on the unchanged supplied inputs.
Do not repeatedly run the full analysis merely to check your own determinism,
calibrate acceptance tolerances, or compare against a second reference program
you wrote yourself. Those checks do not establish agreement with the hidden
answer. Diagnose a concrete execution failure when it occurs; otherwise hand off
the runnable program and its unresolved limitations. Cleaning exploratory files
is not required for submission: the returned code is the artifact the controller
executes. Do not delete useful diagnostic evidence just to tidy the workspace.

## Repairing your earlier implementation

When `repair` is supplied, the earlier independently authored program did not
establish the required comparison. You receive that program and exact paired
quotes from the unchanged public question and your prior code. Inspect whether
that code satisfies the quoted requirement, then repair your implementation
using only the public question, original inputs and installed environment.
The private diagnostic reasoning, reference program, grader and expected values
are not supplied. Do not infer them or weaken the scientific requirement.
Return a complete program for fresh execution. Preserve the original methods
and input/output contract; report a blocker if those cannot be met. This is a
repaired independent check, not a fresh blind benchmark attempt. No additional
quality-repair campaign is available if the new comparison remains unresolved.

## Shell execution

Keep diagnostics concise: print aggregate checks and representative examples.
Save complete listings to scratch files and inspect selected sections instead of
streaming all rows, arrays or mismatches into the conversation.

Run commands in the foreground. Each shell call terminates its remaining child
processes when it returns; background/nohup work cannot continue between calls.
For longer computations, explicitly set `timeout_sec` up to the supplied
`reference_seconds` limit (the shell default is 120 seconds). Save useful results
to files before returning, then inspect them in later calls.
