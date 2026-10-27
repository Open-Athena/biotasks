# Refuse an impossible solver window before claiming a trial

PyMC 213 passed its 14 scientific controls and native oracle/no-op checks, then requested 600 solver seconds while its clipped outer budget was below 600. Pinned upstream rejected that request before launching a solver. The adapter had already written an unresolved trial claim and reserved resources; preserve the original records.

The candidate checks the same solver allowance against the existing outer timeout before writing a claim or making a reservation. It reports an infrastructure timeout without shortening the solver allowance, increasing campaign time, retrying the trial or accepting the task. Deterministic controls retain their previous behavior. Five new boundary cases and the combined 114-test affected suite pass. [Checks](offline-checks.json).

This improves admission and diagnostics; it does not solve slow authoring or demonstrate a successful solver run. It is unadopted and needs a new source admission before execution.
