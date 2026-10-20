# Official native run active

Issue #25 remains open. The official entrypoint is running on the authenticated,
bounded TRC controller as `/exedev/biotasks25-official-001`, using checkpoint
`8c67bf99`. No upstream source has been modified. This is not yet a completed
pipeline result or a scalability conclusion.

## Verified prerequisites

- Official source archive and frozen dependencies installed successfully.
- All five native date-window configs passed upstream validation.
- Docker client/daemon compatibility and the approved two-container resource
  guard passed live checks; installation-check cleanup and archive readback passed.
- The user completed a fresh GitHub device login on the controller. No existing
  local GitHub credential was extracted or transferred.
- Native GLM-5.3 calls through OpenRouter have begun successfully. There is no
  fallback and no external LLM repair stage.

## Current execution boundary

Three repositories, at most one bootstrap per repository, 20 native agent turns
per bootstrap, a $5 estimated stop threshold per repository, and unchanged native
2,048-output-token requests. The estimator is best-effort: early calls show
$0.0000 estimates, which must not be interpreted as zero billed cost. Model
responses marked INVALID by upstream remain native failures; no settings are
changed in response.

The five recorded windows cover the five comparison inputs and 11 additional
same-day inputs before native filtering. Subsequent windows reuse the native
bootstrap cache; they remain unresolved if that cache/image is unavailable.

## Remaining completion requirements

Record all native outcomes, export counts, usage/cost evidence and limitations.
If tasks are exported, run official base/reference grading on the preserved
images, without repairing source, tests or outputs. Keep native acceptance
separate from grading results. Verify final archived artifacts and cleanup,
then publish immutable evidence and a conclusion before closing #25.

The first installation submission was unschedulable with zero attempts because
its pinned worker disappeared. The second succeeded. Those infrastructure
attempts are separate from the native pipeline results.
