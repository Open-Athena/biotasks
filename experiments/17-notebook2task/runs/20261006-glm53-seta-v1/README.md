# GLM-5.3 attempt: blocked before execution

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

Next step: restore an approved, reachable route to the existing GLM-5.3 bulk
service and rerun the same bounded protocol. Subsequent trials use GLM-5.3;
the earlier Codex pilot remains separate evidence. Native task validation still
depends on obtaining and completing a task package.
