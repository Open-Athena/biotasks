# Issue 33: unattended validation

## 2026-10-23 — scope and budget

The user authorized independent weekend work with less than $100 extra spending and issue/HF records. Created epic #33, kept #28 closed and #29–#32 open, and started from main `2a1950d239f1ada467c35393991dac87debe35f7`. The operating ceiling is $90 across incremental billed services, leaving a $10 margin. Initial work uses no model calls or new paid capacity; paid model execution stays disabled until conservative request-cost reservations and actual provider reconciliation are implemented. The first remote stage may use at most 32 additional allocated CPU-hours on existing reserved TRC CPUs. Research inputs and outcomes remain separate from prior experiments.

## 2026-10-23 — source inspection changes the diagnosis

PR742's original exported `environment/docker-compose.yaml` maps PyPI and GitHub hosts to `0.0.0.0`. This is the pinned upstream answer-leakage guard, not an accidental missing Iris network setting. The #29/#31 Docker wrapper changes the resource/network properties but retains these task-provided `extra_hosts`. The candidate verifier replays a recorded editable install needing isolated build dependencies, so it conflicts with the preserved guard. Existing logs report refused package-index connections and `rebuild_incomplete` on both controls. Do not remove the guard to make a task pass. A generic build-dependency cache or distinct trusted preparation stage needs its own controlled comparison. No rerun or repair was performed for this finding.

The previous #31 license assessment relied on GitHub's null license metadata. #28 already retained actual MACS BSD-3-Clause notices at PR742's exact base and head, plus a reviewed original archive and upstream Apache-2.0 notice. Reuse those source notices and inspect the new artifacts before publication. This corrects the claim that source terms are wholly unknown; it does not automatically clear new downloaded data or an image release.

## 2026-10-23 — verified durable MACS archive

Preserved all eight reviewed #31 execution archives, source notices and provenance in the public HF bucket under `research/33-unattended-validation/2026-10-23/079a0f50dce9cb6c09984c6a4313b97eda8578ae859da0c12d2b143fa007185b`. All 31 objects passed fresh anonymous download and checksum verification, including nested archive member checks. The upload/readback completed in 21.06 seconds with peak RSS 115,400 KiB and exit status 0. Owned readback/cache directories were removed. No model calls or remote jobs were launched. Storage billing is not yet reconciled; retain the conservative $10 reservation. Original control failures remain unchanged.

## 2026-10-23 — control reconciliation

Recomputed #28 acceptance predicates and #29 paired outcomes with source-hash checks. The 83 exports remain 83; 74/59 original positive/clean counts become 82/67 ever-positive/ever-clean across separately retained environments. Ten follow-up pair slots cover nine existing tasks. Scanpy4389 remains without a positive pair; 15 tasks have positive tracked tests without a clean command. Full content/image identity reconciliation remains pending. No model calls or remote jobs. See `control-reconciliation.md` and the machine ledger.

## 2026-10-23 — offline preparation child issue

Filed #34 and verified its GitHub sub-issue relation to #33. It isolates base-revision dependency preparation while preserving the task egress guard and recorded rebuild/test commands. The first controlled comparison has a maximum 12 allocated CPU-hours inside the shared 32-hour ceiling, with no reservation consumed until a concrete run is checkpointed. Static planning checks are on `codex/research/34-offline-rebuild`; compiled fixture and live task controls remain unexecuted. No new model calls or remote jobs.

## 2026-10-23 — content identity reconciliation

Bound all83 original exports to canonical ten-file inventories from retained full-phase manifests, checking each phase digest against its original result record. All nine #29 follow-up task input inventories match the original paths, sizes, modes and hashes exactly. Each original task now has a deterministic content identity; original/reconstructed execution attempts remain separate. This step uses previously retained member hashes, not a fresh readback of all raw files. Matchms's old unpublished-private manifest supplies only the historical inventory: its obsolete private-bucket location is not claimed as current storage. Explicit base/head revisions and runtime image digests remain pending. Counts remain83exports,82ever-positive and67ever-clean; no new runs or model calls.

## 2026-10-23 — exact exported source/image metadata

Downloaded the public Cobrapy/OHIF/Scanpy phase archives and build records with the bounded one-stream HF profile, and read the protected original Matchms archive locally. Verified source archive digests and every selected task.toml against its recorded member hash. Recovered base commits and bootstrap image identities for all83tasks;77have original runtime build records, while six have none. PR head commits are not present in exported metadata and remain explicitly unknown. No current GitHub PR head was substituted. Temporary downloads/cache were removed. The first attempt stopped on a231,639-byte OHIF task.toml exceeding the initial128KiB metadata bound; increased the bounded read to2MiB, with each selected member verified against its manifest and an overall256MiB streaming limit. Counts and control outcomes unchanged. No new execution/model calls.

