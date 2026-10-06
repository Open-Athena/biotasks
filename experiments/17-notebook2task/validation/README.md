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
