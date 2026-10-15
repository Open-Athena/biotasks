# Specification run 002: structurally valid, not accepted

The compact input produced a complete response in one GLM-5.3 medium call
(497 seconds; 28,598 prompt tokens, 57,168 completion tokens, including 51,396
reported reasoning tokens). The worker selected `draft_ready`. Schema acceptance
is not semantic acceptance: source/content review found substantive blockers.

Original outputs: [public brief](task-brief.md), [worker review](review.md),
[validation plan](validation-plan.md), [structured response](specification.json).
Their formatting and contents remain unchanged.

## Inspection findings

- The brief proposes unmeasured numeric tolerance values and commits to comparison
  criteria not yet validated. The plan repeats these values rather than leaving
  them to measurements.
- It admits consequential defaults/formulas still need inspection while treating
  them as known in a ready public brief. A version pin alone is not that evidence.
- It assigns `n_iterations=2` to all clustering calls. The source sets this
  override on the first call; the later resolution loop omits the argument.
  The default for those later calls needs inspection, not copied settings.
- Partition renumbering is allowed while the annotation instructions depend on
  hidden reference numbering. That equivalence needs a consistent public rule;
  the worker must not invent a new biological annotation rule.
- Markdown sections were flattened into long lines, making inspection difficult.

The source DOES call `obs_names_make_unique()` after concatenation. The earlier
operator concern inferred from a duplicate-name warning was too strong; that
warning precedes the explicit disambiguation. Preserve the actual source behavior
rather than imposing a manually chosen composite-key scheme.

The next prompt revision makes evidence sufficiency an initial gate, preserves
arguments per invocation, forbids numeric guesses even in the private plan, and
requires consistent equivalences and readable Markdown. These rules do not name
this notebook, its packages or desired output values.

The host is terminal (SUCCEEDED). No scientific rerun, sandbox, construction or
solver occurred. No original worker output was manually repaired.
