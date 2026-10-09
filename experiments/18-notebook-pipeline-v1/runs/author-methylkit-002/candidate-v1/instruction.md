# Compare CpG methylation between treatment and control samples

## Background

You have four bisulfite sequencing CpG methylation call tables from an experiment
comparing two treatment samples (`test1`, `test2`) with two control samples
(`ctrl1`, `ctrl2`), all mapped to the hg18 assembly. Each table is
tab-separated with a header line and one row per measured CpG on one strand,
with columns:

- `chrBase` — label of the form `chr.start`
- `chr` — chromosome (all rows are `chr21`)
- `base` — genomic position
- `strand` — `F` or `R`
- `coverage` — number of reads covering the site
- `freqC` — percent of methylated cytosines, rounded to 2 decimals
- `freqT` — percent of unmethylated cytosines, rounded to 2 decimals

The files are at `/app/inputs/test1.myCpG.txt`, `/app/inputs/test2.myCpG.txt`,
`/app/inputs/control1.myCpG.txt` and `/app/inputs/control2.myCpG.txt`. Their
sample identities are test1, test2, ctrl1 and ctrl2 respectively. The treatment
group is {test1, test2}; the control group is {ctrl1, ctrl2}.

## Objective

For every CpG locus that is confidently measured and shared by all four samples,
compute the percent methylation of each sample from integer read counts, and
quantify how much the treatment group differs from the control group at that
locus.

## Method

1. **Coverage filter, applied per sample.** Keep only loci with
   `coverage >= 10` reads. Then discard loci whose coverage is greater than or
   equal to the sample's 99th percentile of coverage — that is, keep only
   loci with coverage strictly below the percentile value. The percentile is
   computed over the coverage values of that sample's loci that satisfy the
   low-coverage bound, using linear interpolation between order statistics
   (the type-7 convention of R's `quantile`). The lower bound is inclusive
   (coverage exactly 10 is kept); the upper bound is exclusive (a locus with
   coverage exactly equal to the percentile value is discarded).
2. **Join.** Retain only loci present in all four samples after filtering,
   keyed by (`chr`, `base`, `strand`). Do not merge opposite strands
   (no destranding): a CpG measured on the F strand and the same position
   measured on the R strand are different rows.
3. **Percent methylation from counts.** For each sample and locus, recover the
   integer methylated read count as the nearest integer to
   `coverage * freqC / 100`, resolving exact `.5` ties to the even integer
   (banker's rounding). Define percent methylation as
   `100 * numCs / coverage`.
4. **Group aggregation.** Per locus compute the unweighted mean of the two
   treatment samples' percent methylation (`test_mean_pct`), the unweighted
   mean of the two control samples' percent methylation (`ctrl_mean_pct`), and
   the difference `diff_pct = test_mean_pct - ctrl_mean_pct`.

Do not perform differential significance testing; the required comparison is
the explicit group aggregation above.

## Output contract

Write a tab-separated file at `/output/group_methylation.tsv` with exactly this
header:

```
chr	base	strand	pct_test1	pct_test2	pct_ctrl1	pct_ctrl2	test_mean_pct	ctrl_mean_pct	diff_pct
```

One row per retained locus. `chr` and `strand` are strings, `base` is an
integer, and the seven numeric columns are decimal percentages. Rows may be in
any order but each (`chr`, `base`, `strand`) key must appear exactly once. The
four `pct_*` columns are the per-sample values from step 3, and the group
columns follow step 4.

Internet access is disabled. Inspect the environment for available software;
required dependencies are installed.
