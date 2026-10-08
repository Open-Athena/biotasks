# Embedded solver trace viewer

The explorer's Attempt tab embeds a self-contained iframe using
[atif-lens](https://github.com/Eli-Chandler/atif-lens) at the revision in
`vendor-manifest.json`. Vendored source is unmodified and MIT-licensed; its
license is retained in `vendor/LICENSE`. React, Markdown and syntax highlighting
are bundled with esbuild; Tailwind generates static CSS. No CDN, backend or live
model connection is required. The iframe blocks network requests with CSP.

`main.tsx` supplies search, optional setup messages and step grouping.
`pi-tools.tsx` renders Pi bash commands and written files as highlighted code.
Tool results and reasoning use the upstream expandable components. Code and
output panels have bounded height. The submitted report and grading annotations
remain outside the recorded trace.

## Rebuild

Under the repository's shared-node resource guard, install the pinned lockfile
with `npm ci --ignore-scripts --no-audit --no-fund` in this directory, then run
`node build.mjs`. Rebuild the parent explorer with `explorer/build.py` afterward.
The generated JS/CSS and self-contained HTML are committed for HTMLPreview.

## SETA evidence

The completed 2026-10-08 Pi/GLM-5.3 attempt was copied read-only from the active
Iris orchestrator after its SETA sandbox had been removed. The original retained
file is Pi's JSONL event stream (`agent/pi.txt`); Harbor did not produce a separate
ATIF file or native session directory in this run. `convert_pi.py` derives the
ATIF display from `message_end` records, pairs tool results by call ID, and omits
intermediate streaming deltas. The source SHA256 is recorded in the derived
trace. An `agent_end` event and zero pending calls establish that this SETA trace
is complete. This does not describe BixBench's state.

The derived trace contains 12 messages (2 setup messages, 10 agent messages) and
10 tool calls. Aggregate input/output/cache counts match Harbor's result record:
91,715 / 10,566 / 78,080. The released verifier passed all 10 tests and assigned
reward 1.0. The visualization preserves that grade; it is not a new scientific
audit or a regrade.

`check_trace_browser.py` in the parent directory checks the real trace offline,
including search, tool expansion, recipe isolation and mobile width. Browser
checks need an existing Playwright/Chromium environment and the shared-node guard.
