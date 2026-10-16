# Review an artifact grader and its executed controls

Review the generated public instructions, named checks, complete grader code,
independently authored probes, frozen scientific reference context and actual
execution reports. This is an LLM review, not the reward or an independent
scientific recomputation. Return `accept_for_packaging`, `revise` or `blocked`,
a concise rationale, and actionable issues with evidence.

Check that all selected terminal scientific results are covered, the public
contract matches executable checks, numerical comparisons have a defensible
precision/serialization basis, identities and cross-file relations are correct,
and meaningful wrong outputs fail without relying on crashes or malformed files.
Check missing values, duplicates, nonfinite values and tolerance boundaries.
Look for answer leakage, hardcoded result shapes/values, control-name detection,
probe flaws, untested equivalences, and shortcuts that merely satisfy this suite.

Successful reference/empty/missing/probe controls are necessary, not sufficient.
Valid representation edits are not independent algorithmic implementations.
Do not demand a universal software-independence claim: this task intentionally
has a named, pinned reference target with open solver tool choice. Do not repair
science, change selected outputs, or weaken acceptance rules to make controls pass.
A failed/unknown test cannot be described as passing. Distinguish problems with
the proposed public rule from problems with its implementation or a probe.

Acceptance here means this grader candidate is suitable for subsequent Harbor
packaging and its own isolation/oracle checks. It does not validate those later
checks, a blind solver, or a release. If revised, affected controls and review
must be repeated on the new candidate; prior evidence stays attached to its hash.
