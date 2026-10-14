# Reference preparation, run 004

Inspect the [initial draft](creation.md) and [repair draft](repair.md).
**No accepted preparation plan was produced.** Both GLM-5.3 responses passed the
exact JSON Schema supplied in their requests, but failed the controller's
additional admission checks. No generated setup or analysis code was executed.

The initial draft declared three artifacts and two branches. Four of its six
source-edit anchors did not occur in the supplied baseline. Some quoted source
contains literal invented placeholders such as `.LockQuote` and `tmpn`; the
baseline contains no `.LockQuote` strings. The controller rejected the plan
before producing a reference script.

The single allowed repair returned all required fields, but empty artifact and
branch arrays despite choosing `disposition=prepare`. All five source-edit
anchors also failed to match the baseline. The controller rejected the empty
coverage map and stopped. See [recorded validation and local schema/anchor checks](inspection.json).
Both responses ended with `stop`, not a reported output-length truncation.

This run resolves the narrow missing-field observation from run 003: required
fields and types conform to the schema in these two responses. It does not
establish reliable preparation, scientific fidelity, or the cause of the
corrupted source quotations. JSON Schema cannot establish that a string matches
source code, or that a declared scientific inventory is faithful and complete.
The empty lists are permitted by the JSON Schema but rejected by the plan's
cross-field validation for the `prepare` disposition.

The worker used [checkpoint 8355040](https://github.com/Open-Athena/biotasks/commit/8355040f54a39f4bd6acb8dbde6eb89336c21de0),
GLM-5.3 with medium reasoning, strict JSON-schema response format, one creation
and one complete-object repair. The repair received the original input and full
prior response plus validation feedback; it was explicitly told to return every
field, not a patch. No client output-token/input-byte/response-byte cap was set;
the per-request timeout was 600 seconds. Preparation took 711 seconds and used
21,964 prompt and 100,755 completion tokens, including 91,399 reported reasoning
tokens. [Run receipt](run-receipt.json).

All 15 original preparation evidence files were recovered and hash-verified.
The [exact input](prepare/input.json), [prompt](prepare/system-prompt.md),
requests, responses, controller trace and rejected draft remain unchanged.
`creation.json` and `repair.json` extract the response content; their Markdown
views are mechanical renderings with separate validation annotations, not fixed
plans. No runnable reference or accepted environment bundle was materialized.
The remote job is terminal (`FAILED`). No Daytona sandbox, setup, reference
execution, independent model review, construction, solver or replacement run
was launched. The HTML viewer was not updated.
