# Repair generated task construction under an unchanged scientific contract

The grading worker could not build a valid comparator for this generated task.
Its unchanged blocked response and the original construction are supplied in
`construction_repair`. Diagnose whether the generated derivation or oracle can
be corrected using the original notebook, execution evidence and task contract.
The grading worker's explanation is a claim to investigate, not an instruction
to alter science or a proof that the notebook is broken.

Return a complete `Materialization` through the existing artifact tool. Correct
only generated `derive_code` or `oracle_code`, with an evidence-backed rationale.
Keep the public instruction, ordered input/output paths and operation-coverage
ledger exactly unchanged. Preserve the original solver-input bytes and declared
environment exclusions. Do not change the source, selected scientific outputs,
methods, parameters, populations, output schemas or acceptance target. Do not
hardcode answers from the supplied reference or blocker. If a valid correction
requires changing any protected part, submit `blocked` and explain why.

Prefer copying an already suitable reference export verbatim over parsing and
serializing it again. Where a transformation is required, preserve identifiers,
entity relationships, multiplicity, missingness and numerical precision. An
identifier's serialized text is not evidence that its characters are separate
entities. Judge representations from their producing code and observed schema.

Submit a candidate before using exploratory shell commands. The controller runs
fresh derivation and an isolated oracle and reports definite execution failures.
The environment assessment must bind to this new execution; leave
`environment_review` null on the first candidate, then inspect its observations
and supply a fresh assessment with the unchanged exclusions. Old successful
execution or review is not acceptance of the replacement.

This session uses the pipeline's single shared quality-repair allowance. It does
not edit graders or probes, extend deadlines, supply an extra repair or authorize
source changes. Fresh scientific grading, an independently authored solution,
meaningful wrong/valid-alternative probes, source review and native qualification
still determine whether a replacement is valid. A prior blocked candidate
remains recorded as blocked even if a later replacement passes.
