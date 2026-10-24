# Native published-Harbor comparison

Stage `native_probe_returned`, driver exit `0`, completed `True`. The same external observer was used for both published packages; writer/test bytes and five-second deadlines are unchanged.

| Version / case | Native result | Writer starts / ends | Live sampled after native end | In-container hole samples | Final NUL bytes |
| --- | --- | --- | --- | --- | --- |
| 0.6.6 / finite | 0.0 | 1 / 1 | False | 0 | 0 |
| 0.6.6 / timeout | VerifierTimeoutError | 2 / 0 | True | 10 | 0 |
| 0.24.0 / finite | RuntimeError | 0 / 0 | False | 0 | 0 |
| 0.24.0 / timeout | skipped_failed_finite_prerequisite | Unmeasured | Unmeasured | Unmeasured | Unmeasured |

Baseline recorded dependency constraints match: `True`. Candidate package/dependency closure is recorded separately; this is an upgrade variant, not an isolated single-source patch. All installed package source/metadata/license identities are checked against the pinned wheels.

A live-after-end observation requires matching PID/start ticks, non-zombie state and writer command, with the observation starting after the native verifier finished/exception timestamp. UTC is enforced; native timestamps have microsecond precision. Missing live samples never prove termination. Docker lifecycle events and process samples measure teardown ordering independently; no observer terminates or repairs a verifier.

Retry overlap, transient in-container holes and final raw NULs remain separate observations. The original #41 conjunction and historical Scanpy uncertainty are unchanged. Finite prerequisites and native compatibility failures are preserved; no biological control, new task export, dependency upgrade or production-readiness result is implied.

The 0.6.6 baseline has 34 matched PID observations after its final native verifier exception, with both writer identities represented. The latest is 10.333724 seconds afterward. Docker events record SIGTERM at +0.557842 seconds, SIGKILL at +10.573770, container death at +10.628393 and destruction at +10.635841. This demonstrates survival through the stop grace period, followed by eventual teardown; it is not an indefinite post-teardown leak. Ten writer samples and nine outside observer samples had transient holes; the final log contains no NULs.

The 0.24.0 finite trial fails before its writer: the published environment tries to build an egress-control sidecar using Docker Buildx, which is absent from the old minimal runner toolchain. Its timeout case is skipped under the declared finite prerequisite. No 0.24.0 cancellation result exists. The upgrade comparison is therefore inconclusive beyond the baseline observation and concrete toolchain incompatibility. No plugin, native package or task repair was applied during this run.

One managed attempt used 0.099667222 / 2 allocated CPU-hours, zero model calls/new capacity. Runtime HF readback, owned cleanup and shared public base preservation are verified. Summary/source archival and local duplicate cleanup follow as separate gates.

Runtime snapshot: `hf://buckets/open-athena/biotasks/research/43-native-harbor-comparison/2026-10-24/68475d52b7608a42ee60973450834d8ddc5e20ba41005a5edc853aec3412d169`.
