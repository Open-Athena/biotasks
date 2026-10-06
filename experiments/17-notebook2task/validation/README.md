# Preparation checks — October 6, 2026

This validates template packaging and the explorer, not task generation or science.

- Locked Python 3.13.13 environment: Ruff lint and formatting, ty, all five pytest
  tests (including wheel/sdist installation and external CLI use), and all
  pre-commit hooks passed. No GitHub CI claim.
- Initial reuse of another checkout's tools made ty resolve the wrong environment;
  that attempt failed. Offline sync then failed because the pinned uv wheel was
  absent from the selected cache. A fresh locked sync resolved both; the final
  run used this checkout's `.venv` and `/tmp/biotasks17-uv-cache`.
- Offline Chromium checks passed for all 14 detail cards, repository and role
  filters, empty search, reset, filtered JSON download, and 390px layout without
  horizontal overflow. No page errors. Desktop screenshot inspected.
- Initial sandbox browser startup was denied by the process sandbox. An elevated
  attempt with single-process rendering also failed. Issue #5's previously used
  Chromium configuration succeeded. Owned browsers were closed after each attempt.
- Resource receipts preserve start/end times, exit codes and sampled process-group
  RSS. Measurements are sampled, not exact aggregate high-water marks. Work ran
  with the nonblocking shared lock, single-thread settings, reduced CPU/I/O
  priority, admission checks, and active resource monitoring. No paid compute.

Reproduce code checks using the commands in root AGENTS.md. Rebuild the explorer
with `python experiments/17-notebook2task/explorer/build.py`. Its browser checker
uses an existing Playwright environment and Chromium (`CHROMIUM` can override
its executable); pass a public preview URL as the optional positional argument.
Apply the shared-node guard before any browser, test, or build invocation.

## Full original notebook view

The pinned TAL1 notebook loaded in the embedded nbviewer frame: more than ten
code blocks and full text were present, the visible frame was inspected, and
returning to task ideas worked. Saved Colab output JavaScript initially raised
`google is not defined`; output scripts are now disabled in the frame. Static
cells and saved static outputs render, but interactive widgets and script-based
math rendering may be unavailable. External links allow opening the source.
Earlier viewer checks also assumed an incorrect nbviewer CSS selector; retained
failed receipts are test/setup outcomes, not notebook-conversion outcomes.

The first public HTMLPreview check exercised the controls successfully but
reported a script error: HTMLPreview tried to execute the JSON data block as
JavaScript. Replaced the inert JSON block with a safe JavaScript data assignment
(the builder still escapes `<`). This is a hosting compatibility correction.

Final public verification passed at explorer commit
`365a27799a1dc936d9f3b2ccefd8e282d53227be`: all 14 detail cards, filters,
reset, empty search, JSON export, and desktop/mobile checks, without page errors.
A separate check on that public URL loaded the full TAL1 nbviewer notebook and
returned to task proposals successfully, with no page errors. Other external
notebook/document embeds were not individually browser-validated.
