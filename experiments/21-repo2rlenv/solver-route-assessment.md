# Free GLM solver route: preparation status

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
answers, grades or model usage. No solver request has been made for #21 yet.
