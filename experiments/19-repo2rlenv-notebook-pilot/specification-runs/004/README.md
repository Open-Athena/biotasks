# Specification run 004: useful evidence gaps, response not accepted

One GLM-5.3 medium call returned `needs_evidence` and correctly left the public
brief empty. Its review recognizes the difference between explicit arguments and
omitted defaults, including distinct invocations of the same function. It asks
for implementation evidence that is absent from the supplied context.

The complete response is still not satisfactory. The private plan chooses exact
reference labels and coordinates before settling scientific equivalence, later
permits group alignment inconsistently, and treats a cell-row permutation as a
wrong-method control despite key-based comparison. It also introduces speculative
numerical boundaries. Much of the prose is in Chinese, with literal `n` characters
instead of Markdown line breaks and occasional garbled text. These defects are
present in the original model content, not introduced by file rendering.

The [review](review.md), [validation plan](validation-plan.md) and
[structured response](specification.json) are unedited. The
[response summary](response-summary.json) records one completed call in 331.3
seconds: 29,112 prompt tokens, 42,201 completion tokens (38,608 reasoning), finish
reason `stop`. All seven retained small files match archived hashes.

Iteration 005 simplifies the general prompt: a blocked review requests only the
specific missing evidence; full task drafting and grading design apply only when
that evidence is sufficient. It clarifies that reference repeatability alone does
not establish correctness across conforming implementations. Context, schema,
model, reasoning setting and one-call stage contract are unchanged. No manual
correction of the generated response or seed-specific method is supplied.

Host terminal: SUCCEEDED. Factory content inspection: not accepted.
No sandbox, scientific rerun, construction, solver or viewer update.
