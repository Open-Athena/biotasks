# Sonnet comparison completed

The unchanged official native pipeline produced zero exports. Sonnet emitted 35
parsed actions with zero INVALID actions; the GLM baseline had 49 actions with
17 INVALID actions. This supports better compatibility with the native action
format in this sample, without establishing improved task yield or cost.

Two native images were saved, including scikit-fingerprints with failed smoke
and fresh-image checks. Its four selected PRs had zero fail-to-pass matches.
Nipype saved its image but timed out while listing PRs, before validation.
PsychoPy exhausted 20 turns without saving an environment; its second window
was skipped without another bootstrap. No extra model call, manual retry or
external environment repair ran. With no exports, grading had no inputs.

Dedicated GH_TOKEN authentication worked without browser interaction. Both Sonnet
jobs and the five baseline jobs are terminal. Archive readback and owned cleanup
passed; 3.118936 CPU-hours cover both Sonnet attempts, and 4.625277 CPU-hours cover
all seven issue jobs. Model billing remains unverified because native estimates
were zero and usage/request identifiers were not retained. See results.md and the
retained original evidence for the comparison and limits.
