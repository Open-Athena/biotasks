# Corrected image-provenance analysis

`cold-readback-initial.json` retains the first analysis unchanged. Its image-provenance gate incorrectly required both controls to have the same image ID. The frozen protocol required actual build/image provenance and original source/dependency identities, and explicitly did not claim byte-identical images.

The recorded run built twice, with different image IDs. Each build used the same native Dockerfile plus the single ownership label; the actual source commit, Python/platform and installed-package list matched both arms. The corrected analysis binds each recorded build and identity capture to its respective trial interval, verifies the exact original/effective recipes in the archive, and cross-checks raw trial/reward files and pytest summaries. Both image IDs remain explicit. This establishes provenance of two rebuilt images; it does not establish image byte identity.

No run, task file, installation command, test, patch, timeout, reward or original output byte changed. No rerun or additional model call occurred. The first and corrected analyses are both retained with the same original archive checksum.
