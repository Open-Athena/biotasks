# Diagnose an independent-comparison conflict

One independently authored implementation disagrees with the fixed reference and
grader. Other basic controls passed. Diagnose the defective artifact from the
recorded evidence before choosing the existing single quality-repair route.
Independent execution alone does not prove either implementation correct.

Inspect `revision_context`: the original public question and materialization,
independent code/execution, grader and measured conflict. Original source and
reference evidence, repeated execution and read-only package/reference inspection
are also supplied. Do not change the scientific analysis, reference, inputs,
selected outputs, grader, tolerance or acceptance criteria to make a comparison
pass. A statement by a previous worker is a claim to check, not evidence by itself.

Return one of these targets using the response schema:

- `public_question`: an omission or false methodological statement in the public
  question prevents a correct independent implementation. Return complete corrected
  `instruction` text, preserving the scientific target and fixed assets, with no
  `independent_issues`. Explain the source-backed correction privately.
- `independent_solution`: the question states the required convention correctly,
  but the independent code does not implement it. Keep `instruction: null`. Each
  `independent_issues` entry contains an exact `public_requirement_quote` from the
  existing public instruction and an exact `prior_code_quote` from that worker's
  submitted code. Choose the relevant requirement and suspect code; do not insert
  replacement code, reference values or private evidence into these quote fields.
- `none` with `disposition: blocked`: evidence is insufficient, a scientific asset
  needs changing, or neither available repair can resolve the conflict. Return
  `instruction: null`, an empty issue list and the concrete private rationale.

Only the exact public-question and prior-code quotes are forwarded for an
independent implementation repair. Your private rationale, reference outputs,
grader and failed-control messages are not forwarded. The isolated worker must
repair its own implementation from the unchanged public question and inputs; its
outputs still face the unchanged grader and fresh controls. This is a repaired
independent check, not a new blind solver attempt or proof of broad portability.

This diagnosis and the resulting fresh validation use the existing one
quality-repair allowance and absolute campaign deadline. It does not authorize a
second repair campaign, data substitution, weaker criteria or operator task edits.
