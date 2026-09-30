# Top-300 depth and sparse primary-group coverage

Follow the user's directions recorded in issue #5 before execution: expand all
four lists to 300 canonical sources and compare less-frequent primary groups at
100, 200 and 300, for each route and their deduplicated union.

Use the same September 29 numerical snapshots, source identity conventions and
GitHub candidate universe as the top-200 baseline. Newly collected metadata may
resolve lower-ranked source identities but does not refresh scores or seed the
GitHub ranking. The separate known-repository audit diagnoses discovery gaps;
its additions do not enter this controlled depth comparison. Preserve all saved
first-200 IDs, scores and labels. Record corrections explicitly if evidence
requires changing those identities rather than silently replacing the baseline.

Start from the archived top-200 preparation cache, verifying each imported file
against the published cache manifest. Extend screening to at most 550 Bioconda
package rows, 350 Bioconductor rows, 400 PyPI rows and sufficient candidates from
the recorded GitHub pool. Review every newly selected source's main purpose and
identity. Reuse existing assistant labels; assign new labels from metadata and
primary evidence, making uncertainty and borderline decisions explicit. Keep
one primary group per source and the existing group vocabulary where applicable.

Compare complete group distributions at all three depths. Define the tail with
explicit count bands (0, 1, 2–5, 6–10, >10) and also track groups with 1–5 sources
at top 100 through later depths without redefining that cohort. Show newly
represented groups separately. Counts, shares, represented-group counts and
per-group changes complement these threshold-dependent summaries. Labels are
assistant-assigned and do not establish executable biological task quality.

Budget: sequential public metadata calls for at most 200 added package/source
identities; bounded read-only collection and standard-library analysis estimated
below 200 MiB. Use one worker, the shared resource guard and exact source
checkpoints. No models, candidate executions, paid compute or biological-data
files. Inputs come from the retained HF archive or recorded public metadata;
outputs and follow-up code stay on this research branch. Preserve older HTML
preview permalinks. Validate list uniqueness, numerical preservation, canonical
joins, all depth summaries and the browser before publishing a new preview.

## Findings

Each route now has 300 sources; their union has **1,014 distinct source identities**.
All 800 previously published ranking rows and all 672 existing annotations are
preserved. The union at 100 / 200 / 300 is 335 / 672 / 1,014 sources, spanning
18 / 22 / 22 primary groups and 79 / 125 / 157 finer topic labels. The last step
adds 342 sources and 32 finer labels, but no new broad primary group. Finer-label
counts depend on annotation granularity and do not measure validated task yield.

| Primary group in merged union | Top 100 | Top 200 | Top 300 |
| --- | ---: | ---: | ---: |
| Gene regulation | 5 (1.49%) | 24 (3.57%) | 54 (5.33%) |
| RNA structure | 1 (0.30%) | 2 (0.30%) | 3 (0.30%) |
| Biomechanics & physiology | 0 | 1 (0.15%) | 1 (0.10%) |
| Ecology & conservation | 0 | 1 (0.15%) | 4 (0.39%) |
| Immunology | 0 | 6 (0.89%) | 12 (1.18%) |
| Metabolomics | 0 | 3 (0.45%) | 7 (0.69%) |

The first two rows are the fixed top-100 tail (1–5 sources); the last four were
absent at 100. This distinction matters: a count of sparse groups can rise when
new groups first appear, and fall when a represented group crosses the threshold.
The merged union has 2 / 4 / 3 groups with 1–5 sources at the three cutoffs.
It is misleading to interpret that sequence alone as improving or worsening
coverage. Gene regulation fills out substantially; RNA structure only keeps pace
with the expanding denominator; biomechanics remains a single source.

| Route | Represented groups at 100 / 200 / 300 | Groups with 1–5 sources at 100 / 200 / 300 |
| --- | --- | --- |
| Bioconda | 14 / 15 / 15 | 8 / 7 / 4 |
| Bioconductor | 11 / 14 / 17 | 5 / 3 / 6 |
| PyPI | 18 / 19 / 21 | 10 / 6 / 7 |
| GitHub stars | 11 / 18 / 18 | 4 / 7 / 7 |
| Merged union | 18 / 22 / 22 | 2 / 4 / 3 |

Deeper Bioconductor selection introduces three groups after top 200; GitHub and
Bioconda introduce none at that step. Bioconductor/PyPI still have no shared
canonical source identities under this source-level policy. Bioconda/Bioconductor
have the largest top-300 overlap (73; Jaccard 13.85%; within-intersection Spearman
0.682). Other overlaps and correlations are in [rank-correlations.csv](rank-correlations.csv).
These correlations are conditional on shared selection, not population estimates.

## Screening and provenance

The numerical inputs remain the archived September 29 snapshots. Additional
September 30 metadata establishes lower-ranked source identities and annotations;
it does not replace numerical scores. The package screens extend from raw
500 → 550 Bioconda rows, 250 → 350 Bioconductor rows and 350 → 400 PyPI rows.
The GitHub pool remains the saved 1,370 candidates; identity and exclusion review
operates within it. Remaining unselected candidates are not all reviewed.

