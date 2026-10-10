# Proposed additional repair campaign — not authorized or launched

The final candidate has successful native controls and a successful blind solve,
but a GLM repair failed to establish reference-input integrity. Its scientific
review also exceeded the citation span limit. The current ten-replacement
allowance is exhausted. This proposal does not change that allowance.

The prepared reusable prompt changes explicitly classify mutable reference data
as blocking, distinguish matching copies from independent identity, and require
citation-span self-checks. They do not edit any generated task, supply a
notebook-specific repair, or relax a release gate. No new execution evidence
supports these prompt changes yet.

Propose one additional campaign starting from the final generated candidate,
with its unchanged native controls imported by checksum. Allow GLM one quality
repair, then at most five fresh native trials (no-op, reference, wrong analysis,
valid alternative, and one blind solver). Run a fresh scientific review. Reject
rather than publish if the same defect survives. Reusing prior evidence must
never bind old results to a changed task.

Proposed additional ceilings: 40 API requests (16 quality/review, 24 solver),
one five-minute solver attempt with at most 12 turns, five scientific trials
plus one infrastructure preflight, two hours plus five minutes cleanup, and $5
Daytona usage before credits. Use the existing reserved Iris 2-CPU/4-GiB host
and one active 1-CPU/2-GiB/10-GiB Daytona sandbox; no GPU, no parallel campaigns,
GLM-5.3 only, offline solving/grading. These are new proposed allowances, not
unused allowances silently carried forward. Actual launcher/accounting support
must be checked before submission; a new source revision must be frozen.

If approved, first confirm that the upstream repair path can import the final
candidate's controls without repeating generation or resetting historical usage.
Preserve separate historical and additional-budget ledgers. No manual task,
solution or grader repairs. Publish through the already approved release path
only if every existing release gate passes, followed by a fresh download check.
