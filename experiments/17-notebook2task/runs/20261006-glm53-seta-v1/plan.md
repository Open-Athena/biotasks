# GLM-5.3 SETA baseline pilot

User explicitly requested GLM-5.3 using the existing bulk service and authorized
an Iris CPU job or Daytona for execution. Reuse the existing inference service;
no GPU or inference deployment. This CPU job runs two sequential idea-stage
trials with unchanged SETA text, the same observed comparison inputs and a
bounded read/list/write tool loop. It does not execute scientific code.

Per-case limits: 8 minutes, 12 requests, 4096 generated tokens per request,
temperature 0.6; service-default reasoning behavior is not independently pinned.
Tool reads are 12000 characters and the accumulated JSON context is capped at
90000 characters. One CPU, 4 GiB RAM, 8 GiB disk, total job timeout 20 minutes,
no failure/preemption retries. Source inputs and rendered template paths are
checkpointed before launch. Runtime prompts and exact API responses are saved.

This is a different model and harness from the Codex pilot. Compare descriptive
outcomes; do not attribute differences solely to model quality. Tokens are
observable; the service's billing arrangement is not independently observable.
Bulk access and remote route configuration stay outside the public repository.

Native task validation remains a subsequent stage. First inspect the GLM drafts
and complete a task package; keep the prior Codex builder timeout intact.
