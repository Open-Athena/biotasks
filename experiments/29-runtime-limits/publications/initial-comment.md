🤖 Initial investigation is published on the permanent research branch at `3588e2b6123b87f58ff3c41a50fe562815160723`.

The input inventory is complete: 14 original controls were unstarted. Fresh paired comparisons require 20 commands across nine existing exports: 16 Matchms/OHIF scheduling controls and four Scanpy timeout-arm controls. Task and reconstruction member hashes are recorded. No tasks have been regenerated or executed.

The two partly completed Matchms/OHIF pairs need both sides on the same reconstructed image; reusing an old nop result with a new-image oracle would confound the comparison. The 300-second and 1,200-second Scanpy arms also require both controls. Original images were deleted, so reconstruction provenance and recipe validation are prerequisites.

Next: inspect saved reconstruction recipes and runner timeout-override support, then checkpoint a bounded live comparison. Proposed first stage is $0 model calls and at most 32 allocated CPU-hours on existing reserved capacity; it has not been submitted. OpenMS checkout and MMseqs2 bootstrap comparisons remain separate later arms.

[Evidence](https://github.com/Open-Athena/biotasks/blob/3588e2b6123b87f58ff3c41a50fe562815160723/experiments/29-runtime-limits/plan.md) · [Scope](https://github.com/Open-Athena/biotasks/blob/3588e2b6123b87f58ff3c41a50fe562815160723/experiments/29-runtime-limits/issue-scope.md) · [Logbook](https://github.com/Open-Athena/biotasks/blob/3588e2b6123b87f58ff3c41a50fe562815160723/experiments/29-runtime-limits/logbook.md). All changes remain research-only; no promotion to main, live task repair or model spend. The issue remains open.