| Route | Rank-300 score | Raw package/candidate rank supplying cutoff |
| --- | ---: | ---: |
| Bioconda | 202,448 | 511 |
| Bioconductor | 1,163 | 300 |
| PyPI | 9,983 | 378 |
| GitHub stars | 673 | 353 |

The 673-star cutoff remains above the two truncated GitHub query-page tails
(642 and 523). This supports depth sufficiency for those saved pages; it does
not establish complete biological discovery. The separate
[known-repository audit](../2026-09-30-discovery-gaps/README.md) remains a diagnostic
of that pool. None of its newly nominated repositories is seeded into these lists.

[decisions.json](decisions.json) records exclusions and identity corrections.
General interval/graph/optimization utilities, nonbiological materials tools and
an ambiguous packaging-only bundle are excluded. Dedicated ecosystem support is
retained as infrastructure where documented. CUDA implementations in
`colabfold-legacy-kernels` are an independent support implementation, so a proposed
upstream collapse was withdrawn before final export. Two CellChat repositories
retain separate identities under the original fork/source policy; shared lineage
means these counts are not counts of independent scientific methods. The EMBOSS
source mirror was checked by HTTP HEAD, not downloaded or checksum-compared.

[annotate.py](annotate.py) explicitly records all 342 new labels and borderline
scope notes. All baseline labels remain unchanged. Selected README inspections
clarified mixed-purpose sources such as DataJoint, Leabra, MDF, SAX-NeRF, btrack,
DeepForest and BioPyTools. These are assistant judgments, not independent human
validation. Keeping the 22-group vocabulary makes depth comparison interpretable,
but it is not an exhaustive biological ontology. A source's one primary group
hides secondary uses, and neither inclusion nor licensing metadata establishes
execution readiness, permissive reuse or task quality.

## Files and reproduction

- [rankings.csv](rankings.csv): all 1,200 positions, native scores and package identities.
- [source-annotations.csv](source-annotations.csv) and [source-observations.json](source-observations.json): the 1,014-source union.
- [primary-group-depths.csv](primary-group-depths.csv): all 330 group/cohort/depth cells, including explicit zeroes, counts, shares and bands.
- [results.json](results.json): type distributions, fixed-tail membership, group counts, overlaps, correlations and all depth checkpoints.
- [imported-inputs.json](imported-inputs.json), [analysis-provenance.json](analysis-provenance.json), `metadata/`: verified retained inputs, source checkpoints, checksums and timestamped public metadata.
- [explorer.html](explorer.html): offline HTML with sorting, composition, overlap/correlation and a dedicated **Primary-group tail** tab.

The tail tab shows count bands for all five cohorts and a detailed aligned-bar
table at all three depths. Switch between counts and shares and between the fixed
top-100 tail, absent-at-100 groups, the remaining top-300 tail or all 22 groups.
The panel uses complete cohorts and explicitly ignores discovery filters. Select
a group to inspect its sources in the merged explorer. Other composition and
comparison panels retain their discovery filters and now support top 300.

Restore the retained provider cache at `/tmp/bio-discovery-20260929` from the
[HF archive manifest](../2026-09-30-bucket-archive/manifest.json). Existing collected
metadata is checked in; collection is not required for offline reproduction.
Run, sequentially from the checkout, under the shared resource guard:

```bash
python3 experiments/5-source-discovery/scripts/run_bounded.py 200 python3 experiments/5-source-discovery/runs/2026-09-30-top300/prepare.py assemble
python3 experiments/5-source-discovery/scripts/run_bounded.py 200 python3 experiments/5-source-discovery/runs/2026-09-30-top300/annotate.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 200 python3 experiments/5-source-discovery/runs/2026-09-30-top300/analyze.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 200 python3 experiments/5-source-discovery/runs/2026-09-30-top300/build_explorer.py
python3 experiments/5-source-discovery/scripts/run_bounded.py 200 python3 experiments/5-source-discovery/runs/2026-09-30-top300/check_data.py
```

Working `provisional.json` is reproducible and ignored; published exports are
retained. The collection's first attempt failed on a cache symlink before provider
reads; the resolved archive path was then verified. The first annotation check
caught one unassigned microRNA package; it was labeled before export. Runtime
records preserve completed collection and analysis commands, exit status and peak
RSS. Browser validation and public-preview results are recorded separately after
execution. Earlier explorer permalinks remain valid; no research merge is proposed.

## Validation

The independent data check verifies all 800 original ranking rows and all 672
original labels exactly, all 1,200 new ranking positions, all 330 group/cohort/depth
cells, embedded source data and input/output hashes. Browser checks cover all
18 ranking-pair calculations (at 100/200/300), all six separate adoption pairs,
count/share scales, all tail selectors, every cohort, zeroes, source drilldown,
CSV export, filters, sorting and desktop/mobile layouts. Chromium
152.0.7977.64 / Playwright 1.56.0 runs with networking disabled for the local
check. See `data-check.txt` and `browser-check-01.txt` for the initial passing
checks; the subsequent two-decimal tail percentage adjustment is checked in
`browser-check-02.txt`. No model calls or candidate execution are part of validation.

The generated HTML is about 807 KB, contains all data/assets and has no runtime
provider requests. Earlier preview versions are preserved. This result remains
on the research branch; no PR to or merge into `main` is proposed. Public-preview
verification is recorded in `public-preview-check.txt` after publication.
