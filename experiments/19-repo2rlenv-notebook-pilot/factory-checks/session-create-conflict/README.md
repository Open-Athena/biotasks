# Session creation conflict recovery

Scanpy 206 failed before an execute request: creation timed out, a lookup reported 404, and retrying creation with the same session ID returned 409. Its complete original failure is retained in [result 206](../../panel-rounds/102/result-206.json).

The general correction reconciles only a conflict on the existing sole creation retry. It must observe the same empty session before submitting the command once. Unknown identity, unexpected commands, failed lookup or an initial unexpected conflict remain failures. The original deadline and uncertain-command cleanup remain unchanged; no scientific prompt or execution/repair budget changes.

182 affected tests and eight source-admission/refusal tests pass. The actual provider check ran three bounded cases: an existing empty session after response loss, a confirmed absent session, and late visibility after one injected stale 404. The last case received an actual provider 409 and verified the actual empty session. Every nonce-bound command executed once. Injected faults are explicit; this is neither biological validation nor a claim that the original natural outage was replayed. The check took 16.677 seconds; original cleanup and fresh ID/owner absence pass.

[Configuration](live-check-configuration.json), [provider summary](integration-summary.json), [fresh cleanup](live-fresh-provider-cleanup.json), [offline checks](offline-checks.json). Full original control records are retained in the durable private issue handoff. One initial launcher import failure created no resources; a subsequent readback refused different JSON serialization before comparing semantic equality and recording both original hashes. Neither configuration was rewritten.

[Round103 admission](../../panel-rounds/103/source-admission.json) verifies the exact232-file candidate, no scientific prompt changes, the exact transport AST delta, and the new provider proof. Earlier frozen cohorts and their failures are preserved. No scientific qualification follows from this infrastructure check.
