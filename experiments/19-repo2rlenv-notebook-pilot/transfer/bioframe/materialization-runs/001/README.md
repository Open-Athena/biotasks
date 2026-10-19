# Bioframe materialization 001

The existing GLM construction worker completed in 763.07 seconds using 67 model
requests. Its first controlled submission staged the three original inputs
unchanged and created a private reference by renaming the selected motif columns.
The separately executed oracle passed the answer-access isolation check and
produced a CSV byte-identical to the projected reference (SHA-256 recorded in
`manifest.json`). The combined derivation/oracle controller call took 2.07 s.

The oracle is a standalone Python interval implementation using gzip/CSV parsing
and a heap-based overlap algorithm. It does not call bioframe or pandas. Its
author could inspect the source/reference during construction, so this is not
the separate blind implementation required by the grading stage. Numerical
comparison rules, adversarial controls and scientific acceptance remain pending.

`candidate.json` preserves the exact worker response; the Python/Markdown files
are presentation copies verified against the original archive hashes. No source,
solution, instructions or scientific results were manually repaired. The input,
reference and oracle-output files remain in the configured artifact archive.
Worker cleanup passed and provider absence was checked separately.
