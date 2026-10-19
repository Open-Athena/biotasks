# Acceptance rules (addendum to the task specification)

## Output file and format

Write **exactly one** output file, `ctcf_peaks_maxmotif_clean.csv`, and nothing else. It must be the only content of your submission directory (a tolerated variant: the file sitting alone inside an otherwise-empty subdirectory named exactly `outputs` or `output`). No logs, indices or sidecar files. The file is UTF-8, comma-separated, with exactly one header line and one data row per retained peak sub-interval, no index column and no additional columns. Lines must end with a newline; blank lines anywhere (including the last line) fail. A final newline is expected; CRLF line endings are read as newlines. A gzipped output fails.

The header line must read exactly:

```
chrom,start,end,fc,motif_chrom,motif_start,motif_end,motif_pval,motif_strand
```

Each data row has exactly nine comma-separated fields in that order. Tab-, semicolon- or space-delimited files fail, as does a byte-order mark or any non-UTF-8 byte sequence.

## Field value rules

- `chrom`, `motif_chrom` — contig name (e.g. `chr1`), matched by exact string. Blank or malformed values fail.
- `start`, `end`, `motif_start`, `motif_end` — plain non-negative base-pair integers, compared numerically and exactly. Leading `+`, leading zeros, non-integer renderings (`48309541.0`, `4.8e7`) and negative values all fail.
- `start < end` and `motif_start < motif_end` must hold in every row.
- `fc` — the peak's fold change, a finite decimal number. Renderings that parse to the same number are accepted (`5.208`, `5.20800`, `5.208e0`); blank, non-numeric, `NaN` or infinite values fail. All rows belonging to one peak (including split sub-intervals) carry that peak's fold change.
- `motif_pval` — −log10(p) × 100, a finite decimal number, admitted under the same rendering rule.
- `motif_strand` — exactly `+` or `-`.
- **A blank motif block is an answer, not missing data.** A peak with no assigned motif must have all five motif fields blank. A partially blank block (e.g. motif coordinates present but motif_pval blank) fails: it is neither a valid assignment nor a valid "no motif" answer. Such rows are never treated as missing or dropped values, and `NaN`/infinite values in numeric fields always fail rather than comparing equal.
- Every row's `motif_chrom` equals its `chrom`.

## Row alignment, ordering and multiplicity

Rows are aligned to the reference by the stable identifier `(chrom, start, end)` of the retained peak sub-interval. **Row order is free and is not compared.**

- The set of distinct `(chrom, start, end)` intervals in the submission must equal the reference set exactly: no reference interval may be absent, and no interval outside the reference may appear. One row is emitted per retained peak sub-interval; a peak split into several pieces contributes one row per piece with the same annotations; a peak entirely removed by the expanded blacklist contributes no row. Peaks that appear more than once in the peak file may be reported in one row or in several rows for the same interval (see fold-change rule below).
- No row may be an exact duplicate of another row (identical in all nine fields). Every distinct row must be reported once.

## What is compared scientifically

The submission is compared against the reference copy of this table, which was produced by the approved analysis: strongest-overlapping-motif assignment on the original, untrimmed peak spans, followed by ±1 kb expanded-blacklist trimming of the reported coordinates. Comparison is per interval, after alignment by `(chrom, start, end)`. Three quantities are checked as separate named checks, so a submission that gets the intervals right but the annotation wrong (or the reverse) fails on the corresponding check:

1. **Retained peak sub-intervals** — which peaks survived where, i.e. the trimmed coordinates (set equality as above).
2. **Peak fold change** — for every reference `(interval, fc)` pair, at least one row of the submission for that interval must report that fc. Comparison is by the exact parsed number with **no tolerance**: any difference, including one unit in the last digit, fails. Only the decimal rendering of an equal number is normalized away. Where an interval belongs to more than one peak record, rows reporting the additional records' fold changes are not penalized by this check, but the reference value must be present and every reported value must be attached to a reference interval.
3. **Motif assignment** — for every reference interval, all submission rows for that interval must carry the same motif block, equal to the reference assignment: either blank in all five fields, or the reference `motif_chrom`, `motif_start`, `motif_end`, `motif_strand` exactly and `motif_pval` equal as the exact parsed number. Turning a blank block into a motif, dropping a motif, swapping motifs between peaks, changing the strand, or changing the score by any amount fails.

The assigned motif is not required to overlap the reported, possibly trimmed sub-interval (assignment uses the original untrimmed peak span, as specified), and this overlap is not checked. The grader does not re-run the analysis and does not read the raw inputs; it evaluates the delivered table only.

## Failure handling

A missing output file, unreadable file, malformed CSV, wrong header, wrong column count, blank lines, non-numeric or nonfinite numeric field, partially blank motif block, or a motif on a chromosome other than the peak's own fails the corresponding checks. All declared checks are reported in every case; a failure upstream of a check makes that check fail (it is reported as not evaluated), never a crash. The grader exits 0 with a written report for both correct and incorrect submissions.
