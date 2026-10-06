# GLM SETA baseline: bounded harness correction

The first live GLM pilot made 12 successful requests but produced no draft:
cytopathology stopped at the 90,000-character context ceiling; BixBench used its
entire final 4,096-token allowance for reasoning (finish_reason=length). Its
original runner incorrectly labeled that empty response completed. Preserve
those original outputs and report the corrected interpretation separately.

Retry exactly the same two cases and byte-identical prompt templates. Change
only the recorded harness limits: 180,000 serialized-context characters, 8,192
output tokens per request, explicit documented medium reasoning. Retain 12
requests and 480 seconds per case, one sequential CPU worker, no automatic
request retries, and the corrected existing-service runtime. The runner now
labels a length-limited terminal response output_limit. These changes prevent a
controlled model-only comparison with the earlier Codex pilot.

The task-authoring text is unchanged. No scientific execution, new inference
service, GPU allocation, or benchmark scoring is part of this retry. Native
validation remains a later stage. Exact requests/responses and provider usage
will be preserved; billing and served weights revision remain unavailable.
