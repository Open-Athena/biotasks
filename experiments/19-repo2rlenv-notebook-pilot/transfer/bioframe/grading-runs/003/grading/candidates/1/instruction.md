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
