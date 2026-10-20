# Native Bioframe 001 — oracle, no-op and blind solver passed

The frozen task from materialization 005 and final grading 004 ran through the
pinned upstream Harbor adapter on offline CPU-only Daytona. Oracle reward 1,
no-op reward 0, and blind GLM-5.3 Terminus-2 reward 1, with no exceptions.
The solver's 210.21-second overall trial used seven successful API requests
and passed all five verifier checks. Its initial prompt, commands and observations
are preserved in the original trajectory.

All raw result/receipt identities pass the release gate. The full 158-file archive
passed download/readback verification; diagnostic transport restored 133 files,
a bounded subset. Twenty-six selected original records retain their hashes.
Independent provider readback found zero sandboxes across the three exact
ownership labels; the Iris host and task SUCCEEDED. The exact pre-trial bundle
was separately downloaded and verified, and the published immutable release
matches its hash. No task-specific scientific artifact was manually altered.
