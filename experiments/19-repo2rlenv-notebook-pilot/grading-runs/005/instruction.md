# Marker-gene (differential-expression) analysis for a fixed clustering of pooled bone-marrow single-cell data

## Scientific context

The data are two 10x Chromium Gene Expression samples — `s1d1` and `s1d3` — of bone-marrow mononuclear cells from healthy human donors (NeurIPS 2021 Multimodal Single-Cell Integration reference dataset; Luecken et al., 2021), each distributed as a filtered feature–barcode matrix of raw integer UMI counts. In the source analysis, the two samples were pooled, permissively quality-filtered, normalized by median count depth with a natural log1p transform, and clustered with Leiden (resolution 0.50). The terminal interpreted result of that analysis is the per-cluster marker-gene table: for each cluster, every gene ranked by a two-sided Wilcoxon rank-sum test of the cluster's cells against all other cells, with per-gene score, uncorrected and Benjamini–Hochberg-adjusted p-values, and a log2 expression fold change.

Cluster discovery, dimensionality reduction, embeddings, QC diagnostics and doublet detection are **not** part of this task. The per-cell cluster assignments of the recorded reference clustering of this dataset are **supplied as a fixed grouping input** (one executed computational clustering; not a validated biological annotation). Your task is the downstream marker analysis conditional on that grouping.

## Inputs

The four files below are provided directly in the run's input directory.

| file | content |
|---|---|
| `s1d1_filtered_feature_bc_matrix.h5` | original 10x filtered feature–barcode matrix (raw UMI counts), sample `s1d1` (md5 `a99285913ea3f3d22600d3d2f8a88e34`) |
| `s1d3_filtered_feature_bc_matrix.h5` | original 10x filtered feature–barcode matrix (raw UMI counts), sample `s1d3` (md5 `825f7f7578e3dc0b8955f5a97a402338`) |
| `cell_groups.csv` | fixed per-cell cluster assignments |
| `gene_identities.csv` | gene identity map for both samples |

**`cell_groups.csv`** — one row per analysis cell, columns:

- `sample` — `s1d1` or `s1d3`;
- `barcode` — the cell barcode exactly as stored in that sample's 10x file;
- `cluster` — the group label (an integer-like string); use it verbatim as the group identifier.

The pair (`sample`, `barcode`) is unique (the same barcode string can occur in both samples). The table covers exactly the analysis population defined below, has no missing values, and every (`sample`, `barcode`) it lists is present in that sample's h5 file.

**`gene_identities.csv`** — one row per gene-expression feature that the source analysis included from that sample, columns:

- `sample` — `s1d1` or `s1d3`;
- `h5_row` — zero-based index of the feature in that sample's stored feature dimension (reading that row of the stored matrix yields the feature's counts for all barcodes);
- `gene_id` — the gene identifier used throughout this analysis; unique within a sample;
- `gene_symbol`, `ensembl_id` — the symbol and id stored in the file for that feature (provenance only; do not use them as join keys).

The map fixes which stored features are in the analysis, the identifier of each gene, and the correspondence between identifiers and stored matrix rows; you do not need to reproduce any library naming, feature-type filtering or deduplication convention. The gene identifier in your output is `gene_id`. A gene symbol may occur more than once within a sample; the map keeps such features as distinct genes under distinct `gene_id`s — do not merge or sum them.

A pooled analysis gene is a `gene_id` that appears in the map of **both** samples; that intersection is the pooled gene universe.

## Analysis population, identifiers and normalization

The following conventions of the source analysis define the requested quantity.

