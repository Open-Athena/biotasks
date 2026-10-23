# Durable runtime artifacts

## 2026-10-23 — source assessment

Started from main `2a1950d239f1ada467c35393991dac87debe35f7` on `codex/research/35-durable-runtime-artifacts`. The first MACS diagnostic's exported Dockerfile refers to a local image ID that its verified cleanup removed. This establishes an artifact-availability question, not a fresh-worker execution result.

Source inspection found existing upstream registry and inline-recipe distribution. Verified eight relevant source files against the frozen package acquisition and Git blob identities; no package code was imported or executed. Favor these interfaces before building new distribution infrastructure. Documented a source-level unresolved-digest edge case and the need for actual retrieval/control evidence.

An initial check incorrectly compared the stored API-tarball digest with the separate codeload-archive digest and stopped before inspection. The existing acquisition record identifies the API archive (`7e387fbb…`) and verifies selected files by Git blob identity at the same pinned revision. Subsequent inspection used that recorded source tree and its per-file hashes. No inputs were changed or reacquired.

No registry credentials were inspected, no task variant was generated, no source package or remote job executed, and no image bytes were uploaded. This issue has no new budget allocation. The active #34 confirmation proceeds independently under its existing reservation. Next: assess the native inline recipe's actual cache requirements and registry prerequisites; checkpoint a concrete eligible retrieval comparison before any execution.
