# Bounded builder continuation

The first builder request spent 16,384 tokens in reasoning and wrote no new
files; draft_spec.md was its pre-staged input. Continue from the saved response,
retaining both reasoning field aliases for this deployed endpoint. Its observed
prompt-token counts differ between single-field and dual-field requests, so the
exact server-side history treatment remains an implementation uncertainty. The
local serialized-context budget counts the identical reasoning value once.

Retain the builder's 24-request, 15-minute and 16,384-output-token limits, with
at most two explicit finish-writing continuations after length-limited responses.
Those requests count against the existing request/time caps. Preserve all raw
responses; do not silently turn a cutoff into completion. Native validation is
still a subsequent parent stage.
