# Diagnose a comparison or public-question defect

One independently authored implementation disagrees with the fixed reference and
grader. Other basic controls passed. Diagnose the defective artifact from the
recorded evidence before choosing the existing single quality-repair route.
Independent execution alone does not prove either implementation correct.

Alternatively, `semantic_question_review` identifies an exact-quoted false or
ambiguous base-question claim even though the basic numerical controls passed.
In that case only `allowed_targets` may be selected. Correct the public wording
from source/input/package evidence; do not alter an already matching independent
implementation or the scientific target to accommodate prose.
Passing controls do not validate an explanation those implementations ignored.

Inspect `revision_context`: the original public question and materialization,
independent code/execution, grader and measured conflict. Original source and
reference evidence, repeated execution and read-only package/reference inspection
are also supplied. Do not change the scientific analysis, reference, inputs,
selected outputs or scientific acceptance criteria to make a comparison pass.
A statement by a previous worker is a claim to check, not evidence by itself.

Return one of these targets using the response schema:

- `public_question`: an omission or false methodological statement in the public
  question prevents a correct independent implementation. Return complete corrected
  `instruction` text, preserving the scientific target and fixed assets, with no
  `independent_issues`. Explain the source-backed correction privately. When the
  same recorded review also identifies grader/addendum/probe-annotation defects,
  include their coherent correction in `grader_repair`, using the existing typed
  repair fields. Do not freeze a known defect merely because the question also
  needs correction. Return null when that component is already sound. Preserve
  all check identities, kinds and artifact associations; only their explanatory
  descriptions may be corrected. Probe scripts, names, focus and source citations
  remain fixed. Annotation changes require evidence from the unchanged mutation
  and scientific requirement, and all scientific checks retain wrong-result
  coverage. If a mutation or scientific target itself needs changing, block.
  The controller binds the repair to the original inventory, retains the original
  suite, and runs it again against the revised candidate, with fresh independent
  execution and review. Passing old controls is not acceptance of the revision.
- `independent_solution`: the question states the required convention correctly,
  but the independent code does not implement it. Keep `instruction: null`. Each
  `independent_issues` entry contains an exact `public_requirement_quote` from the
  existing public instruction and an exact `prior_code_quote` from that worker's
  submitted code. Choose the relevant requirement and suspect code; do not insert
  replacement code, reference values or private evidence into these quote fields.
  Keep `grader_repair: null`: this route supplies only public/prior-code feedback.
- `none` with `disposition: blocked`: evidence is insufficient, a scientific asset
  needs changing, or neither available repair can resolve the conflict. Return
  `instruction: null`, `grader_repair: null`, an empty issue list and the concrete
  private rationale.

Verify proposed corrections against the actual definitions and their conditions.
Do not copy a reviewer's illustrative example without checking that it follows
from the rule being explained. Prefer a concise identified standard or reference
procedure where it disambiguates the method; do not invent a function-by-function
recipe or an unnecessary textbook explanation. For standard output formats,
prefer the installed native reader when available, and distinguish scientific
values from harmless supported representation differences. A code defect may be
fixed to implement the unchanged scientific criterion; a new tolerance or weaker
criterion cannot be introduced just to accommodate a failed control.

Only the exact public-question and prior-code quotes are forwarded for an
independent implementation repair. Your private rationale, reference outputs,
grader and failed-control messages are not forwarded. The isolated worker must
repair its own implementation from the unchanged public question and inputs; its
outputs still face the unchanged grader and fresh controls. This is a repaired
independent check, not a new blind solver attempt or proof of broad portability.

This diagnosis and the resulting fresh validation use the existing one
quality-repair allowance and absolute campaign deadline. It does not authorize a
second repair campaign, data substitution, weaker criteria or operator task edits.
