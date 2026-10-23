# OHIF: successful image build, unusable environment

The original saved recipe produced Docker exit 0 but did not install the project's dependencies. The verified build log contains `ERR_PNPM_OUTDATED_LOCKFILE`: `platform/docs` is a lockfile workspace whose directory/package file is missing from the image. Jest then reports the missing `jest-environment-jsdom` dependency and lists zero tests. No controls were run and no pair/recovery result is claimed.

The exact pinned source has `platform/docs/package.json`, while its root `.dockerignore` excludes `platform/docs/` (and `testdata/`, `.git`, among other paths). The reconstruction's `COPY . /workspace` obeys those ignore rules. This identifies a build-context omission, not proof that the original lockfile itself was inconsistent. The original bootstrap copied the checkout into its sandbox rather than using this reconstructed Docker build context; that distinction must be preserved in any follow-up.

The recipe's `pnpm install ... | tail` and test-listing pipelines mask intermediate failures, explaining the successful Docker exit. Syntax-only checks and Docker exit status cannot establish environment readiness. The image is being removed after archive readback rather than used to produce misleading failed task controls.

A possible general infrastructure comparison is reconstruction from the complete original checkout, explicitly controlling build-context exclusions, while preserving all saved RUN instructions, task files and dependencies. This has not been applied. Do not silently repair the lockfile, install missing packages manually, or count this failed environment as a verifier-timeout result.

Evidence: `ohif-reconstruction-readback-001.json` binds the private original log; `ohif-context-source-readback.json` binds exact GitHub source files at commit `4965e280cada2202a99f9dd0212a8465865b49f7`. No additional model calls or new capacity.
