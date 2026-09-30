# Source discovery explorer

Build a self-contained HTML explorer of the saved four top-200 lists for issue
#5. Include every canonical source, including non-GitHub sources and archives;
preserve the existing identities, scores, labels and missing values. Add linked
views of exact set membership, pairwise overlap, rank agreement, source types,
topic coverage, depth gains, and the separate 95-source adoption comparison.
No new source collection, scientific annotation, model calls or paid compute.

The page embeds its data, styles and JavaScript and has no runtime dependency
on a data endpoint or chart CDN. Publish it on the research branch and link a
commit-pinned HTMLPreview URL from issue #5. Keep the original baseline frozen.
Annotations remain assistant-assigned discovery labels, not validated scientific
coverage. Missing ranks mean not selected in the recorded list, never zero.
Rank comparisons condition on the pairwise intersection; adoption comparisons
use a different fixed cohort and pairwise complete measurements.

Checkpoint the executable inputs before building. Build with
`python build_explorer.py` from this directory (or provide its full path from
the repository root). The builder writes `explorer.html` and `provenance.json`.
The provenance records input hashes and the source/code checkpoint. Run the
data checks and browser checks under the shared resource guard, recording their
results here after completion.

Local budget: builder and data checks estimated below 100 MiB; one headless
Chromium session plus its Python/Node driver estimated below 450 MiB for this
sub-megabyte static page. Use one browser and one page at a time, a single
renderer, shared nonblocking lock, thread limits and resource monitoring.
No persistent server or detached browser. The UI must work offline, with
keyboard controls and at narrow viewport widths. Check counts, correlations,
filtering, sorting, no-result states, detail links and CSV export.

## Result

[Open or download the explorer](explorer.html). Issue #5 links the published,
commit-pinned HTMLPreview version. The 562,235-byte file includes all 672 sources
and 800 rank entries, with source details, search, filters, sorting and CSV
export. Its SHA-256 is
`d74d7d4fc45a61f03d228d7bd54786a94b015d2b4700045290ecf5bf78ee0434`.
The executable checkpoint is `fec1407d4739e6961d3708d77ca91077ac7765bf`;
[provenance.json](provenance.json) records every input hash.

The four views separate source exploration, ranking comparisons, the original
95-source adoption cohort, and methods/evidence. Overlap cells and exact
membership bars drill into the source table. Pairwise rank scatterplots include
intersection sizes and Spearman correlations; type and primary-group charts
support filtering. The depth view preserves the observed 335-to-672 union growth
from top-100 to top-200 and 79-to-125 finer-topic labels. These labels are
assistant-assigned and are not independently validated biological coverage.

The optional scientific-source filter selects exactly software, workflows and
research implementations. It does not reproduce the older report's broader
software subset, which also included infrastructure. Original evidence and
interpretations remain in the frozen baseline. Adoption measurements have their
own missing-value handling and cohort; discovery filters do not alter that view.

## Reproduction and validation

Build and data checks used Python 3.13.13 from the repository environment.
Browser checks used a temporary Python environment with Playwright 1.56.0,
greenlet 3.5.6, pyee 13.0.1 and typing_extensions 4.16.0, and existing headless
Chromium 152.0.7977.64 at `/home/exedev/.local/bin/chromium`. The browser helper
records this machine-specific executable path; adapt it for another environment.
No browser or scientific runtime dependency was added to the package.

From the repository root, run these sequentially:

```bash
python3 experiments/5-source-discovery/scripts/run_bounded.py 100 \
  .venv/bin/python experiments/5-source-discovery/runs/2026-09-30-explorer/build_explorer.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 100 \
  .venv/bin/python experiments/5-source-discovery/runs/2026-09-30-explorer/check_explorer.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 450 \
  /tmp/biotasks-explorer-browser-20260930/bin/python \
  experiments/5-source-discovery/runs/2026-09-30-explorer/check_browser.py \
  --screenshots /tmp/biotasks-explorer-screenshots-20260930
```

The temporary browser environment is not retained in Git. To reproduce it,
create a virtual environment and install the exact versions above; use that
environment's Python in the last command. The builder embeds the current Git
revision, so rebuilding from a later revision changes the output hash even if
the saved data are unchanged. Use the recorded checkpoint for byte reproduction.

- [Build](build.txt): exit 0, 0.05 seconds, 27,832 KiB peak RSS.
- [Data checks](data-checks.txt): exit 0, 0.04 seconds, 24,872 KiB peak RSS.
  All identities, ranks, scores, package mappings, annotations, source links,
  list composition, expansion cutoffs, adoption observations and hashes match.
- [Browser checks](browser-checks-03.txt): exit 0, 3.00 seconds,
  123,864 KiB reported peak RSS. All six ranking and six adoption correlations
  match the saved results within 1e-12, including empty intersections and ties.
  Sorting, filtering, drilldowns, source details, CSV export and narrow-screen
  layout pass. The downloaded file works with the browser offline and makes
  no HTTP requests. Screenshots at 1440- and 390-pixel widths were inspected.
- Python Ruff lint/format, JavaScript syntax and Git whitespace checks passed.
  No supported pipeline code or original analysis inputs changed.

The resource guard checks memory and load throughout each command. Its reported
peak RSS comes from GNU time and is not an aggregate of simultaneous browser
processes; the browser was budgeted at 450 MiB and constrained to one renderer.
No owned browser worker was retained after completion.

Two earlier attempts are preserved. [Attempt 1](browser-checks-01.txt) failed
during Chromium startup with the single-process flag; removing that flag and
disabling GPU rendering resolved it. [Attempt 2](browser-checks-02.txt) exposed
mobile overflow from long select values; constraining filter widths resolved it.
Neither is a scientific-data or correlation failure. The successful attempt
used the final recorded source checkpoint.
