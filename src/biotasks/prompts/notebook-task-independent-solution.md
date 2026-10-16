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
