🤖 The deleted-target comparison completed in one attempt: 201.029 seconds, 0.2233656 allocated CPU-hours, zero model calls. Archive and owned-resource cleanup are verified.

Original selection reproduces a missing test path and zero collected tests. The general surviving-path selector removes that error, but exposes missing `chemap`: pre collects 0 items with 6 errors; post collects 45 items with 5 errors. Both stop during collection and native validation returns no F2P tests. Collected items are not passing tests. No dependency installation or other repair was added.

PR671 preserves exactly the same native F2P/P2P sets (1/30). No exports or independent Harbor controls were generated, and no task-recovery claim is made. This isolates a real selection defect from a separate historical-environment failure.

[Diagnosis](https://github.com/Open-Athena/biotasks/blob/40a80ef0/experiments/32-runner-coverage/target-live-diagnosis.json) · [Verified archive and cleanup](https://github.com/Open-Athena/biotasks/blob/40a80ef0/experiments/32-runner-coverage/live-readback.json). Parser/completion and broader runner work remain open; the original comparisons remain immutable.
