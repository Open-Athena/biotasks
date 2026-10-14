# Independent review: declarative reference preparation

Reviewed revision: `74b5f0c`. Review requested by the user on 14 October 2026.
A separate reviewer inspected the prompt, schema, preparation-only entry point,
environment helper, execution adapter and focused tests without editing or running
models, setup or analysis.

## Findings and disposition

1. **P2: malformed project table bypasses the repair call.** Valid TOML with a
   scalar or array `project` caused an AttributeError, outside the artifact
   controller's validation-error handling. Added an explicit table check that
   raises ValueError, with regressions for both wrong types.
2. **P2: worker-staged input provenance is not preserved before later execution.**
   The runner retained the lockfile but not the requested staging receipt.
   Defined the receipt's file records in the prompt; the controller checks
   paths, identities and actual file hashes before setup succeeds and downloads
   the receipt before scientific execution. Empty staging gets an empty receipt.
   A regression verifies a valid fixture and rejects changed data and malformed
   records. This checks declared files; completeness and scientific provenance
   still require review. This later execution path was not remotely exercised.

The reviewer found the preparation-only boundary clear and no reason to add
notebook-specific rules or more stages. Thirty-five focused tests passed after
these fixes (2.87 seconds; peak RSS 132,136 KiB), including the real offline uv
fixture. No biological dependencies were installed during these tests.

The reviewer rechecked both fixes and found no blocker to preparation. Their
follow-up suggestion was also applied: remove a prior staging receipt before
each setup attempt so retries cannot inherit stale provenance.
