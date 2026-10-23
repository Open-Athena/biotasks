Can a general reset-and-rebuild lifecycle validate compiled code at historical PR revisions? Follow-up to #28.

**Current findings:** Verified original MACS evidence independently confirms extension removal in seven paired validations. An additional prerequisite emerged: three RUN commands in its saved reconstruction Dockerfile fail shell syntax checks. The original saved image cannot be assumed reproducible by building that recipe verbatim.

**Remaining work:** Next: separate baseline reconstruction from historical rebuilding, then test correct-revision compilation at native and emitted-task boundaries before a MACS comparison. Saved rebuild commands exist but include shell-semantic hazards; no command or dependency repair has been applied.

**Boundaries:** original baselines remain immutable; use only justified general changes and upstream’s built-in model calls, with no added per-task LLM/Codex repair loop. No remote/native jobs or model calls have been launched in this follow-up. Execution requires a checkpointed cumulative allowance; #28’s unused ceiling is not a fresh budget. A mechanism test does not establish task recovery or production readiness.

[Evidence](https://github.com/Open-Athena/biotasks/blob/0d9d4101de445f86f438ebb7182ab0463b9fd101/experiments/31-historical-builds/findings.md) · [Full comparison scope and success criteria](https://github.com/Open-Athena/biotasks/blob/0d9d4101de445f86f438ebb7182ab0463b9fd101/experiments/31-historical-builds/issue-scope.md) · [Logbook](https://github.com/Open-Athena/biotasks/blob/0d9d4101de445f86f438ebb7182ab0463b9fd101/experiments/31-historical-builds/logbook.md). Detailed investigation updates are in comments.
