Can a general script-transport change remove large-argument failures while preserving native behavior? Follow-up to #28.

**Current findings:** A candidate using stdin plus a Bash loader passes 20 bounded local cases. The original method reproduces Linux errno7 on a large synthetic script; the candidate delivers the payload exactly with a maximum 92-byte argument. Quoting, UTF-8, stdin EOF, exit/trap behavior and timeout cases were checked.

**Remaining work:** Next: exercise actual Docker behavior and owned-process cleanup, then a predeclared live PR comparison. These results use a local Docker-argument adapter, not a Docker daemon or biological task. No recovery count is claimed; shell diagnostic/introspection differences and inherited remote timeout cleanup remain explicit.

**Boundaries:** original baselines remain immutable; use only justified general changes and upstream’s built-in model calls, with no added per-task LLM/Codex repair loop. No remote/native jobs or model calls have been launched in this follow-up. Execution requires a checkpointed cumulative allowance; #28’s unused ceiling is not a fresh budget. A mechanism test does not establish task recovery or production readiness.

[Evidence](https://github.com/Open-Athena/biotasks/blob/726307f44ecef02e41b4e85d1622549224c8b28d/experiments/30-script-transport/local-results.json) · [Full comparison scope and success criteria](https://github.com/Open-Athena/biotasks/blob/726307f44ecef02e41b4e85d1622549224c8b28d/experiments/30-script-transport/issue-scope.md) · [Logbook](https://github.com/Open-Athena/biotasks/blob/726307f44ecef02e41b4e85d1622549224c8b28d/experiments/30-script-transport/logbook.md). Detailed investigation updates are in comments.
