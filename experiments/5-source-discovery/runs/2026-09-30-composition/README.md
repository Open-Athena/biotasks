# Type and primary-group distributions

The user requested distributions for each of the four discovery lists and their
merged union. Extend the standalone explorer with a dedicated Composition tab:
source types and primary groups each use aligned bars across five columns.
Show count and share together, with a common count or percentage bar scale.
The union counts each canonical source once. Each percentage denominator is the
filtered size of its own column; empty columns have undefined shares.

Use the existing frozen top-200 CSVs and canonical identities. Preserve labels,
rankings, adoption analyses and earlier artifact commits. No new collection,
annotations, model calls or paid work. This is a presentation follow-up on the
research branch, not a pipeline promotion. The original explorer and evidence
remain at commit `bd2511873049ab1d03b08f90cc77475d3f5d5519`.

Executable changes live in `../2026-09-30-explorer/`; this directory records the
follow-up build and validation. Checkpoint before building. Use the existing
builder and data verifier with a 100 MiB estimate and one offline/headless
browser under the 450 MiB shared resource guard. Test rendered counts and bar
widths against independent sets from the original CSVs at top-200 and top-100,
with type/group filters, empty columns and no results. Check desktop/mobile
layouts and then the exact published HTMLPreview link. Preserve earlier checks.

## Result and checks

[Open the published explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/20cef08c51d7b5a6ce23296a80287d58a85b29c6/experiments/5-source-discovery/runs/2026-09-30-explorer/explorer.html)
and select **Composition**. This URL pins the artifact revision.

The updated [HTML](../2026-09-30-explorer/explorer.html) is 565,346 bytes, SHA-256
`fd4298a10b19bbd0196d270fb65feaee5f8345aee0031bb39e4e98c6a1f4358b`.
Its source checkpoint is `dc96a50ac3ec581b48be08b38efb443ad12e79df`.
The current [provenance](../2026-09-30-explorer/provenance.json) records source and
input hashes. Source types have 10 categories and primary groups have 22.
The default denominator is 200 in each route and 672 in the merged column.

- [Build](build.txt): exit 0, 0.06 seconds, 27,716 KiB peak RSS.
- [Data checks](data-checks.txt): exit 0, 0.05 seconds, 24,896 KiB peak RSS.
  All 672 identities, 800 rank records, annotations and saved statistics match.
- [Offline browser checks](browser-checks-01.txt): exit 0, 4.00 seconds,
  119,820 KiB reported peak RSS. Rendered counts and bar widths match independent
  sets constructed from the original CSVs, including list-depth and type/group
  filters, empty columns, both bar scales and the deduplicated union. The
  existing interaction and twelve correlation checks also pass. Desktop and
  narrow-screen screenshots were inspected; tables scroll inside their panels.
- Python lint/format, JavaScript syntax and Git whitespace checks passed.
- [Public preview checks](public-preview-checks.txt): exit 0, 4.11 seconds,
  278,548 KiB reported peak RSS. The same numerical and interaction checks passed
  through the exact published URL above with no page errors. To repeat, add
  `--url` with that full URL to the browser command below.

Commands use the existing builder and verifier from the repository root:

```bash
python3 experiments/5-source-discovery/scripts/run_bounded.py 100 \
  .venv/bin/python experiments/5-source-discovery/runs/2026-09-30-explorer/build_explorer.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 100 \
  .venv/bin/python experiments/5-source-discovery/runs/2026-09-30-explorer/check_explorer.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 450 \
  /tmp/biotasks-explorer-browser-20260930/bin/python \
  experiments/5-source-discovery/runs/2026-09-30-explorer/check_browser.py \
  --screenshots /tmp/biotasks-composition-screenshots-20260930
```

The environment is unchanged: Python 3.13.13, Playwright 1.56.0 and Chromium
152.0.7977.64. See the original explorer record for exact browser dependencies
and the machine-specific executable path. Browser checks run outside the process
sandbox, but the offline browser context disables networking. Peak RSS is GNU
time's reported value, not the sum of simultaneous browser processes. The shared
resource guard monitors memory/load and cleans up owned subprocesses.
