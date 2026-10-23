🤖 The opt-in rebuild candidate now covers native validation and exported verification, with default-off behavior checked against the pinned builders. All 12 synthetic compiled-library lifecycle checks and seven graded-export checks pass.

The graded checks use the unchanged upstream standalone verifier: nop earns 0 and oracle earns 1; failed builds, invalid base revisions and obstructed test resets clear stale rewards and fail closed. A command failure can still coexist with tracked-test reward 1, explicitly preserving upstream's distinction between `resolved` and `command_resolved`.

[Lifecycle evidence](https://github.com/Open-Athena/biotasks/blob/4436eaba74ec5e5ab2a85aa1430ba9a95402ae34/experiments/31-historical-builds/candidate-lifecycle-results.json), [graded verification evidence](https://github.com/Open-Athena/biotasks/blob/4436eaba74ec5e5ab2a85aa1430ba9a95402ae34/experiments/31-historical-builds/graded-export-results.json), and [candidate/static evidence](https://github.com/Open-Athena/biotasks/blob/4436eaba74ec5e5ab2a85aa1430ba9a95402ae34/experiments/31-historical-builds/candidate-static-results.json).

These checks do not establish full CLI/configuration integration or MACS recovery. No Docker/Harbor execution, model calls, manual dependency repair or promotion to main occurred. The issue remains open.
