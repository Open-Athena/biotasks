# Offline historical rebuilds

## 2026-10-23 — scope

Started from main `2a1950d239f1ada467c35393991dac87debe35f7`. Issue #34 is a child of #33 and uses its existing shared spending/resource budget. No new model calls or remote jobs have started. Preserve the #31 MACS PR742 failure and the pinned upstream egress guard. The first candidate prepares base-declared Python build dependencies outside the task runtime, excluding the target project itself; it does not claim to solve apt, submodules or dynamic dependency discovery. Runtime rebuild commands remain unchanged. Unsupported dependencies fail explicitly.

Source inspection found the recorded recipe also contains unquoted shell `>=` tokens. Those may be interpreted as output redirections rather than package-version constraints. Do not silently fix the recorded commands in this comparison; preserve their actual shell semantics and report the limitation. Exact commands are retained in #31 `macs-native-742-manifest.json`.

## 2026-10-23 — static preparation checks

Implemented a non-executing static pyproject build-requirement planner and wheel-identity inspection. Eight synthetic checks pass, including target-project rejection and metadata mismatch. This does not prove dependency availability, binary compatibility, compiled fixture execution, robust network isolation or task controls. The offline pip environment is a candidate configuration, not enforced isolation against arbitrary recorded commands that override it. Keep the upstream runtime network guard. Actual wheel resolution must occur on the same Python/platform as the task and retain full hashes. No downloads, model calls or remote jobs in this step.

## 2026-10-23 — compiled fixture result

The first attempt rejected setuptools because vendored dist-info metadata was mistaken for multiple root distributions. Preserved the failed download log/resource record and corrected root-metadata selection with regression coverage. The second attempt completed in 4.45 seconds at 73,192 KiB peak RSS under the shared lock. With the identical `pip install -e .` command and build isolation enabled, the empty cache failed for missing setuptools; the prepared setuptools80.9.0/wheel0.45.1 cache built a C extension that imported and returned42. All temporary fixture environments and downloaded wheels were removed. This uses pip offline configuration, not OS-level network isolation; Docker guard behavior and MACS remain untested. No remote jobs or model calls.

Fetched only pyproject metadata at the exact MACS PR742 base and verified its Git blob digest. Static build requirements are setuptools>=80.0, numpy>=1.25 and Cython>=3.0, target distribution macs3. Recorded hashes and plan in `macs-base-dependency-plan.json`; runtime-platform resolution and wheels remain pending. No project hook or MACS source executed locally.

## 2026-10-23 — reconstruction launched

Checkpoint `2d6d665a` passed preflight and launched one bounded original-recipe reconstruction on an existing reserved worker; authoritative observation at22:12:04UTC reports running. See `reconstruction-submission.json` for payload hashes and resource bounds. Four CPU-hours remain reserved, not actual consumed usage. No retry, new capacity, model calls or control run. Private submission retains the exact worker binding for follow-up and cleanup. Do not resubmit this handle after interrupted observation.

## 2026-10-23 — candidate transformation and readback prepared

The original reconstruction remains running on its existing handle. Added terminal-accounting/readback helpers with duplicate archive-member rejection. Prepared the trusted base-declaration cache helper and separate task transformation. A static transformation check against the exact archived MACS task verifies nine unchanged original files, twelve final files, unchanged egress guard/test assets, refusal of mutable image tags and no overwrite. The test's synthetic digest is explicitly not an executed image, and the temporary variant was removed. Candidate Docker build and controls remain unexecuted; use the actual verified reconstruction digest before producing the real variant. See `offline-controls-protocol.md` for admission and evidence requirements.

## 2026-10-23 — bounded control runner wired

Copied five control infrastructure helpers byte-for-byte from #31, including the resource wrapper and original Harbor invocation logic. Adapted only run/ownership identifiers, verified reconstruction admission, candidate manifests, and receipt collection. Before controls, require successful terminal reconstruction, smoke/fresh checks and archive readback. After controls, copy the actual dependency receipt from a stopped ownership-labeled image container without executing code; existing cleanup removes that container too. The transformation check now also feeds the twelve-file candidate through the unchanged control inventory checker and emits exactly two300-second nop/oracle commands. No control job has been submitted; the reconstruction handle remains running at the latest authoritative check.

## 2026-10-23 — packaging and cleanup paths

Prepared candidate packaging that requires verified reconstruction evidence, binds the actual retained image digest, writes a deterministic archive, and independently reads every member against the candidate manifest. Prepared ownership-gated image cleanup with admission requiring all #34 jobs terminal; if controls were submitted, their archive/result evidence must be verified first. No packaging, controls or cleanup executed yet. The existing reconstruction was still running at the latest check. Space further status checks until at least22:24UTC and use the wait for independent #33 work; never resubmit this active handle.

## 2026-10-23 — reconstruction verified; controls checkpoint

One reconstruction attempt succeeded in 1,397.321 seconds, 1.552579 allocated CPU-hours. All 16 recorded actions matched, smoke and fresh-image checks passed; fresh check reported 4,924 passed/348 skipped. Verified the 64,599-byte archive and all retained stream hashes. Owned build containers/tools were removed; only the bound reconstruction image remains. Packaged the twelve-file offline candidate against its exact digest and independently verified every archive member. Original nine non-Dockerfile assets remain unchanged. Reconciled the four-hour reconstruction reservation and booked at most four CPU-hours for controls under the shared budget, preserving cleanup allowance. No model calls. Control submission remains separate.

