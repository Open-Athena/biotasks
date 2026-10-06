# GLM-5.3 service working; first live pilot limited by harness budgets

The existing GLM-5.3 bulk service returned 12 successful model responses after
moving the CPU authoring job to another documented region and correcting the
launcher dependencies using the working collection from
[Marin issue #9775](https://github.com/marin-community/marin/issues/9775).
The Iris job succeeded; neither case produced a task draft.

| Case | Observed outcome | Successful requests |
| --- | --- | --- |
| Cytopathology | Context ceiling: 90,000 serialized characters | 6 |
| ASXL1 / DESeq2 | Output ceiling: final 4,096 tokens were all reasoning, with finish_reason=length | 6 |

The raw runner incorrectly labels the ASXL1 response `completed`. Its empty final
message and API finish reason establish an output-limited attempt. Preserve
that original summary; do not count it as a successful draft or an EARLY_DITCH.
The corrected runner handles this explicitly for subsequent runs.

The archive was recovered from remote logs and SHA-256 verified. See
[raw results](results/summary.json), per-case API responses and tool observations,
and [transport receipt](results/transport.json). Provider totals count repeated
context across requests: 170,432 prompt tokens and 13,428 completion tokens.
No scientific workflow was executed; these are authoring attempts, not scores.

A [separate bounded retry](../20261006-glm53-seta-v1-budget-retry/plan.md)
preserves both source prompts byte for byte and changes only recorded harness
limits and reasoning settings. No inference service or accelerator was created.

## Runtime corrections

The first region remained queued; its retry was cancelled and confirmed killed.
The alternate region started promptly. Three startup failures exposed an
unpublished package pin, disabled prerelease dependency resolution, and an
incompatible HTTPX prerelease. All occurred before model calls. The working
setup uses the published Iris/Rigging pins and HTTPX 0.28.1 from #9775, with
prereleases enabled; see [runtime correction](runtime-correction.json).
Region-local relay discovery was corrected using the service owner's guide.
Private routes and access material stay outside public artifacts.

## Initial dispatch history

On October 6, 2026, one bounded Iris CPU job was submitted at 21:27 UTC
using the [checkpointed protocol](plan.md). It remained pending while awaiting
acceptance by the destination peer. No worker logs or model output appeared.
Cancellation was requested at 21:34 UTC; the controller confirmed terminal
`KILLED`, reason `Terminated by user`, at 21:35 UTC.

A read-only direct controller check returned `Forbidden`. A read-only models
endpoint probe failed with `URLError` before returning an HTTP status. Neither
check produced an inference result. The existing service instructions were
rechecked; no updated route was established. No new inference service or
accelerator was provisioned, and no job from this attempt remains active.

This is an infrastructure outcome, not a model rejection, generated task,
scientific validation, or benchmark score. There are no GLM token-usage records
or responses to report. Private service routes and access material are excluded.
The service billing arrangement was not independently observable.
