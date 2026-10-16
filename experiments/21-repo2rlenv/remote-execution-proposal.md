# Remote execution proposal

Status: prepared, not launched; billable allowance awaits user approval.

The remaining executable recipes require Docker builds and target-code execution
on remote workers. Start with the pinned Repo2RLEnv Daytona worker probe before
committing generation time to a backend that may not support Docker-in-Docker.

## Requested campaign limits

- At most $25 total incremental CPU/sandbox charges, including failed builds and
  the controller. This is a spending allowance, not a price quote or a promise
  that every recipe will finish within it. Establish a conservative resource-rate
  estimate before dispatch; if it cannot fit the allowance, stop before launch.
- One remote generation worker at a time: 2 vCPU, 4 GiB RAM, 10 GiB disk initially.
  No GPUs, new inference deployments, or paid model fallbacks.
- At most eight aggregate remote worker/controller hours. Each worker has at
  most a two-hour execution window. The first backend probe has a 30-minute
  controller deadline, with cleanup allowed to finish afterward.
- Existing GLM-5.3 bulk service only. Proposed ceiling: 500 model calls and eight
  million total input/output tokens across generation, repair, and review; all
  retries count. Enforce reservations before requests and reconcile usage after
  responses. No blind solver sample is included initially.
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
