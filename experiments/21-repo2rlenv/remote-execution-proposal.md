# Remote execution proposal

Status: operational and model limits below were individually agreed on 2026-10-16. The second zero-model backend probe passed, and provider deletion was verified with HTTP 404. The first probe was interrupted after an incorrectly inferred approval; its cleanup is separately preserved in the logbook.

The remaining executable recipes require Docker builds and target-code execution
on remote workers. Start with the pinned Repo2RLEnv Daytona worker probe before
committing generation time to a backend that may not support Docker-in-Docker.

## Agreed campaign limits

- At most $100 total incremental CPU/sandbox charges, including failed builds and
  the controller. This is a spending allowance, not a price quote or a promise
  that every recipe will finish within it. Establish a conservative resource-rate
  estimate before dispatch; if it cannot fit the allowance, stop before launch.
- Approved: up to four remote CPU sandboxes at once, each initially 2 vCPU, 4 GiB RAM, and 10 GiB disk. This does not set model-request or Codex-agent concurrency.
  No GPUs, new inference deployments, or paid model fallbacks.
- Approved: no aggregate remote-hour cap; the $100 ceiling applies across the campaign. Generation runs have an initial two-hour execution timeout. A fresh compatibility probe has a 30-minute execution deadline, with cleanup allowed to finish afterward.
- Existing free GLM-5.3 only, up to four simultaneous requests across the campaign. No additional global call-count or token cap. Preserve native per-request output limits and recipe repair bounds; record every call, retry, and input/output usage. The earlier 500-call / eight-million-token proposal is superseded. No blind solver sample is included initially.
- Retain the issue's three independently validated tasks / ten candidates per
  applicable route and input cohort. Stop on any campaign or cohort limit.

## First dispatch

Run `remote_worker_probe.py` with the pinned locked runtime and Daytona extra.
It provisions exactly one worker, calls the upstream binary-transfer, Docker
build, offline-network, and fresh-container probes, preserves their results, and
terminates the worker in a `finally` block. It makes no model calls and executes
no biological code. A failed probe stops this backend path; there is no automatic
Modal fallback, larger worker, duplicate launch, or relaxed isolation setting.

After the probe, finalize exact biological dependency/test profiles and model
request guards before generation. Resolve GLM from the approved execution
location at runtime; verify schema and tool support separately. Native pipelines
need a verified Docker execution route of their own. A successful research-worker
probe does not establish native-pipeline compatibility.

## Evidence and cleanup

Keep endpoint and credential discovery in a private launcher. Pass the Daytona
credential only through the controller's environment. Do not give the inference
credential to target repositories or generated task code. Keep provider receipts
and raw diagnostics private until sanitized.

Persist the worker name and creation receipt before dispatch. A creation or
observation timeout is not evidence that the worker is absent; reconcile the same
identity before any retry. Export reports before termination, verify provider
deletion, and reconcile cost from a receipt or an explicitly conservative
estimate. If artifact export fails, preserve the receipt and report the failure;
do not retain an indefinitely billable worker. Archive sanitized evidence on the
research branch or in an immutable bucket snapshot before removing temporary
local files.

## Initial rate check (2026-10-16)

[Daytona published pricing](https://www.daytona.io/pricing) lists $0.0504/vCPU-hour, $0.0162/GiB-hour RAM, and $0.000108/GiB-hour storage. Charging all 10 GiB conservatively gives $0.16668/hour for the initial 2 CPU / 4 GiB worker, or $0.08334 for 30 minutes before setup/cleanup overhead. Reserve $5 for this dispatch. This is an estimate, not an account receipt; reconcile lifetime and any build charges after deletion. The controller initially runs lightweight SDK requests on the existing VM, with no incremental remote controller allocated.
