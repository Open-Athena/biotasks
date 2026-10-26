# Reuse the existing empty-response retry for empty provider aborts

The original184 final review returned finish_reason=abort, empty content, no tool/function action and no refusal. Its original adapter rejected that incomplete response and stopped. Full original archives and fresh cleanup remain unchanged; this is not a scientific rejection. [Original observation](../../panel-rounds/088/provider-abort-184.json).

The next-version adapter routes only that strictly empty aborted response through its existing single empty-response retry. Stop/tool_calls empty responses and empty aborts share the same stage-instance counter, including upstream resubmissions. Original replies and ledger entries remain preserved; no tool/artifact is accepted from the aborted response. Partial content, tool/function actions, refusals, filtered responses, exhausted allowance and deadline still stop. The change adds no retry category, stage, quality repair, resource/time/token or request allowance.

All234default project tests and lint/format/type/pre-commit checks pass;139affected source/clock, construction and specification/review checks pass. Tests use synthetic responses matching the archived shape; this is not a live second response or recovery of184. Live adoption requires a fresh source-only campaign.