## 2026-10-23 — full task/attempt identity join

Recovered all83head commits from the original compressed discovery records, checking their member hashes against the original phase manifests. Joined those heads to the exported base commits, ten-file content identities and original runtime-build digests. Verified #29's three retained bounded-build records against the control archive inventories and attached reconstructed runtime image digests to the ten later pair slots. The final `task-execution-ledger.json` has83tasks and93attempt slots,87with recorded runtime image digests; the six originally unbuilt slots remain explicitly absent. Every positive pair has a recorded runtime image. Stable task identities do not conflate reconstructed environments with originals. Counts remain82ever-positive and67ever-clean. Image availability and dataset release readiness are not established. The epic's task-level reconciliation deliverable is complete, while archival, candidate validation and unattended-runner work remain.

## 2026-10-23 — remaining archive inventory and recovery

Inventoried18accounted output archives across #29/#30/#32. Sixteen had matching protected local copies; recovered the two missing #29 cleanup archives from their original remote locations (1,083 and349bytes), verifying size and SHA-256 against accounting. All18now have verified local copies. Five raw Matchms archives remain excluded from public upload pending curated review. The other13pass the bounded recursive text/archive structural scan; this is not yet public-eligibility approval. No remote compute/model calls. The recovered copies live under #29's ignored `inputs-private/matchms-cleanup-001/outputs.tar.zst` and `inputs-private/ohif-cleanup-001/outputs.tar.zst`; retain until eligible durable archival/readback or explicit private-retention handoff. No operating-system temporary directory is used.

## 2026-10-23 — non-Matchms evidence archived

Published thirteen reviewed #29/#32 non-Matchms execution archives with accounting and matching source notices in append-only HF snapshot `research/33-unattended-validation/2026-10-23/db8604c842f593aef5ebac94103de7de4363d72851fb655150fdb1c49733a6bd`. All50objects passed anonymous download/checksum and recursive archive-member verification. Owned transfer cache/readbacks were removed; no overwrite. Five raw Matchms archives remain protected locally, pending curated-summary retention. No new remote compute/model calls; storage billing remains unreconciled under the existing$10reservation.

## 2026-10-23 — follow-up retention milestone

Published whitelisted scalar Matchms outcomes/provenance for #29/#30/#32 under HF snapshot `research/33-unattended-validation/2026-10-23/c89055424187380fb21b47a335ab4946bf60f30d86d863ca4ef35d09bb559572`; all5objects passed anonymous checksum readback. No raw logs, patches or fixture data included. Removed verified staging. Together with prior snapshots,21eligible full archives are public and five raw Matchms archives remain protected locally with exact path/hash retention records. This completes initial #29–#32 eligible-evidence preservation, not public release of the restricted originals or retention of future #34 outputs.

## 2026-10-23 — reusable-change assessment

Reviewed exact #30 transport and #32 completion candidates against their recorded experiments. Stdin transport has synthetic payload and one live control-parity support, but timeout cleanup remains an independent obligation. The initial outer completion check is insufficient; the stronger pytest candidate has real synthetic runner evidence but lacks biological Harbor validation and skips other runners. Targeting changes test scope and is not bundled into completion correctness. Recorded the qualified decisions and source hashes; no new test run, job, model call or pipeline change. This completes the epic's assessment item, leaving offline comparison and resumable-runner demonstration outstanding.

## 2026-10-23 — resume controller implementation

Added a one-step journal controller with atomic, fsynced intent records, per-run controller locking, immutable input/evidence bindings, semantic stage verification and explicit recovery rather than automatic retry of unknown effects. Eight synthetic interruption checks passed. Added an adapter for the existing #34 candidate and fixed control handle; it cannot submit or regenerate controls. Two separate local invocations independently verified all twelve candidate archive members, then resumed the journal and adopted the existing submission. These are real frozen-input/adoption steps, not automatically launched controls. Remote collection/readback are wired; HF publication and cleanup stages remain explicitly unimplemented and pending. No new remote work or model calls.

## 2026-10-23 — control evidence and archive admission

