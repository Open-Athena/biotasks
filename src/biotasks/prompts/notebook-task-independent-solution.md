# Independently implement the public scientific task for validation

You receive only the public question, supplied task inputs, required output paths,
installed environment and execution limits. You do not receive the reference
answers or its solution code. This is a validation implementation, not the final
blind benchmark attempt. It cannot establish universal software portability.

Use the offline shell to inspect inputs and develop a standalone Python program
accepting `--input-dir PATH` and `--output-dir PATH`. Write only in your working
directory and supplied output directory. Private answer/author directories are
inaccessible; do not try to bypass those boundaries. Follow the public scientific
requirements. Prefer an independent implementation from basic numerical/statistical
primitives where practical; do not simply assume a high-level method with a similar
name has the requested options or definitions. Do not change the scientific method
to obtain a convenient answer. Report ambiguity rather than guess hidden rules.

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

## Shell execution

Keep diagnostics concise: print aggregate checks and representative examples.
Save complete listings to scratch files and inspect selected sections instead of
streaming all rows, arrays or mismatches into the conversation.

Run commands in the foreground. Each shell call terminates its remaining child
processes when it returns; background/nohup work cannot continue between calls.
For longer computations, explicitly set `timeout_sec` up to the supplied
`reference_seconds` limit (the shell default is 120 seconds). Save useful results
to files before returning, then inspect them in later calls.
