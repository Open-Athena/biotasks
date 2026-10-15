# Specification run 001: invalid response

One GLM-5.3 medium call returned `finish_reason=stop` but only placeholder text,
an empty task brief and `draft_ready`. The schema/semantic validator rejected it;
no automatic retry or downstream step ran. This is a generation failure, not an
accepted task specification.

Inspect [returned content](returned-content.txt), [validation error](specify/artifact-stage/draft.json),
[usage and timing](response-summary.json), [actual prompt](specify/system-prompt.md),
and [configuration](configuration.json). The exact input is specification-inputs/001.
Original request/response and full traces remain in the original artifact archive;
small original files have verified hashes in artifact-manifest.json. The returned
content and response summary are explicitly derived views of the original response.

The request used 93,807 prompt tokens and 42,913 completion tokens (including
42,865 reported reasoning tokens). No client output-token cap was set. This does
not prove why the model emitted a placeholder. The input included the full uv lock
with many wheel URLs/hashes. The next iteration removes that non-scientific detail
from model context, retaining the lock hash and exact resolved package list.
Remote job is terminal (FAILED); no sandbox or scientific execution occurred.
