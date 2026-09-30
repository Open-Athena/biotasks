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
