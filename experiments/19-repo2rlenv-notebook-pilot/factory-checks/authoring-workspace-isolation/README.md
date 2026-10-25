# Controlled staging without authoring workspace state

Original174 passed its in-session test with a staging recipe that copied exploratory downloads from the authoring workspace. Fresh replay could not find those files and stopped. The original recipe, failure and complete evidence/cleanup remain preserved. The source notebook is not classified as broken.

The existing test_reference tool now moves the canonical authoring directory aside during dependency build and input staging, then restores the original files before post-build validation and worker feedback. A recipe depending on that workspace fails before consuming a scientific reference attempt, so the existing GLM worker can correct its own recipe within the existing session and budgets. No new model stage, repair allowance or computation attempt is added.

Unexpected recreation of the reserved authoring path is preserved separately, reported and rejected; original author files are restored. Failed restoration or uncertain execution blocks further commands and cannot finalize as a normal worker refusal. Receipts preserve both the first error and any restoration error. The original candidate hash check still runs afterward. The packaged setup prompt explains the actual boundary.

This isolates the known authoring workspace, not all filesystem state, and is not a replacement for fresh-sandbox replay. It changes no notebook methods, input population, endpoints or generated scientific artifact.

The old controller fails the scratch-dependency regression and four unsafe-finalization cases. All290affected checks pass after the changes, including actual filesystem copy/restore/preservation and controller failure/cancellation/budget tests. Ruff passes. [Exact local checks](local-validation.json). The prepared provider check uses only synthetic files and real online/offline controls; it has not run, and no fresh complete notebook campaign has adopted this change.
