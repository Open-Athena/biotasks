# Upstream verifier cancellation assessment

Published Harbor 0.24.0 removes the old automatic verifier retry from the single-step trial path. This is a candidate way to avoid the particular overlapping retry seen in #41, not proof that container-side processes are reliably cancelled or that an upgrade is compatible with our pipeline. No newer Harbor package was installed or executed.

| Property | Pinned 0.6.6 baseline | Published 0.24.0 / inspected main |
| --- | --- | --- |
| Internal single-step verifier retry | Two attempts in the same environment, native overlap measured in #41 | One shared/separate verifier branch invocation; errors propagate to recovery/teardown |
| Outer verifier deadline | asyncio.wait_for | Still asyncio.wait_for |
| Inner script exec deadline passed by verifier | None | None |
| Buffered Docker collector on outer cancellation | No cancellation cleanup branch | Still no cancellation cleanup branch |
| Streamed Docker collector | Not this newer callback path | BaseException cleanup terminates/kills the CLI subprocess; streaming is opt-in |
| Proof of daemon-side verifier termination | #41 measured survival into retry | Not established by source or client termination |
| Verifier stdout path/redirection | Fixed per-trial path, truncating redirection | Still fixed per-trial path, truncating redirection; old automatic inner retry is gone |
| Environment cleanup | Trial finalization | Shielded stop in recovery/finalization; reviewed tests use fake environments |

At the 2026-10-24 metadata check, the latest GitHub release and PyPI metadata both identify 0.24.0. Its tag is pinned to b53b8134e1241686dca7759af188f987ecc48e8b; ten inspected runtime modules match the published wheel exactly. Current main is separately pinned to 6099b8cf2bfbbb3e7ff1eb2163bfc4524dbd9ba5; it is unreleased source, not the measured published package. All acquired source bytes match Git blob identities. Structural checks cover 25 selected functions across baseline/release/main without importing upstream code. Ten named test modules per current revision were inspected; no tests were executed and the selection is not an exhaustive test audit.

The single-step call path and unchanged timeout wrapper support the no-inner-retry conclusion. The buffered collector still catches only its own TimeoutError. The streamed collector catches BaseException and cleans up the host CLI process, but no inspected helper demonstrates terminating the process inside the Docker container. With no registered log callbacks, the trial log context is a no-op and Docker uses the buffered path. The selected streamed-output tests exercise fake CLI processes and an ordinary local subprocess, not daemon-side containment; the cleanup tests exercise fake environments. These are distinct guarantees.

Primary source: [published single-step verifier](https://github.com/harbor-framework/harbor/blob/b53b8134e1241686dca7759af188f987ecc48e8b/src/harbor/trial/single_step.py#L88), [buffered and streamed collectors](https://github.com/harbor-framework/harbor/blob/b53b8134e1241686dca7759af188f987ecc48e8b/src/harbor/environments/docker/docker.py#L766), [opt-in streaming context](https://github.com/harbor-framework/harbor/blob/b53b8134e1241686dca7759af188f987ecc48e8b/src/harbor/trial/trial.py#L453), [verifier script invocation](https://github.com/harbor-framework/harbor/blob/b53b8134e1241686dca7759af188f987ecc48e8b/src/harbor/verifier/verifier.py#L229). Exact file/function hashes and line spans are in source-assessment.json.

No production upgrade or custom patch is promoted. A later comparison would first need CLI/task-format compatibility checks and an explicit versioned native candidate, keeping #41's original fixture deadlines/writers and recording process survival independently from log-hole persistence. Removing an automatic retry changes execution semantics; do not silently mix such a run into the 0.6.6 evidence. Original biological task validity, missing Scanpy rewards and historical NUL causation remain unproven. No runtime reservation, model call, new capacity, paid execution or new task export was added.
