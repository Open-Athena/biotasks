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

## Acceptance rules

# Acceptance rules (addendum to the task specification)

## What is graded
Your submission is graded **only** through the single required file `ctcf_peaks_maxmotif_clean.csv`, read from your output directory. Any other file you write is ignored. Grading compares the *parsed scientific content* of your table against the reference result computed under the published analysis rules; no execution of your code takes place, so nothing about your implementation method, toolchain, or intermediate files affects the outcome.

## Structural rules
1. The file must exist, be non-empty, and decode as UTF-8 (a single leading byte-order mark is ignored). A comma-separated parse must yield exactly one header line followed by at least one data row.
2. The header line must contain exactly these nine names, in exactly this order: `chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand`. Names are matched literally — no renaming (`chrom_2`, `pval_2`, …), reordering, extra columns or missing columns. Quoting of fields is accepted and ignored.
3. Every data row must have exactly nine comma-separated fields. Empty lines are ignored; any row with a different field count fails the file-format check.

## Value rules
4. `chrom` and `motif_chrom` are matched as exact strings (no case folding and no alias/prefix normalization); they must be non-empty and carry no leading/trailing whitespace.
5. `start`, `end`, `motif_start`, `motif_end` must denote non-negative integers below 2^62, with `start < end` and `motif_start < motif_end`.
6. `fc` and `motif_pval` must be plain finite decimal numbers (optional sign, digits, decimal point, optionally a decimal exponent such as `e2` or `E-3`). `NaN`, `Inf`, empty strings and whitespace-padded values are rejected.
7. `motif_strand` must be exactly `+` or `-`.
8. For each row, the five motif fields (`motif_chrom`, `motif_start`, `motif_end`, `motif_pval`, `motif_strand`) must be **all blank or all present**. Blanks mean "no assigned motif"; a partly filled set is an error. Zero as `fc` or as `motif_pval`, if produced by the analysis, is meaningful and must be written, not left blank.

## Row-level comparison rules
9. **Row order is free**: rows are compared as an unordered multiset, so you may present rows in any order. Row order is not used to identify anything, and sorting is not required. Original row order is irrelevant, since row order was never a scientific part of the analysis specification.
10. **Multiplicity counts**: two rows carrying the same values are two distinct items. Omitting a required row, adding an extra row, or duplicating a row all fail. In particular, a peak that survives as multiple trimmed pieces is represented by multiple rows, each carrying the same `fc` and motif annotation, and all must be present.
11. `fc` and `motif_pval` are compared **by numeric value, exactly, with no tolerance**: `450`, `450.0`, `4.5e2` and `0450` are all the same number. A text denoting any different number — a value rounded to fewer digits, perturbed in the last decimal place, or off by one unit — is a mismatch and fails. There is no epsilon, and no rounding is applied to either side; exactness follows from the released input values being decimal literals of at most six digits (`fc` always has five decimal places; `motif_pval` is always an integer), so any disagreement reflects a wrong input value, not formatting noise.
12. All nine fields are compared together in one row identity, so a correct peak interval paired with a wrong `fc`, or a correct motif paired with a wrong peak, fails.

## What the checks mean
The graded-table checks are, in order:
- `csv_format` — the file exists, parses as UTF-8 comma-separated text, has the one required header line with the nine required names in order, at least one data row, and every data row has exactly nine fields.
- `value_domains` — every data row obeys rules 4–8.
- `peak_rows_match` — the multiset of `(chrom, start, end, fc)` equals the reference multiset. This verifies that you analyzed **distinct peak intervals** (40572 of them, not 40587 records), assigned each the **fold change of the first record** for that interval in the peaks-file row order, removed peak material within the ±1 kb expanded blacklist (so all trimmed pieces are present and wholly covered peaks are absent), and reported the surviving sub-intervals as integers. Because `fc` also participates in row identity, this is the check that catches a duplicated interval reported with the other record's fold change.
- `motif_annotation_match` — for each peak sub-interval (`chrom`, `start`, `end`) present in your table, the multiset of motif annotations (`motif_chrom`, `motif_start`, `motif_end`, `motif_pval`, `motif_strand`) matches the reference for that same sub-interval, including the case where those five fields are blank on both sides. This verifies the strongest-motif selection (largest `pval` wins; ties go to the **earliest** motif row in the motif-track file order), the `pval` value itself, the strand, and that unassigned peaks stay blank. Note that a row's assigned motif **need not overlap the trimmed sub-interval** it is reported on, since assignment precedes trimming: do not re-assign or clear motifs after trimming.
- `full_table_match` — the multiset of complete nine-field rows equals the reference multiset with no missing, extra or altered row. This is a direct function of the previous two content checks, computed independently, and verifies the pairing between peak interval, fold change and motif annotation within each row.

Passing all five checks is the sole acceptance criterion; `passed` is the conjunction of the five check booleans.

## Controls
The grader is deterministic and has no time or randomness dependence; it always finishes within the allotted verifier budget. Missing or malformed files (including an empty submission directory) produce a completed report with `passed: false`, never a crash. Every declared check is reported for every submission, including malformed ones. The grader does not execute your code and does not consult your inputs, intermediate files or file names other than the one required output.
