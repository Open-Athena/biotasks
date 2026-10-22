# Resume after user-requested VM security maintenance

The user asked to checkpoint and pause so an outside operator can perform exe.dev security remediation. No VM or software restart, trust-store edit or package upgrade was performed by this task. Official notice: https://exe.dev/security/emudhra-compromise. The documented control-plane SSH help was denied authentication; no credentials were sought or repurposed. Do not run further authenticated publication before the maintenance/reload status is confirmed.

## Execution is finished; do not regenerate or resubmit

All ten original runs are terminal, original output readback and owned Docker cleanup are verified, and the serial watcher ended naturally with exit 0. Its elevated host PID/start-tick identity is absent. There are no remaining experiment workers to keep running. Original per-response charges reconcile to **140 calls / $5.975286**; allocation is **20.03094222222222222222222222 CPU-hours**. `results/cohort-terminal-checkpoint.json` retains the safe original-run accounting snapshot. This does not assert goal completion.

The permanent branch is `codex/research/28-catalogued-fields`. Nine reviewed HF snapshots and receipts were pushed before the pause. Latest pushed evidence is `c90f6e56`; this maintenance handoff/terminal snapshot is a local checkpoint, not yet pushed. Unrelated untracked `drafts/` and `experiments/24-pr-runtime/` remain untouched.

## Persistent private state

All 635 original working files (6,110,885 bytes) were moved out of `/tmp/biotasks28-private-state` into:

`/home/exedev/.local/share/biotasks/checkpoints/issue28-20261022-security-maintenance`

The directory has mode 0700. `_checkpoint-relocation.json` records full SHA256, byte-size and file-mode readback after an atomic same-filesystem rename. Four additional task-prefixed cached source files (50,539 bytes) were moved into `_supplemental-source/` with hash/mode verification; `_supplemental-relocation.json` records those moves. No `biotasks28*` paths remain in `/tmp`. Historical owner records still mention the former `/tmp` path; use the persistent location above for every resumed helper's `--state-dir` argument. Do not move it back to `/tmp`.

This private checkpoint is active working evidence, not a public upload allowlist. It still includes OHIF's excluded account-usage snapshots/enclosing outer archive; never publish those. After final reviewed retention/readback and completion audits, remove the redundant private state and record cleanup before closing the lifecycle. Do not delete it merely because the compute jobs finished.

## OHIF result requiring final retention

The original `biotasks28-ohif-viewers-001` ended with native CLI exit 2, while the wrapper succeeded in retaining evidence/cleanup. Returned 38 candidates, entered 19; three paired validations started and two returned results. No exports or independent controls exist. Actual model cost is $0.984420 for 20 calls; allocation is 1.5977844444444445 CPU-hours. Its original assessment is already in the private result directory; preserve its bytes.

- Bootstrap smoke exits 0 and reports 1,446 passing tests. The exact standalone Jest parser maps 1,440 unique passed labels from that smoke log; do not assert those two counts are identical. The fresh check's saved summary reports 121 suites / 1,446 tests passing, exit 0. Both original bootstrap flags are true.
- PR6278 native validation parses 1,407/1,411 passing tests, F2P=0/P2P=1407. The exact standalone parser agrees. Four test cases appear only post-fix. A new Jest project config/mock is on the source side while the new test file is on the test side; collection dependence is a qualified inference, not an isolated repaired comparison.
- PR6273's test patch fails on binary screenshot entries lacking full index information. Native raw scripts contain binary-diff filenames, not `GIT binary patch` image payloads. No repaired patch application or rerun was attempted.
- PR6261 aborts at post-fix Docker exec with OSError errno 7. The separate exact public diff is 145,551 bytes; both split-patch hashes match the original validation-start record. `transport-diagnostic-pr6261.json` reconstructs strings only: pre argument 33,470 bytes, post argument 146,149 bytes. No reconstructed script was executed and the exact remote kernel limit was not probed.

The private OHIF result directory retains `diagnostic-pr6261.diff` and `transport-diagnostic-pr6261.json`. The derived Git OHIF result, final native log census and publication review were not yet written: an initial read-only analysis assertion incorrectly expected 1,446 unique parsed smoke labels; follow-up inspection established 1,440 while the raw test summary remains 1,446. This affected no execution or original evidence. `results/OHIF__Viewers-process-probe.json` is already preserved with its interpretation limits; no OOM or runtime attribution follows from process names alone.

## Finish after maintenance

1. Confirm security remediation and any required process reloads; preserve original scientific inputs/settings. No model calls, builds, controls, generation retries or replacement repos are needed.
2. Finish OHIF's derived result/census and exact source/data/public-eligibility review, then commit/push its allowlist before `archive_result.py`. Retain original phase/assessment separately from diagnostics. Native source remains pinned and unrepaired.
3. Publish the reviewed OHIF append-only HF snapshot with fresh anonymous object/member readback. Remove its redundant outer/account-usage files only after the scientific retention is verified.
4. Refresh `candidate_coverage.py` and `summarize.py` using the persistent state. Current reports intentionally still contain nine accepted results and withhold full-cohort ratios. Primary yield remains two Scanpy exports / one verified tracked-test task / zero clean verified oracle commands. Do not convert timeout rewards to zero or redefine the tracked-test criterion.
5. Run the prepared `audit_run_accounting.py` and `verify_final_archives.py` for all ten and inspect their scope. The original Scanpy direct reward audit is retained in `results/scverse__scanpy-independent-audit.json`. Complete every original requirement in `completion-audit.md`; no single helper proves whole-goal completion.
6. Finish the self-contained `conclusion.md`, with immutable pushed evidence and the final ten-row report. Its current draft remains explicitly incomplete. Preserve the original protocol separately; record the worker-revision-only last-run adaptation and environment replay limits.
7. Verify all original handles/resources/processes, preserve required evidence, delete the task-owned persistent checkpoint/caches, and record cleanup. Publish/read back the exact conclusion, verify label and close #28. Commit/push receipts and verify actual final state before marking the goal complete.

No work should resume until the user resumes this paused goal after maintenance.
