# Reproducing the source-only assessment

This assessment uses the pinned [Repo2RLEnv source](https://github.com/huggingface/Repo2RLEnv/tree/27d04ee8203cd5b2f20c3997d13836e5f5b64238) and retained research manifests. It runs no Docker, solver, task verifier or model. Original evidence remains at the public HF paths recorded in `acquisition.json`.

Restore the #29, #31, #33, #38, #39 and #40 research branches in the sibling worktree layout recorded by the source plan. Populate #31's `inputs-private/upstream-package` with the pinned upstream checkout; its Git-versioned `package-acquisition.json` supplies the 353 expected file hashes. The checker reads these files but never executes the pipeline. Keep the source read-only and follow shared-node resource rules.

Run `acquire_sources.py` with the pinned archive client environment to anonymously retrieve the ten bounded public objects. Then run `assess_sources.py` under the shared heavy-work guard with one thread and the recorded 150-MiB working-set estimate. The recorded successful run used approximately 26 MiB RSS. The executable validates original source/actions, original task bytes/modes, prior trial/cleanup records and the relevant wrapper interfaces before deriving `source-assessment.json`.

`assessment-evidence-manifest.json` and its receipt identify the separately archived source/derived snapshot and notices. The raw logs are referenced unchanged, including NUL holes; human-readable derived excerpts explicitly omit NUL characters and are not substitutes for raw artifacts. Re-running a historical bootstrap/control is outside this source-only reproduction. The snapshot is not a standalone runnable task or a new Scanpy validation result.
