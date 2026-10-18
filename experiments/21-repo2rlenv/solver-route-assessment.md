# Free GLM solver route: preparation and executed evidence

The pinned Repo2RLEnv `execution.harbor.run_trial` rejects any `model.endpoint`
before dispatch. This is a wrapper restriction. Inspection of the exact cached
Harbor 0.22.0 package (matching the generator lock) finds Terminus-2 accepts
`api_base` and `llm_call_kwargs`; its LiteLLM client forwards the former as the
request base and merges the latter into completion arguments. Source hashes are
recorded in solver-harbor-source-inspection.json. This is source inspection,
not a live solver compatibility result.

The intended owned adaptation is an Iris CPU Harbor orchestrator using the
existing approved free GLM endpoint, with Daytona tool environments. Resolve
service routing inside the authorized job; supply credentials only to the
host-side model client. Preserve the native task's separate verifier and
no-network learner policies. Harbor 0.22.0's Daytona environment advertises
network disabling and CPU/RAM requests; these capabilities still require live
controls on an accepted task rather than assumption from declarations.

Use one blind attempt per independently validated task, a 900-second agent
limit, 12 turns and 2,048 output tokens per request. Generation's medium effort
and 131,072-token allowance do not carry over to the solver. A small solver
allowance may be exhausted by reasoning; record that outcome rather than
silently raising the limit or disabling thinking. No paid fallback or model
switch is allowed.

Before the first solve, validate the exact agent settings with mocked transport
and run no-model provider controls. Preserve all existing failed/rejected tasks
separately. Capture solver transcripts and artifacts before teardown; public
receipts must exclude credentials and private routing fields without altering
answers, grades or model usage. That was the initial preparation state. Executed results are recorded below.

## 2026-10-18 executed bounded pilot

Eight independently accepted tasks each completed one blind attempt with the agreed900s/12turns/2048output limits and no trial exception. Native rewards were positive for portable PR2633, LCC, three SCALER instances, Esty interval and observed_features; fixture-adapted R2E-Gym PR2633 scored0 after12 turns without editing the source. All solver sandboxes independently confirmed absent; each trace is preserved in a public HF snapshot with anonymous object/member verification. See the case-linked [reconciliation](evidence/interim-results-20261017/reconciled-subset.json) and individual solver summary files. This establishes the owned provider/scaffold route for these profiles, not a supported native custom-endpoint path, general Harbor compatibility, representative benchmark rate or Atlas admission. Generation token/effort settings remain separate.