The resume controller collected terminal accounting and hash-verified the same #34 control archive without new submissions. Controls are positive and the oracle command is clean; the actual wheel receipt is absent, so provenance remains qualified rather than inferred from source. Reconciled total allocated CPU usage to 2.203877 hours and reserved 1/6 hour for cleanup. Prepared a bounded 16-object, 155,170-byte snapshot after nested text/archive inspection and exact historical notice checks. Publication has not yet executed. Wired the existing add-only HF publisher and ownership-gated cleanup into the journal, retaining explicit preconditions for reviewed manifests and budget admission.

## 2026-10-23 — resumed lifecycle through owned cleanup

The real journal now contains all eight stage receipts: frozen candidate, adopted control submission, terminal accounting, archive readback, public review, sixteen-object anonymous HF readback, terminal cleanup and verified cleanup. Repeated invocation returns complete without another effect. This proves resumption of an existing export/control lifecycle across separate processes; it does not demonstrate unattended initial control submission. Updated `resume-demonstration.json` preserves that distinction. No active jobs or retained reconstruction image remain. Total allocated CPU usage is 2.211349 hours; CPU reservations are fully reconciled. The 623-byte cleanup archive still needs HF preservation, and missing dependency receipt capture remains an open scientific-provenance requirement. No model calls.

## 2026-10-23 — cleanup archive preserved

The six-object cleanup metadata snapshot (15,218 bytes) passed complete anonymous HF readback under its own append-only prefix. No external temporary archive now remains unpreserved for the first #34 comparison. Transfer caches/readbacks were removed automatically. Snapshot staging remains small and is retained because the current journal rechecks staged file bindings; deleting it requires updating the completed-stage verification contract rather than silently breaking resume. Original private archives remain local as verified evidence. No model calls, remote runs or new reservations.

## 2026-10-23 — unattended confirmation admitted

Completed the first-submission controller: fixed-handle submit, five-minute observations, terminal accounting, bounded readback, reviewed-family snapshot generation, add-only HF upload/readback and ownership-gated cleanup. It uses the existing journal with explicit stage names and durable intent recovery; nine interruption/transition checks pass. New parser code reproduces the prior verified pair and refuses duplicate arms. Generated manifests are output evidence; their committed generator and eligibility policy enforce the fixed public MACS source family, notice digests, nested text/credential scan and four-MiB/sixteen-file bound, avoiding a human manifest-commit step. Default archive publication keeps its previous gate.

Booked eight CPU-hours for one combined job and 1/6 hour for later cleanup. Worst-case child allocation is 10.378016 hours including prior work, below twelve; the epic ceiling remains thirty-two. Model execution stays disabled. No preflight/submission has occurred at this checkpoint. The same command can resume after interruption without new handles or task repair.

## 2026-10-23 — separate diagnostic identity

Added a source/hash-bound ledger for MACS PR742. It is absent from the frozen 83-export task ledger, so its #31 failed exported controls and #34 successful offline-cache controls are attempts for a separate diagnostic task. Nine original non-Dockerfile assets match exactly across those variants. This leaves the original cohort's 83/82/67 denominators unchanged. The currently submitted confirmation is not counted until its verified result exists. A first path-resolution typo in the ledger script was corrected before producing output; no remote run or source artifact was affected.

## 2026-10-23 — real controller interruption

Authoritative observation at 23:17:41 UTC showed the existing confirmation handle running. Intentionally interrupted only controller session40839 during its sleep; it exited130 with KeyboardInterrupt. Restarted the same command in session6070. Journal and submission SHA-256 values remained identical, and startup resumed waiting on the same stage without preflight or submission. The next scheduled authoritative observation is still required before closing the restart proof. Added the current completion audit and operational runbook; both retain pending scientific, archive and cleanup gates. Known disposable fixture `/tmp` prefixes and partial-transfer files are absent.

At 23:23:22 UTC the resumed controller authoritatively observed the same fixed handle running. Journal/submission bytes still match the pre-interruption hashes, with no re-entry into the submission stage. Final one-attempt accounting remains pending. Five protected raw archives were independently rehashed against retention records; all match and none was uploaded. The current audit and restart proof are checkpointed without claiming scientific completion.

## 2026-10-23 — final comparison validity gate

Added a post-run evidence summarizer that verifies all eight journal stages, exact archive/HF/cleanup bindings, one-attempt accounting and the live restart proof. Scientific acceptance is reported separately from lifecycle completion. It also requires matching wheel filename/version/hash/size sets and matching Python/platform across the two control receipts; satisfying the same version ranges alone is insufficient to establish the same control environment. Four synthetic checks accept equal records and reject missing receipts, changed wheel bytes or changed interpreter evidence. This reporting check does not alter task execution, grading, dependencies or the currently running controller. No live result is available yet.
