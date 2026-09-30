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
