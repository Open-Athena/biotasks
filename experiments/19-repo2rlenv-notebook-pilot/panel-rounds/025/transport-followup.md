# Command completion after a lost connection

This is a next-version infrastructure finding. It does not change any of the ten
frozen worker payloads in this cohort, recover a failed run, or establish that a
notebook is broken.

## Observed failure

Case 127's original `setup-raw/operations/0076/operation.json` records a
`DaytonaBadGatewayError` during the first reference dispatch, followed by
`DaytonaError` while trying to recover its completion receipt. The operation
started at epoch `1792799862.9348493` and was recorded as uncertain at
`1792800007.6417253`, before its original reconciliation deadline
`1792800517.9348497`. There is no verified completion receipt or output log for
this operation. Earlier reset and offline-network checks returned receipts.

The original archive manifest is
`5c9da3f7f3ffcd7881408b68b2c0cdfda1177d06f4c36c2c552c6598db3e351f`.
All 481 archived files were independently checked for size, hash and mode.
The public result and cleanup proof are in `result-127.json` and
`../../autonomous-runs/127/provider-cleanup.json`.

## General controller behavior

In factory `501fbc2f`, `Remote.command` makes one receipt-read attempt after a
transient execution error. Although that attempt is wrapped in the remaining
reconciliation allowance, a failed read immediately ends reconciliation. The
wrapper does not wait for a command that might still be running to produce its
atomic receipt. The archived exception types alone do not establish whether the
receipt was absent, inaccessible or unavailable because of another transport
failure.

`SetupSession.test_reference` then calls `remote.network(False)` in `finally`.
Because an uncertain operation correctly blocks further remote actions, this
raises a new `RuntimeError` and masks the original provider error at the stage
boundary. The original operation record preserves that error, but the stage
summary does not.

The upstream worker's download method uses the Daytona SDK's default file-read
timeout. Merely adding asynchronous retries around that method would be
insufficient: cancelling `asyncio.to_thread` does not stop its underlying read.
A reconciliation change must bound the actual SDK read as well as the outer
deadline. The inspected pinned SDK exposes an explicit download timeout.

## Candidate next-version change

Primary-error preservation is implemented in the working factory after the
frozen version: networking is not reenabled after an uncertain command, so
owner-scoped cleanup can run without masking the execution exception. The new
regression and related controller tests pass (65 checks, 3.43 seconds). This
change is not deployed to this cohort. It does not implement the receipt-wait
change described below or retrospectively recover case 127.

Keep the original operation identity, computation allowance and deadline. After
a transient loss of the execution response, perform only bounded, read-only
completion reconciliation; never submit the command again. Retry only a
verified not-yet-present receipt or a classified transient read failure. Stop
on authentication/authorization failures, malformed or mismatched receipts,
checksum failures, and deadline exhaustion. Do not interpret an untyped generic
provider error as proof that a receipt is merely missing.

Accept completion only after verifying the original nonce, argv, working
directory, timeout, exit status and log hash. Preserve each observational
failure and the original execution exception. If completion remains uncertain,
keep the sandbox offline, perform the existing owner-scoped cleanup, and report
an incomplete infrastructure outcome without replacing the original error with
a failed attempt to restore networking.

Before adopting this change, cover delayed receipt arrival, transient read
failure, persistent absence, forbidden access, mismatched identity, corrupted
logs and exhausted deadlines. Assertions must prove one command dispatch, no
extra reference or repair allowance, no deadline extension, and no network
reenablement after uncertainty. Existing tests cover already-present receipts;
they do not establish delayed-arrival recovery. Live effectiveness would still
require a future campaign, not a retrospective claim about case 127.
