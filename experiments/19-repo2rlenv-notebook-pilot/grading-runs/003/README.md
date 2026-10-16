# Grading 003: verified replay, probe author stopped

Recovery reused the original submitted independent program and grader. The independent output reproduced the previous hash exactly, and all five initial grader controls passed again. No independent or grader authoring calls were made.

The probe worker made 38 calls but did not submit a suite. Its inherited context exposed analysis code and raw-input paths, and it reconstructed raw-analysis helpers instead of limiting itself to result mutations. The operator stopped only the owned author process to apply the general stage-boundary correction. This is an operator cancellation, not a provider failure or successful scientific validation.

The full archive and selected original records are download/hash-verified, and sandbox cleanup passed. The candidate remains unapproved for release: independent probes, review, native trials and publication are still required.