## 2026-10-23 — offline controls running

Control preflight passed on the original reserved worker with the verified reconstruction digest and candidate archive. Submitted one attempt from checkpoint `1ac19916`; authoritative observation at 22:38:05 UTC reports running. It preserves original Harbor commands, 300-second verifier timeout, resource wrapper and task egress guard. Maximum four CPU-hours reserved; actual usage pending. No model calls or retries. Do not resubmit the handle after interrupted observation; inspect its terminal archive and dependency receipt before any result claim.

## 2026-10-23 — control readback gates

Prepared terminal accounting and a bounded archive reader for the existing control handle. The reader verifies twelve candidate files, archive/member digests, the actual dependency receipt and reconstructed image identity. It reports preparation provenance, positive control pairing, clean oracle command and regression preservation separately. Twelve synthetic classification checks pass, including missing rewards, timeout, wrapper error and parse failure; these are reader checks, not live control outcomes. No new remote execution or model calls.

## 2026-10-23 — positive controls, incomplete dependency receipt

The existing control handle succeeded in 586.168 seconds (0.651298 allocated CPU-hours). Hash-verified the 44,324-byte archive and all reported outputs. Nop0/oracle1, 1 F2P repaired, 10 P2P passing in both arms, oracle exit0, twelve files unchanged. Both verifier logs show successful offline-cache editable rebuilds. The supervisor captured no wheel receipt, and nested archive inspection found no executed receipt line; preserved this provenance gap rather than inventing dependency versions or rerunning. See `control-diagnosis.md`. Reconciled CPU allocation and reserved 1/6 CPU-hour for later cleanup. No model calls.

## 2026-10-23 — archival and owned cleanup verified

All sixteen reviewed reconstruction/control snapshot objects passed anonymous HF readback (receipt on #33 branch). The journal then submitted one reserved ownership-gated cleanup attempt. It succeeded in 13.45 seconds, 0.007472 CPU-hours; the 623-byte output archive was downloaded and hash-verified. The cleanup receipt proves no owned images or containers remain and cleanup tools were removed. Total #34 allocation is 2.211349 CPU-hours. The small cleanup archive remains durably local pending HF preservation. Dependency receipt capture remains unresolved; no rerun was launched.

## 2026-10-23 — early receipt capture prepared

Prepared a separate wrapper instrumentation candidate to copy the receipt immediately after image build, before Harbor task startup/teardown. It uses a stopped networkless bounded container and no image execution. The original wrapper is unchanged. Five synthetic checks pass: stopped capture/repeat, foreign-image refusal, failed-copy cleanup, target-wheel rejection and changed-receipt preservation. No remote run. Recorded a proposed combined unattended comparison and an eight-CPU-hour worst-case planning bound; no reservation or submission yet. The existing reconstruction was already cleaned, so any repeat is a distinct reconstructed environment.

## 2026-10-23 — combined unattended job frozen

Implemented a sequential job entrypoint that checks its entire payload, reuses the frozen original replay with separate ownership, requires smoke/fresh-image success, prepares and independently verifies the candidate archive, and invokes the unchanged control commands through the receipt-capturing wrapper. Original ten-file inputs were verified. A local packaging check passed against those real inputs with an explicitly synthetic image digest: twelve candidate files, nine unchanged original assets, and overwrite refusal. No Docker execution is claimed. Froze 25 payload files with exact hashes. Added a bounded single-attempt submitter, terminal collector and ownership-scoped confirmation cleanup code. This is prepared only: no CPU reservation, preflight or submission has occurred. Readback, archival and outer lifecycle wiring must be completed before launch.

## 2026-10-23 — confirmation readback and cleanup gates

Prepared the bounded confirmation archive reader, including payload/output hashes, reconstructed image binding, unchanged twelve-file task inventory, two dependency receipts and original control parsing. Parsing the first verified run reproduces its positive/clean pair and rejects duplicate arms; this is reader validation, not a new control result. Confirmation cleanup is restricted to the same worker and owned labels and requires the exact job archive's verified HF receipt, including on a preserved failed run. Reserved eight CPU-hours for the combined run and 1/6 for cleanup in #33. Worst-case child total is 10.378016 hours. No preflight or remote submission at this checkpoint.

## 2026-10-23 — unattended confirmation submitted

The checkpointed controller verified all frozen inputs, performed preflight and submitted `/exedev/biotasks34-macs-742-confirm-001` from source checkpoint `c2b401d3`. The first authoritative observation at 23:12:40 UTC was pending. The controller remains live in local tool session40839 and will collect the same handle on a five-minute cadence, then verify/archive and submit the separately reserved owned cleanup. See `confirmation-submission.json` for public resource/payload bindings; the exact worker remains in the protected submission. Do not invoke a second watcher or resubmit on observation failure. No model calls.

## 2026-10-23 — real controller restart verified

At 23:17:41 UTC the confirmation handle was running. Stopped only the sleeping local controller, then resumed it from the identical journal/submission in session6070. At 23:23:22 the same handle was authoritatively running, without a new submission. Updated continuation metadata to place first-comparison successes under `prior_completed_comparison`; none is presented as a result of the currently running confirmation. Final control/receipt/cleanup outcomes remain unverified.
