🤖 Initial investigation is published on the permanent research branch at `726307f44ecef02e41b4e85d1622549224c8b28d`.

A candidate using stdin plus a Bash loader passes 20 bounded local cases. The original method reproduces Linux errno7 on a large synthetic script; the candidate delivers the payload exactly with a maximum 92-byte argument. Quoting, UTF-8, stdin EOF, exit/trap behavior and timeout cases were checked.

The loader reads the complete script before executing it and closes command stdin, avoiding the bash -s hazard where read/cat can consume later script lines. Original and candidate use the pinned _run implementation. The comparison took 0.83 seconds, peak RSS 28,912 KiB, with temporary paths removed. No live pipeline was modified.

Next: exercise actual Docker behavior and owned-process cleanup, then a predeclared live PR comparison. These results use a local Docker-argument adapter, not a Docker daemon or biological task. No recovery count is claimed; shell diagnostic/introspection differences and inherited remote timeout cleanup remain explicit.

[Evidence](https://github.com/Open-Athena/biotasks/blob/726307f44ecef02e41b4e85d1622549224c8b28d/experiments/30-script-transport/local-results.json) · [Scope](https://github.com/Open-Athena/biotasks/blob/726307f44ecef02e41b4e85d1622549224c8b28d/experiments/30-script-transport/issue-scope.md) · [Logbook](https://github.com/Open-Athena/biotasks/blob/726307f44ecef02e41b4e85d1622549224c8b28d/experiments/30-script-transport/logbook.md). All changes remain research-only; no promotion to main, live task repair or model spend. The issue remains open.
