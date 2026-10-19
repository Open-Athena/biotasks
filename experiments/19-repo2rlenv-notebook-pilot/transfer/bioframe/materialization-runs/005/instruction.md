# Task: assign the strongest CTCF motif to each CTCF ChIP-seq peak, then blacklist-filter the result

## Objective

For the CTCF ChIP-seq peak set from HFF cells (ENCODE, assembly GRCh38), assign to every peak the strongest CTCF motif from the JASPAR MA0139.1 track that overlaps it, and then conservatively remove any peak material lying within ±1 kb of ENCODE blacklisted genomic regions. The deliverable is a table of the retained peak intervals, each annotated with the peak's fold change and its assigned motif.

## Supplied inputs (read-only; no network access)

1. `/inputs/ENCFF401MQL.bed.gz` — CTCF ChIP-seq peaks (HFF), gzipped narrowPeak, no header. 40587 rows, each with 10 tab-separated fields in order: `chrom, start, end, name, score, strand, fc, -log10p, -log10q, relSummit`. Only `chrom`, `start`, `end` and `fc` are used; `fc` (the 7th field) is a decimal number.
2. `/inputs/MA0139.1.tsv.gz` — CTCF motif occurrences (JASPAR profile MA0139.1, hg38 UCSC track), gzipped, tab-separated. Data rows have exactly 7 tab-separated fields in order: `chrom, start, end, name, score, pval, strand`, where `pval` is the motif score expressed as −log10(p-value) × 100 (an integer value in this file). The file contains 770050 data rows and no header or track-declaration lines; every decompressed line in the supplied file conforms to this schema. A line that does not conform to the 7-field data-row schema (for example a UCSC `track` declaration, should one be present) is not a data record and must be ignored, as must any blank line.
3. `/inputs/ENCFF356LFX.bed.gz` — ENCODE blacklist regions, gzipped BED3 (`chrom, start, end`), no header, 910 rows.

All coordinates are 0-based, half-open `[start, end)` intervals in base pairs on GRCh38/hg38. Chromosomes are matched by exact name string (no aliasing or prefix normalization). Two intervals on the same chromosome overlap if they share at least one base (`start_A < end_B` and `start_B < end_A`); abutting intervals do not overlap.

## Entities, output grain and combination rules

- The output entities are **distinct peak intervals**, not peak records. The peaks file contains 40587 records over 40572 distinct `(chrom, start, end)` intervals; 15 intervals appear in two records each, with **different `fc` values**. Each distinct interval is analyzed and reported as one peak, annotated with the `fc` of the first record of that interval in the peaks file's row order (the file is sorted ascending by `fc`, so this is also the smaller of the two values).
- A peak interval can be overlapped by zero, one or many motif records (many is common); the assignment rule below selects a single motif or none.
- Peaks are neither merged nor re-clustered; each distinct interval is handled independently.

## Analysis specification

1. **Motif assignment per peak.** For each distinct peak interval P = (chrom, start, end), find all motif records whose interval overlaps P. The motif assigned to P is the overlapping motif with the largest `pval`; if several motifs tie for the largest `pval` (such ties do occur for some peaks in this dataset), assign the one that appears **earliest in the motif track file's row order**. A peak with no overlapping motif — or a peak none of whose overlapping motifs has a defined `pval` — is retained with blank motif fields. (Every `pval` in the supplied motif file is defined.)
2. **Blacklist filtering, performed after assignment.** Expand every blacklist interval by 1000 bp on each side and take the union of the expanded intervals (equivalently: first merge expanded intervals that overlap or abut one another). Remove from each peak the portions covered by (sharing at least one base with) the removed set, keeping the surviving sub-intervals with start/end coordinates trimmed to the retained portion. A peak entirely covered by expanded blacklist intervals contributes no rows. Motif assignment is performed on the original, untrimmed peak spans; the blacklist step only trims the reported peak coordinates, so a retained row's assigned motif need not overlap the trimmed sub-interval it is reported on.

## Required output

Write a single file `/outputs/ctcf_peaks_maxmotif_clean.csv`: UTF-8, comma-separated, exactly one header line followed by one data row per retained peak sub-interval, no index column, no additional files. Columns, in exactly this order and with exactly these names:

```
chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand
```

- `chrom`, `start`, `end` — the retained (possibly trimmed) peak sub-interval; integers.
- `fc` — the peak's fold-change value, per the entity rule above.
- `motif_chrom`, `motif_start`, `motif_end` — the assigned motif's interval; `motif_start` and `motif_end` are integers.
- `motif_pval` — the assigned motif's `pval` score (−log10 p × 100).
- `motif_strand` — the assigned motif's strand (`+` or `-`).
- Motif fields are blank for peaks with no assigned motif.
- A peak split into several retained pieces appears once per piece, each row carrying the same `fc` and motif annotation.

Row order is free and will not be evaluated. `fc` and `motif_pval` are decimal numbers; any unambiguous decimal representation of the value is acceptable (for example `450` or `450.0`). The analysis is fully deterministic; no randomness is involved.

## Environment and resources

Run offline. Limits: 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s wall-clock. Any toolchain is acceptable provided the output meets the specification above; for convenience a Python environment including bioframe 0.8.0 is available, but its use is not required.
