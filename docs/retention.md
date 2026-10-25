# Retain held native evidence

`biotasks retain` preserves a supported native failure separately from its
scientific result. It reads an existing frozen validation plan and original
source/worker/accounting evidence, prepares an immutable snapshot, applies the
original publication eligibility policy, verifies readback, and finishes only
the original pre-reserved exact-worker cleanup. It never starts or retries a
primary/model job, changes a task/reward, or rewrites the original held journal.

```bash
biotasks retain plan /durable/native-validation \
  --work-dir /durable/native-retention
biotasks retain run /durable/native-retention --once
biotasks retain status /durable/native-retention
```

Planning and default execution are offline. Before a new public transfer or
uncached cleanup, the actor stops at the corresponding gate. Once the operation
is authorized, use `--allow-publication` and/or `--allow-cleanup`; these flags
never replace the original publication, worker, SDK/config or ledger gates.
Completed original cleanup is imported read-only, without another job or
rewriting reconciled accounting. A missing/uncertain cleanup handle retains
the original intent and reservation instead of submitting a replacement.

Support is deliberately limited to `Native reward disagreement` on the pinned
upstream profile. Both native trials, task/agent paths, deterministic agents,
commands, original deadlines/resources, unchanged grading assets, build/image
and wheel identities, terminal primary/stop accounting and safety stop must
verify independently. Unknown holds are reported as `held_unsupported` and
remain held. Incomplete or altered provenance fails closed.

The actor derives bounded UTF-8 verifier-text inspection views from the
source-bound task/agent/trial paths. It removes NUL padding only while inspecting
those exact bytes for unsafe data; it stores the original bytes and hashes.
It accepts no operator-provided log hashes. Foreign paths, arbitrary binary,
credential-shaped data, invalid UTF-8 and oversized logs remain rejected.
This is an inspection policy, never a log parser or grading repair.

`retention_complete` means the evidence and owned cleanup were verified. It
always reports `scientific_state: held_unaccepted`, false scientific/native
acceptance, the unchanged original held journal and separate publication/cleanup
receipts. A late reward file cannot become an accepted native reward. Repeating
a completed sidecar verifies evidence locally and makes no transport call.

The [generation loop](generation.md) uses this sidecar automatically for a
supported hold after native validation has been authorized. It records an
unaccepted, ineligible bundle outcome and may continue to the next group only
after preservation and cleanup complete and admission is still open. Unstarted
groups are never skipped. Unsupported failures, incomplete retention, CPU holds
and closed admission stop later execution. Normal accepted controls still use
the original collector and all original acceptance conditions.

The CLI, policy tests and archived-source proof do not establish fresh native
execution or general support for other failure families. Public eligibility is
still an explicit operator declaration with retained source notices; this tool
does not infer redistribution rights. See [storage](storage.md) for append-only
snapshots, anonymous readback and retention.
