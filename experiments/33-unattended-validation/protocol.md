# Scope

Epic #33 coordinates evidence preservation, task-level reconciliation, generic candidate comparisons and one resumable validation/archive demonstration. The upstream baseline remains Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`. Compare actual source before adopting a newer upstream change. Each remote comparison must record its precise source revision, original inputs, changed behavior, resources, run handle, budget reservation, expected evidence and cleanup condition before submission.

## Execution stages

1. Review and preserve eligible original evidence with retained source notices and complete SHA-256/member inventories. Use append-only HF prefixes and verified downloads. Keep restricted bytes protected; a successful upload is not release eligibility.
2. Reconcile exports and control attempts by repository, PR, base/head, task hash and image identity. Do not add counts of control attempts as if they were distinct tasks. Missing or conflicting evidence remains explicit.
3. Investigate the native/export environment boundary without bypassing answer-leakage controls. Test general mechanisms with fixtures first, then a separately checkpointed frozen PR comparison. No manual per-task repair or additional LLM repair calls.
4. Integrate a small resumable outer runner only after checking existing upstream and repository helpers. Use deterministic identities, explicit state transitions, bounded calls, evidence before acceptance, and ownership-scoped cleanup. Test resume and failure handling rather than just successful calls.
5. Produce a reviewable result: reproducible code, measurements, exact task-level outcomes, budget ledger and HF receipts. Keep experimental branches permanent; extract any proposed supported change into a fresh pipeline branch rather than merging research history.

## Budget and stopping

`budget.json` is the incremental ledger. The operating ceiling is $90, not a post-call $100 estimate. Paid model calls require conservative admission reservations and actual cost reconciliation; unknown cost blocks only that paid operation. Existing per-repository model settings and limits remain in force. No new cloud capacity or accelerators. Reserved CPU allocation is tracked separately with an initial 32-hour ceiling. Stop repeated identical failures, preserve evidence and record a useful negative conclusion instead of exhausting the allowance. No public credentials, raw billing/account snapshots or unreviewed data.

## Communications and lifecycle

Epic and child issue bodies summarize the current result; comments begin with the repository's agent marker and carry detailed checkpoints, diagnostics and artifact links. Verify published text, labels and states. Keep #29–#32 open for user review and #28 closed. Use no task-owned `/tmp` as evidence storage; remove disposable files after verified preservation. Record private paths and cleanup conditions when public publication is inappropriate.
