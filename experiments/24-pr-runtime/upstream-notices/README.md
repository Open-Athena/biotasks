# Upstream research inputs

The runtime input patches retain their original upstream terms. They are
research inputs, not BioTasks-authored code or a relicensed task release.
`source.json` beside each original notice identifies the repository and
revision from which it was retrieved. The Nipype file explicitly names
Apache-2.0 even though GitHub's license classifier returns `NOASSERTION`.

The 16 statically eligible patches (development, held-out and overlap
exclusions) and capture receipts are
preserved under `inventory/pr-diffs/`. Cohort manifests record their exact
base/head revisions and SHA256 hashes. Other locally cached static-scan
patches are not part of this published runtime snapshot; their hashes and
derived dispositions remain in the inventory evidence.

Native Repo2RLEnv output bundles contain upstream source patches and grader
code. Diagnostic builds are local-only, and their Docker images are removed
after verification. No biological dataset, container image, or runnable task
release is published by this experiment.
