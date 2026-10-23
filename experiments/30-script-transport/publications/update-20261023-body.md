Can a general script-transport change remove large-argument failures while preserving native behavior? Follow-up to #28.

**Findings:** In real Docker, the pinned upstream executor fails with Linux `E2BIG`, while the stdin candidate delivers a 1,080,000-byte payload with exact SHA256. Representative shell behavior matches; diagnostic/introspection differences remain documented. This establishes the transport mechanism, not biological task recovery.

**Separate timeout finding:** both executors leave live, CPU-consuming commands inside the container after the Docker client times out. The transport change does not fix cancellation. Its contribution to earlier repository failures is not yet measured.

**Status and next step:** four bounded synthetic probe attempts are terminal, totaling 0.05442 allocated CPU-hours on existing reserved TRC capacity, with no model calls. All created containers were removed and absence verified. Run a predeclared failed-PR/successful-control comparison next, isolating and removing each owned sandbox after its arm, including on timeout.

**Boundaries:** no per-task repairs or added LLM repair loop; preserve immutable baselines. No repository recovery or production-readiness claim, and no change promoted to main.

[Findings and limitations](https://github.com/Open-Athena/biotasks/blob/39048b92429f437127db14ec69de6731ef310c3e/experiments/30-script-transport/findings.md) · [Exact Docker result](https://github.com/Open-Athena/biotasks/blob/39048b92429f437127db14ec69de6731ef310c3e/experiments/30-script-transport/attempts/004/result.json) · [All-attempt accounting](https://github.com/Open-Athena/biotasks/blob/39048b92429f437127db14ec69de6731ef310c3e/experiments/30-script-transport/probe-accounting.json) · [Full scope](https://github.com/Open-Athena/biotasks/blob/39048b92429f437127db14ec69de6731ef310c3e/experiments/30-script-transport/issue-scope.md). Detailed logs remain in comments.
