# Design-only response for review

[Read the model's draft specification](draft-spec.md). This is the unmodified
`draft_spec` field from one GLM-5.3 response to the reviewed task-design prompt.
No construction, repair, native validation or solver execution followed it.
The HTML viewer was not changed.

The call used the full Scanpy PBMC3k notebook seed, the exact canonical prompt
without appended instructions, low reasoning effort, a 9,000-output-token cap,
and no retries. The response finished normally in 82.88 seconds and passed the
JSON/schema checks: 6 capabilities and a 9,415-character draft. Token usage was
6,869 input and 2,649 output tokens. This proves response receipt and format only,
not scientific validity or task feasibility.

- `request.json`: exact model request, including prompt and seed.
- `response.json`: returned completion and call timing.
- `model-output.txt`: verbatim JSON message content.
- `draft-spec.md`: verbatim extracted Markdown field.
- `manifest.json`: source revision, request/prompt hashes and settings.
- `summary.json`: outcome and explicit stage boundaries.

## Initial review observations

These notes are separate from the preserved model response and have not been
applied as corrections.

- The Methodology paragraph's `log(10000)` statement conflicts with test 6. For
  log1p-normalized values, the relevant row-sum invariant is
  `sum(expm1(X[i, :])) ≈ 10000`, not a sum of logged values equal to `log(10000)`.
- Test 5 checks gene prevalence after cell filtering, although the specified
  three-cell gene threshold is applied before that filtering. Removing cells can
  reduce a retained gene's detection count; these two contracts are not equivalent.
- `.X` versus an unspecified named layer, and the meaning of
  `n_cells_before_filter`, need clarification before construction.

No scientific verification was run. The user will inspect this response before
advancing to another pipeline stage.
