# Acceptance rules (addendum to the task specification)

## Output file and format

Write **exactly one** output file, `ctcf_peaks_maxmotif_clean.csv`. It must be the only content of your submission directory: no additional files, no index/sidecar files, no logs. (An empty `outputs/` subdirectory layout is tolerated: the file may sit alone either directly in the submission directory or as the sole entry of a subdirectory named exactly `outputs` or `output`.) The file is UTF-8, comma-separated, with exactly one header line, one data row per retained peak sub-interval, no index column, and no additional columns. Lines must end with a newline; blank lines anywhere in the file (including the last line) fail the format check. Valid delimiters are commas only, and no UTF-8 byte-order mark.

The header line must read exactly:

```
chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand
```

Each data row has exactly 9 comma-separated fields in that order. Quoting, such as `"chr1"`, is not required or checked; it is accepted only when it parses as unquoted content (a quoted field whose content is a plain value is still compared as that value). Tab-, semicolon- or space-delimited files fail, as do gzipped outputs (the file must be plain text).

## Field value rules

- `chrom`, `motif_chrom` — genome assembly contig name (e.g. `chr1`), matched by exact string. Blank or malformed values fail.
- `start`, `end`, `motif_start`, `motif_end` — plain non-negative base-pair integers, compared numerically and exactly. Leading `+`, leading zeros, non-integer renderings (`48309541.0`, `4.8e7`) and negative values all fail.
- `start < end` and `motif_start < motif_end` must hold in every row.
- `fc` — the peak's fold change, a finite decimal number. Renderings that parse to the same number are accepted (`5.208`, `5.20800`, `5.208e0`); blank, non-numeric, `NaN` or infinite values fail. This is a scalar annotation of the peak: all rows of one peak (including split sub-intervals) carry the same fc.
- `motif_pval` — −log10(p) × 100, a finite decimal number, admitted under the same rendering rule. Exact numeric equality is required; no tolerance is applied to an unanswered, rounded or wrong score.
- `motif_strand` — exactly `+` or `-`.
- **Blank motif fields are an answer, not missing data.** A peak with no assigned motif must have all five motif fields blank in every row it yields. A partially blank set (e.g. motif coordinates present but motif_pval blank) fails. Because blanks here denote a legitimate scientific outcome (`no motif overlaps this peak`), such rows are never counted as missing, dropped or invalid.
- Every row's `motif_chrom` equals its `chrom`.

## Row alignment, ordering and multiplicity

Rows are aligned to the reference by the stable identifier `(chrom, start, end)` of the retained peak sub-interval. **Row order is free and is not compared.** Rows are compared as a multiset (per-row duplicates count): every reference `(chrom, start, end)` row must appear with exactly the same multiplicity, and no additional row may appear. Duplicate identical rows are therefore distinguishable from a single row and fail. One row is emitted per retained peak sub-interval; a peak split into several pieces contributes one row per piece, each carrying the same `fc` and motif annotation, and a peak entirely removed by the expanded blacklist contributes no row. Row count alone is not sufficient: the grader compares the full row content, not just the number of rows, so a table with the correct number of rows but wrong intervals or annotations fails.

## What is compared scientifically

The submission is compared against the reference copy of this table, which was produced by the approved analysis (strongest-overlapping-motif assignment on the original peak spans, then ±1 kb expanded-blacklist trimming of the reported coordinates). The comparison is per row, after alignment by `(chrom, start, end)`:

1. the retained peak sub-intervals (which peaks survived, their trimmed coordinates, and how many rows each peak contributes);
2. the `fc` value on each row;
3. the five motif fields on each row — the presence/absence of an assignment, the assigned motif's `chrom`, `start`, `end`, `motif_pval` and `motif_strand`.

Each of these is a named check, so a submission that gets the intervals right but the motif assignment wrong (or the reverse) fails on the corresponding check. **Numeric fields (`fc`, `motif_pval`) are compared as exact parsed numbers with no tolerance**: a difference of any size, including 1e-12 relative, fails, because the analysis is fully deterministic and the analyzed quantities are exact decimal values of finite precision. Only the decimal *rendering* of an exactly equal number is normalized away (e.g. `450` vs `450.0`). A nonfinite or unparseable value fails the affected check rather than silently comparing equal.

The assigned motif is not required to overlap the reported, possibly trimmed sub-interval (assignment uses the original untrimmed peak span, as specified). The grader does not check scientific method, only the resulting assignment values.

## Input values are never inferred from output

The grader evaluates only the delivered table against the reference table; it does not re-run the analysis and does not read the raw inputs. Values in the output that would be inconsistent with the supplied inputs are not separately detected.

## Failure handling

A missing output file, unreadable file, malformed CSV, wrong header, wrong column count, blank lines, non-numeric or nonfinite numeric field, partially blank motif block, or a motif reported on a chromosome other than the peak's own chromosome fails the corresponding checks. All declared checks are always reported (a failure upstream of a check is reported as that check failing, not as a crash); the grader exits 0 with a written report in all cases, so a failed check means the submission was rejected, never that the verification crashed.
