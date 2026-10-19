# Correct unsupported explanations, preserving executable criteria

All 19 controller controls passed. Preserve the exact grader code, check inventory, numerical thresholds and probe suite. Correct only the public acceptance addendum and private rationale.

- Rule 10 claims that tie/continuity correction, per-cluster normalization or wrong grouping always move scores orders of magnitude beyond tolerance. A continuity term can be smaller than the allowed score tolerance. State the actual numerical acceptance rule, not universal detection of methods.
- Rule 11 says any genuine tail error is rejected. Finite tolerances necessarily accept sufficiently small differences. Report tested examples privately without generalizing them to all errors.
- Rule 12 presents the small-p-value zone as a universal consequence of floating-point underflow and BH scaling. A value of 1e-303 is representable; BH scaling does not universally preserve this zone. Describe the implemented comparison rule exactly, and distinguish empirical calibration from a mathematical guarantee.
- Rule 14 claims dropping stabilizers or other genuine errors must fail by orders of magnitude. Remove that universal claim and unsupported justification for a safety factor. Keep the existing tolerance unchanged; acknowledge calibration limitations privately.
- Do not claim isolated coverage of every failure mode: a combined invalid probe cannot prove each mutation independently detected, and a no-op mutation branch is not evidence for detecting its purported error.
- Describe rank consistency as the implemented adjacent-score comparison, not a guarantee against every cumulative inversion. Do not claim uniformly enforced significant digits when only numerical comparisons are enforced.

The scientific task and observable acceptance criteria must stay unchanged. Return blocked if a requested change would require changing executable behavior. No new scientific tests or broader portability evidence have been produced by this prose correction.