1. For each sample, use exactly the features listed in `gene_identities.csv`, with raw integer UMI counts; cells are the file's barcodes.
2. The analysis population is the set of rows of `cell_groups.csv`; attach each cell's cluster label through (`sample`, `barcode`).
3. **Cell filter (pooled, not per sample)**: for each cell, count the genes with a strictly positive count in the pooled matrix, where the pooled matrix is built over the intersection gene universe. Keep cells with at least 100 such detected genes. The retained set must equal the rows of `cell_groups.csv` exactly; if your filter does not reproduce it, your preprocessing deviates from the defined population and the deliverable is invalid.
4. **Gene filter (pooled)**: on the cell-filtered pooled matrix, keep genes with a strictly positive count in at least 3 cells. This set is the tested gene universe; it is identical for every cluster, and no other feature selection (e.g. variability-based) is applied.
5. **Normalization**: for each retained cell *i*, let `total_i` be the sum of its counts over the tested gene universe, and let `T` be the median of `total_i` over all retained cells (standard median: the mean of the two middle order statistics if the number of cells is even). The normalized value is `x_ij = ln(1 + count_ij × T / total_i)` (natural log). This is one pooled median-of-totals scaling for the whole population — not per-sample, and not a fixed count-per-10k/million target.
6. Nothing else alters the expression values before the marker test (the source's doublet scoring, feature-selection and dimensionality-reduction steps are excluded from this task and do not feed the test).

## Per-cluster marker test

Perform, for every supplied cluster label `c` (in-group = cells assigned to `c`; "rest" = all other analysis cells, regardless of their cluster or sample), a gene-by-gene comparison on the normalized values:

- **Score** — two-sided Wilcoxon rank-sum statistic, per gene: rank the `N` analysis cells by the gene's normalized value using **average ranks** (ties receive the mean of the ranks they span); let `W_c` be the sum of the in-group ranks and `n_c` the cluster size. The score is

  `z = ( W_c − n_c (N + 1) / 2 ) / sqrt( n_c (N − n_c) (N + 1) / 12 )`.

  This variance is the source convention: average ranks, **no** tie-variance correction, **no** continuity correction. If the denominator is zero, define `z = 0`. You may compute the statistic by any mathematically equivalent route (e.g. via Mann–Whitney U statistics); the delivered quantity is this `z`.
- **Uncorrected p-value** — the two-sided standard-normal tail probability `p = 2 · (1 − Φ(|z|))`. Evaluate the tail numerically in a stable way (directly from a complementary-CDF or error-function routine); computing it as `1 − Φ(...)` loses small probabilities long before true underflow. Values below the smallest positive double may be reported as 0; otherwise report the probability itself.
- **Adjusted p-value** — Benjamini–Hochberg within each cluster across **all** tested genes (the entire universe of step 4, never a reported subset): for the within-cluster sorted p-values `p_(1) ≤ … ≤ p_(m)`, the adjusted value is `p_adj_(i) = min(1, min_{j ≥ i} (m / j) × p_(j))`.
- **Effect size** — with `μ_c` and `μ_rest` the arithmetic means of the normalized values over the cluster's and the rest cells,

  `log2fc = log2( ((e^(μ_c) − 1) + 1e-9) / ((e^(μ_rest) − 1) + 1e-9) )`

  (natural base `e`; the `1e-9` stabilization constants are part of the source definition). Positive values mean higher expression in the cluster.

## Required output

`cluster_marker_genes.csv` — written directly under the run's output directory, as a plain CSV with header exactly:

`cluster,rank,gene,score,pval,pval_adj,log2fc`

- One row for **every** pair of supplied cluster label and tested gene (the complete cross product; no subsetting, cutoff or top-k). Each (`cluster`, `gene`) pair appears exactly once, and the number of rows is the same for every cluster.
- `cluster` — supplied label, verbatim. `rank` — the gene's position within its cluster when that cluster's genes are ordered by **descending** score (rank 1 = highest score). `gene` — `gene_id`. `score` — the `z` defined above. `pval`, `pval_adj`, `log2fc` — as defined above.
- Rows sorted by ascending numeric cluster label, then ascending rank. Break exact score ties in any deterministic order.
- All values present and finite (no blanks, NaN or inf). Underflowed p-values reported as `0`. Non-zero numeric values reported with at least 6 significant digits.
- Use one cluster labeling consistently throughout the file.

## Resources, environment and determinism

- 4 CPU cores, 8 GiB RAM, 10 GiB disk; 600 s wall-clock limit; no network access.
- The requested computation is deterministic; no random seeds are involved. If you use any randomized component, fix it.
- Software choice is open. A prebuilt offline Python environment containing the scanpy/anndata/h5py/pandas/scipy stack is available for convenience, but any implementation meeting the definitions above is acceptable. Applied to data prepared exactly as specified, with the supplied grouping, a standard `scanpy.tl.rank_genes_groups(..., method="wilcoxon")` call with default options computes the defined test; alternatively implement the statistics directly. (Note: other rank-sum implementations may default to tie-corrected or continuity-corrected variants; the defined statistic uses neither.)

## Provenance and license

- Expression data: figshare doi:10.6084/m9.figshare.22716739.v1 (NeurIPS 2021 benchmark dataset, CC BY 4.0). Source analysis: the scanpy "Preprocessing and clustering" tutorial (BSD-3-Clause), revision `8c1463d`.
- `cell_groups.csv` and `gene_identities.csv` are derived from the recorded reference run of that analysis and from the stored h5 metadata; they carry identity and grouping information only and contain no differential-expression results. The supplied grouping fixes the populations being compared; it is not asserted to be biological ground truth.

## Acceptance rules

## Acceptance rules for `cluster_marker_genes.csv` (addendum)

Your output is compared against a recorded reference table for the same supplied grouping, on **parsed scientific content**, never on file bytes, row text or the software that produced it. The reference is read dynamically at grading time; its cluster labels, gene identifiers and per-cluster gene counts are taken from the reference file itself, never from any fixed constant. Comparisons are keyed by the stable pair (`cluster`, `gene`) — never by row position. Each rule below names the check that enforces it.

### Required file and format

1. `cluster_marker_genes.csv` must exist directly under your output directory, as a plain UTF-8 CSV (no byte-order mark) whose first line is exactly `cluster,rank,gene,score,pval,pval_adj,log2fc` (same seven columns, same order). Every data row must carry exactly seven fields with no blank (empty or whitespace-only) field anywhere. A file that is missing, unreadable, has a different header, ragged rows, or blank fields fails all checks — it does not count as a run. *(check `file_present_parseable`)*
2. Every field of `score`, `pval`, `pval_adj`, `log2fc` must parse as a finite decimal number in plain or scientific notation (either case of `e`). `NaN`, `inf`, `-inf`, empty or otherwise non-numeric text fails; numbers overflowing the double range fail as non-finite. *(check `numeric_finiteness`)*
3. `pval` and `pval_adj` must lie in `[0, 1]`: they are two-sided tail probabilities and Benjamini–Hochberg adjusted values. *(check `numeric_finiteness`)*
4. `cluster` must be the supplied label written verbatim and `gene` the `gene_id` of `gene_identities.csv`; both are compared as exact strings after CSV unquoting — surrounding whitespace inside these identifier fields is not equivalent, and one identifier is never accepted in place of another. *(check `row_key_coverage`)*
5. `rank` must be a positive integer without decimals or exponent; a leading `+` sign or leading zeros are accepted notation for the same integer. *(check `row_ordering`)*

Writing a value with coarse rounding (for example two significant digits) is not checked by counting digits; it is rejected by the numeric comparisons of rules 10–14, which require far more precision than such rounding retains. The "at least 6 significant digits" requirement of the task is therefore enforced indirectly through those comparisons.

### Completeness and key alignment

6. The file must contain exactly one row for **every** `(cluster, gene)` pair present in the reference cross product — the complete cluster × tested-gene product and nothing more. Missing pairs, extra pairs, unknown cluster labels, unknown gene identifiers, or duplicated `(cluster, gene)` pairs fail. Per construction the tested gene set is identical for every cluster, so every cluster must carry the same number of rows as the reference's per-cluster row count. *(check `row_key_coverage`)*

### Ordering and rank

7. Rows must be physically sorted by ascending **numeric** cluster label, then ascending `rank` (e.g. `..., 9, 10, 11, ...`, not lexicographic `1, 10, 11, 2, ...`). *(check `row_ordering`)*
8. Within each cluster, `rank` must be exactly the consecutive integers `1..G`, where `G` is that cluster's number of tested genes; each rank value appears once per cluster. *(check `row_ordering`)*
9. **Ranking consistency.** Your within-cluster ranking must be a valid descending-score ordering, both against your own reported `score` values and against the reference's scores for those same genes: when your rows are taken in your reported rank order, neither score column may increase from one rank to the next by more than the score tolerance (2 × 10⁻⁴, rule 10). Exact score ties may be broken in any deterministic order, and near-tied genes (scores within the tolerance) may legitimately appear in either order; this tolerance-banded condition is what is enforced, so a different but equally valid tie break is accepted. A rank column that is not a valid positive integer, or invalid numeric values, make this check fail rather than silently pass. *(check `rank_consistency`)*

### Numerical agreement (per `(cluster, gene)` pair)

10. **`score`** — absolute tolerance **2 × 10⁻⁴**. Basis: the recorded reference statistics were produced by a pipeline whose normalized expression values pass through single-precision storage, which resolves cell-level value ties slightly differently from a full double-precision evaluation of the stated definitions; each such re-tied comparison moves the rank sum `W` by a fraction of a rank unit, which rescales to roughly this magnitude in `z`. The tolerance is set several times larger than that residual while real methodological errors (tie-variance- or continuity-corrected variance, per-cluster instead of pooled normalization, wrong reference group, shuffled cells) move `z` by orders of magnitude more and are rejected — including any single pair that exceeds the tolerance. *(check `score_agreement`)*
11. **`pval`** — relative tolerance **1 × 10⁻²** (fail when |a−b| > 0.01 · min(|a|, |b|)). Basis: the two-sided normal tail `p = 2·(1−Φ(|z|))` has relative sensitivity ≈ |z| per unit of z, and |z| reaches several tens on this data, so the z-scale residual of rule 10 induces about a percent-level relative change in the tail at worst. Any genuine tail error (one-sided tail, floored or truncated evaluation) is far outside this band and is rejected. *(check `pvalue_agreement`)*
12. **`pval` underflow equivalence — intentional equivalence zone.** A reported `0` and any value **≤ 1 × 10⁻³⁰³** are treated as equivalent. This is an intentional widening of "values below the smallest positive double may be reported as 0", adopted because the recorded reference itself reports `0` over a range of |z| where a stable double-precision complementary-CDF evaluation still retains a small positive (subnormal) value, while its smallest retained nonzero values are themselves subnormal; Benjamini–Hochberg scaling by m/j keeps adjusted values arising from such tails inside the same zone. Above that zone a reported `0` against a positive reference value is a failure, not an equivalence: a faithful evaluation cannot underflow there, and rounding a well-representable non-zero probability away to zero is rejected. *(checks `pvalue_agreement` and `pvalue_adj_agreement`)*
13. **`pval_adj`** — the same rule as `pval`: relative tolerance 1 × 10⁻² with the same 0/underflow equivalence zone. The adjustment must be Benjamini–Hochberg across the whole tested gene universe of the cluster (never a reported subset): omitting the adjustment, Bonferroni-correcting, or adjusting over a top-k subset moves most values far outside tolerance. *(check `pvalue_adj_agreement`)*
14. **`log2fc`** — absolute tolerance **1 × 10⁻⁴**. Basis: the reference's stabilized effect sizes were written from single-precision storage, whose representation granularity is about 6 × 10⁻⁸ relative (well under 10⁻⁶ absolute on the reported values); a two-orders-of-magnitude margin covers that noise while any genuine error (dropping the 1e-9 stabilizers, swapping cluster and rest means, using a different logarithm base) is rejected by orders of magnitude, including any single pair exceeding the tolerance. *(check `log2fc_agreement`)*

### What is not compared

15. File bytes, CSV quoting style, line terminators, trailing-newline conventions, upper- vs lower-case exponent notation, and number formatting width (beyond rules 2–5). Two outputs that differ only in such serialization details are equally valid, provided the parsed content satisfies the rules above.
16. No cluster is checked for "biological correctness" — the supplied grouping is a fixed computational input, and only the marker analysis conditional on it is graded.
