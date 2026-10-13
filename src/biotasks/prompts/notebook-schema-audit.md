Audit the public artifact schema against the grader. You receive a mechanically
extracted inventory of Python literal-key accesses plus task source evidence.
Return one obligation per distinct inventory expression, exactly once. Do not
edit the task. Separate submission fields from reference-only variables,
internal test bookkeeping, and optional lookups guarded by alternatives.

For each expression, determine whether a valid submission must provide the
exact named key for the grader to run and pass. Check the public instruction's
actual wording: a name offered with "e.g." or "for example" is optional, not a
mandatory schema. A name merely used by the reference is not a public requirement.
An absent mandatory name is a contract defect even if all tested solvers happened
to use that name. Mark internal/reference-only access not_applicable.

Cite short exact source passages supporting each decision. For every mandatory
key that is optional or absent publicly, explain the mismatch and propose a
minimal repair that preserves the biological methodology and software choice.
Do not weaken scientific tests or hand-edit results. Usually the appropriate
repair states the existing required artifact schema explicitly; where the public
contract intentionally permits alternative keys, the grader must honor it.
