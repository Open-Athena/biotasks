# Correct explanations in an already executed acceptance contract

You receive a task, a grader candidate whose controls passed, and review feedback.
Return corrected public acceptance text and a private rationale using the supplied
schema. This is a prose-only stage: no shell or scientific execution is needed.
The controller retains the exact grader code and check inventory, then reruns the
controls and review. Do not reconstruct or return grader code.

Preserve the scientific task, all acceptance criteria, numerical thresholds,
comparison formulas, required outputs and allowed representations. Correct only
misleading explanations, unsupported guarantees, and placement of private
validation history. State what the comparator actually checks; do not claim that
all implementations of a wrong method must fail. Distinguish a measured example
from a universal guarantee. Numerical tolerances necessarily permit differences
below their thresholds. Do not invent a scientific rationale for a safety margin.
Keep uncertainty and empirical calibration in the private rationale; retain the
clear numerical rules publicly. Do not change a tolerance to make its explanation
easier. If the feedback requires changing executable behavior or the scientific
target, return blocked with the reason instead.

`instruction` is the complete replacement acceptance addendum only. `rationale`
is private and explains the corrections and remaining limitations without claiming
new tests ran. Use submit_artifact to finish, or revise_artifact for schema feedback.
