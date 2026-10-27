# Inspect recorded creations after an incomplete native sequence

`inspect_recorded_creations.py` freshly queries every original SDK sandbox ID and every executed native owner from a checksum-verified complete archive. It requires successful original cleanup records, while preserving dispatch claims without a corresponding native receipt as gaps.

This read-only diagnostic is separate from the strict complete three-trial cleanup gate. It cannot qualify a task, resolve an unknown dispatch merely from missing files, or release an accounting reservation. On 213, four recorded SDK IDs and six recorded owners were absent; the solver's preflight claim still lacked an outcome receipt.
