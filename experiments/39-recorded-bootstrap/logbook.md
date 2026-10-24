# Recorded bootstrap replay at the standalone task boundary

## 2026-10-24 — scope and source checkpoint

Started from main `2a1950d239f1ada467c35393991dac87debe35f7` on `codex/research/39-recorded-bootstrap`. Filed #39 and verified it is a real open subissue of epic #33 with the agent-generated label. Native baseline remains Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238` and #37's sealed OHIF #5996 missing-pnpm failure. This follow-up changes the environment reconstruction procedure explicitly; no installation or PR command is repaired.

Inspected #29/#31 before proposing new code. The existing `recorded_replay.py` already continues original expected failures, preserves their filesystem effects, and stops on any unexpected exit, timeout or executor exception. Adopt it byte-for-byte. The bootstrap reconstruction is an agent action history, including exploration and a cloned-source COPY; it is not a demonstrated standalone recipe. Verify transcript/recipe action mapping and source checkout before any candidate runtime.

Source/fixture preparation only. #38's frozen code and running handle remain unchanged. No model calls, remote submission, new capacity or CPU reservation for #39. Any live comparison follows #38's verified archive/cleanup, a frozen payload/publication policy, and cumulative ledger admission (at most five CPU-hours plus 1/6 emergency cleanup under the epic's 32-hour ceiling). Do not overlap native jobs. Keep the original 300-second/one-CPU/6-GiB task contract and all eight non-Dockerfile/non-metadata grading assets intact. Keep open for review.

### 2026-10-24 — reuse exact OHIF replay inputs and historical controls

Found the original #29 OHIF payload already preserved locally, so no reacquisition or new command extraction is needed. Verified its SHA against the recorded manifest, rehashed the original 8,730,760-byte phase archive, and matched the bootstrap JSON to #37's sealed source. All eighteen command/expected-exit records match; one INVALID action had no upstream shell execution. Regenerated the saved reconstruction Dockerfile byte-for-byte. Original commands remain unchanged.

Independently parsed #29's exact replay archive and four-control-pair archive. Eighteen original BASH exits matched, bootstrap smoke/fresh checks passed, and the public base image ID is exactly the same as #37's native failure (`sha256:58a96d9752cfedf3c4fcfcbe2dabbad725c147f7003caa9f7899a3f414ada3fc`). The public digest can therefore pin the candidate base. Parsed all native trial/reward bytes and stdout for PR6334/6339/6346/6352 against frozen expected F2P/P2P counts: all four historical pairs are positive, clean and preserve P2P. Their old raw results are evidence for reuse, not fresh #5996 outcomes or a claim of current portability. Source/identity details and limitations are in `source-assessment.json`.

This establishes that recorded replay can recover this bootstrap on the observed same public base; it does not establish a fresh #5996 pair, an unattended generic packaging interface or availability after deleting the reconstructed image. Next assess the existing full-checkout/login-shell replay driver and explicit standalone dependency representation. No task recipe has been modified and no new remote job or CPU admission exists. #38 continues unchanged.
