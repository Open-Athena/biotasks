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

Your submission is graded **only** through the single required file `ctcf_peaks_maxmotif_clean.csv`, read from your output directory. Any other file you write is ignored. Grading compares the *parsed scientific content* of your table against the reference table — the result of the analysis rules in the task specification. No execution of your code takes place, so nothing about your implementation method, toolchain or intermediate files affects the outcome.

## Structural rules

1. The file must exist as a regular, non-empty file (an empty file, or a directory or special file in its place, fails). Its bytes must decode as UTF-8, with a single leading byte-order mark ignored; a NUL character anywhere in the text fails. **Reading limit: the file may be at most 64 MiB (67,108,864 bytes); a larger file fails the format check before it is parsed.** The decoded text is then parsed as comma-separated values under strict CSV rules, with the parser's field-size limit set to that same 64 MiB: quoting of fields is accepted and unwrapped, a record that does not parse (for example an unclosed quotation) fails the format check, and empty lines are ignored. The parse must yield exactly one header line followed by at least one data row.
2. The header line must contain exactly these nine names, in exactly this order: `chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand`. Names are matched literally — no renaming (`chrom_2`, `pval_2`, …), reordering, extra columns or missing columns. Quoting of fields is accepted and ignored.
3. Every data row must have exactly nine comma-separated fields. Empty lines are ignored; any row with a different field count fails the file-format check.

**Gating.** These two structural checks come first. If `csv_format` fails, `value_domains` and the three content checks are reported as not evaluated; if `value_domains` fails, the content checks are reported as not evaluated. A malformed submission never reaches a content check.

## Value rules

4. `chrom` and `motif_chrom` are matched as exact strings (no case folding and no alias/prefix normalization); they must be non-empty and carry no leading or trailing whitespace.
5. `start`, `end`, `motif_start`, `motif_end` must denote non-negative integers below 2^62, with `start < end` and `motif_start < motif_end`. Any decimal spelling that denotes that integer is accepted (for example `450`, `450.0` or `4.5e2`); comparisons use the integer value.
6. `fc` and `motif_pval` must be plain finite decimal numbers (optional sign, digits, decimal point, optionally a decimal exponent such as `e2` or `E-3`). `NaN`, `Inf`, empty strings and whitespace-padded values are rejected.
7. `motif_strand` must be exactly `+` or `-`.
8. For each row, the five motif fields (`motif_chrom`, `motif_start`, `motif_end`, `motif_pval`, `motif_strand`) must be **all blank or all present**. Blanks mean "no assigned motif"; a partly filled set is an error. Zero as `fc` or as `motif_pval`, if produced by the analysis, is meaningful and must be written, not left blank.

## Row-level comparison rules

9. **Row order is free**: rows are compared as an unordered multiset, so you may present rows in any order; row order is not used to identify anything, and sorting is not required. Original row order was never part of the analysis specification.
10. **Multiplicity counts**: two rows carrying the same values are two distinct items. Omitting a required row, adding an extra row, or duplicating a row all fail. A peak that survives as multiple trimmed pieces is represented by multiple rows, each carrying the same `fc` and motif annotation, and all must be present.
11. `fc` and `motif_pval` are compared **by numeric value, exactly, with no tolerance**: `450`, `450.0`, `4.5e2` and `0450` are all the same number, and any other unambiguous decimal spelling of the value is likewise accepted. A text denoting any different number — a value rounded to fewer digits, perturbed in the last decimal place, or off by one unit — is a mismatch and fails. There is no epsilon and no rounding on either side; exact numeric equality is the whole rule, and no safety margin sits inside a tolerance, because there is no tolerance. The graded numbers are pass-through values selected unchanged from the supplied input files (whose `fc` fields are decimal literals written with five digits after the decimal point, and whose motif `pval` values are integers), so exact comparison never penalizes a correct value for its decimal spelling, and a numerically different value means a different record was selected rather than rounding of the correct value in a compliant pipeline.
12. All nine fields are compared together in one row identity, so a correct peak interval paired with a wrong `fc`, or a correct motif paired with a wrong peak, fails.

## What the checks are

- `csv_format` — the file is present as a regular non-empty file, decodes as UTF-8 with at most one leading byte-order mark, contains no NUL byte, is at most 64 MiB long, parses under strict comma-separated rules, has one header line with the nine required names in order, holds at least one data row, and every data row has exactly nine fields.
- `value_domains` — every data row obeys rules 4–8.
- `peak_rows_match` — the multiset of `(chrom, start, end, fc)` equals the reference multiset, with `fc` compared by numeric value. The reference multiset is the outcome of the published entity and trimming rules: every **distinct** peak interval of the peaks file (40572 distinct intervals, not 40587 records), each carrying the **fold change of its first record** in file order, with peak material inside the union of the ±1 kb expanded blacklist regions removed, so that a wholly covered peak contributes no row and a partly covered peak is reported as its surviving sub-intervals. Because `fc` is part of the compared key, a peak reported with any fold change other than its first record's — including a doubly recorded interval reported with its second record's value — yields a missing or extra item and fails this check.
- `motif_annotation_match` — on both sides rows are grouped by peak sub-interval `(chrom, start, end)` and, per sub-interval, the multiset of motif annotations `(motif_chrom, motif_start, motif_end, motif_pval, motif_strand)` must be identical to the reference's, blanks included. The comparison fails if a sub-interval retained by the reference is missing from your table entirely; if your table reports a sub-interval the reference does not retain; or if a shared sub-interval's annotation multiset differs — a different motif, a different `motif_pval` or `motif_strand`, an annotation filled in where the reference is blank, blanks where the reference has an annotation, or a repeat repeated a different number of times. The reference annotations embody the analysis specification's selection: the overlapping motif with the largest `pval`, ties broken by the **earliest** motif row in the motif-track file's order, and blank motif fields when no motif overlaps. A row's assigned motif need not overlap the trimmed sub-interval it is reported on, since assignment precedes trimming: do not re-assign or clear motifs after trimming.
- `full_table_match` — the multiset of complete nine-field rows equals the reference multiset: no row is missing, added or altered. This check is **computed directly on complete rows**, not derived from the other two content checks; the grouped comparisons do not by themselves bind a particular `fc` to a particular motif annotation across rows that share a peak sub-interval, so it is this direct full-row comparison that enforces the peak interval, fold change and motif annotation of a single row belonging together.

Passing all five checks is the sole acceptance criterion; `passed` is the conjunction of the five check booleans.

## Controls

The grader reads only your one required output file (and its own reference copy), executes none of your code, and consults none of your inputs, intermediates or other file names. Its comparisons contain no randomness and no clock- or environment-dependent branching, so the same submitted file always yields the same report. Missing, empty or malformed files — including an empty submission directory — produce a completed report with `passed: false` naming all five checks, never a crash; every declared check is reported for every submission, malformed ones included. The same reading rules are applied to the grader's own reference copy, and if that copy cannot be read or does not meet them, the grader reports an internal grading problem and evaluates nothing rather than passing anything.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
