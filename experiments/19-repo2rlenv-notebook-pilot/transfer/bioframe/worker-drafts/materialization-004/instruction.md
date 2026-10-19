# Task: assign the strongest CTCF motif to each CTCF ChIP-seq peak, then blacklist-filter the result

## Objective

For the CTCF ChIP-seq peak set from HFF cells (ENCODE, assembly GRCh38), assign to every peak the strongest CTCF motif from the JASPAR MA0139.1 track that overlaps it, and then conservatively remove any peak material lying within ±1 kb of ENCODE blacklisted genomic regions. The deliverable is a table of the retained peak intervals, each annotated with the peak's fold change and its assigned motif.

## Supplied inputs (read-only; no network access)

1. `/inputs/ENCFF401MQL.bed.gz` — CTCF ChIP-seq peaks (HFF), gzipped narrowPeak, no header. Columns in order: `chrom, start, end, name, score, strand, fc, -log10p, -log10q, relSummit`. Only `chrom`, `start`, `end` and `fc` are used.
2. `/inputs/MA0139.1.tsv.gz` — CTCF motif occurrences (JASPAR profile MA0139.1, hg38 UCSC track), gzipped, tab-separated. The file begins with a single UCSC track declaration line (not a data row); data rows follow with columns in order: `chrom, start, end, name, score, pval, strand`, where `pval` is the motif score expressed as −log10(p-value) × 100.
3. `/inputs/ENCFF356LFX.bed.gz` — ENCODE blacklist regions, gzipped BED3 (`chrom, start, end`), no header.

All coordinates are 0-based, half-open `[start, end)` intervals in base pairs on GRCh38/hg38. Chromosomes are matched by exact name string. Two intervals on the same chromosome overlap if they share at least one base (`start_A < end_B` and `start_B < end_A`); abutting intervals do not overlap.

## Analysis specification

1. **Motif assignment per peak.** Consider each distinct peak interval P = (chrom, start, end) in the peak set. Find all motif records whose interval overlaps P. The motif assigned to P is the overlapping motif with the largest `pval`; if several motifs tie for the largest `pval`, assign the one that appears earliest in the supplied motif track file's row order. A peak with no overlapping motif — or a peak none of whose overlapping motifs has a defined `pval` — is retained with blank motif fields.
2. **Blacklist filtering, performed after assignment.** Expand every blacklist interval by 1000 bp on each side. Remove from each peak the portions covered by (sharing at least one base with) any expanded blacklist interval, keeping the surviving sub-intervals with start/end coordinates trimmed to the retained portion. A peak entirely covered by expanded blacklist intervals contributes no rows. Motif assignment is performed on the original, untrimmed peak spans; the blacklist step only trims the reported peak coordinates.

## Input parsing and value conventions

- The narrowPeak `fc` column (7th column) is a decimal number.
- The motif track's first physical line is a UCSC track declaration (for example `track name=... `); skip it before reading data rows. Every data row has exactly the 7 tab-separated fields listed above.
- Any blank line in a gzip input file is ignored.

## Required output

Write a single file `outputs/ctcf_peaks_maxmotif_clean.csv`: UTF-8, comma-separated, exactly one header line followed by one data row per retained peak sub-interval, no index column, no additional files. Columns, in exactly this order and with exactly these names:

```
chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand
```

- `chrom`, `start`, `end` — the retained (possibly trimmed) peak sub-interval; integers.
- `fc` — the peak's fold-change value from the peaks file.
- `motif_chrom`, `motif_start`, `motif_end` — the assigned motif's interval.
- `motif_pval` — the assigned motif's `pval` score (−log10 p × 100).
- `motif_strand` — the assigned motif's strand (`+` or `-`).
- Motif fields are blank for peaks with no assigned motif.
- A peak split into several retained pieces appears once per piece, each row carrying the same `fc` and motif annotation.

Row order is free and will not be evaluated. The analysis is fully deterministic; no randomness is involved.

## Environment and resources

Run offline. Limits: 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s wall-clock. Any toolchain is acceptable provided the output meets the specification above; for convenience a Python environment including bioframe 0.8.0 is available, but its use is not required.

