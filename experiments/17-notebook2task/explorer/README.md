# Notebook and task-idea explorer

`catalog.json` is the editable source of descriptions, assistant proposals,
source links, historical #10 records, and limitations. `template.html` supplies
presentation and interactions. `build.py` embeds the JSON into `index.html`,
which works offline and through GitHub HTMLPreview without external assets.

Run `python experiments/17-notebook2task/explorer/build.py` after edits.
The browser check exercises filters, every detail card, export and mobile width.
It needs an existing Playwright/Chromium installation and the shared-node guard.

The shortlist is not the run input manifest. It contains 14 source candidates,
including one API-guide seed (Atlas) and an excluded benchmark-derived Scanpy
example. Seven entries retain original source-inspection records from #10's
final commit. Multiple tasks or analyses may share one source/study. Public-use,
evaluation-overlap and resource checks remain unresolved unless an explicit
exclusion is recorded. Nothing has been scientifically executed or accepted.

Source records were inspected October 6, 2026. New suggestions use official
rendered documentation; AlphaGenome and gReLU additionally link to repository
revisions recorded that day. Mutable documentation URLs can change. Historical
#10 locators are preserved as originally reported, not reclassified as a fresh
independent source audit. References contain no credentials or downloaded data.

## Full original source view

Use “Show full original notebook” to embed a commit-pinned nbviewer rendering,
including all cells and saved outputs. Other entries embed their original hosted
analysis/API document. Embedding is lazy and sandboxed; no kernel or custom
server is needed. The service/site must allow framing and be reachable. An
external link remains available if it does not. The candidate catalog works
fully offline, while full-source embedding requires internet. No saved outputs
are represented as freshly executed evidence. The PBMC3k notebook source was
located at the same recorded Scanpy revision used by the older study; it is
still an additional shortlist suggestion, not a reused #10 unit record.
