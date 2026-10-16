# Per-cluster marker-gene identification for a fixed clustering of pooled bone-marrow single-cell data

## Scientific context

The inputs are two 10x Chromium Gene Expression (Multiome) samples — `s1d1` and `s1d3` — of bone-marrow mononuclear cells from healthy human donors (NeurIPS 2021 Multimodal Single-Cell Integration reference dataset; Luecken et al., 2021). In the source analysis, the two samples were pooled, put through permissive quality filtering, log-normalized, and clustered with Leiden; marker genes for each cluster of the annotated (0.50-resolution) clustering were then identified with a per-cluster-vs-rest Wilcoxon rank-sum test on the log-normalized expression, followed by within-cluster Benjamini–Hochberg FDR correction.

Cluster discovery and embedding are **not** part of this task. The per-cell cluster labels from the recorded reference clustering run are **supplied as a fixed grouping input** (derived from one executed Leiden clustering of this dataset; they are not an independently validated biological annotation). Your task is the downstream marker analysis: given the raw expression data and this fixed grouping, produce the per-cluster marker/differential-expression results under the conventions defined below.

## Inputs

| path | content |
|---|---|
| `inputs/s1d1_filtered_feature_bc_matrix.h5` | original 10x filtered feature–barcode matrix, sample `s1d1` (md5 a99285913ea3f3d22600d3d2f8a88e34) |
| `inputs/s1d3_filtered_feature_bc_matrix.h5` | original 10x filtered feature–barcode matrix, sample `s1d3` (md5 825f7f7578e3dc0b8955f5a97a402338) |
| `inputs/cell_groups.csv` | fixed per-cell group assignments |

`cell_groups.csv` has one row per analysis cell and columns:

- `sample` — originating sample, `s1d1` or `s1d3`;
- `barcode` — the cell barcode exactly as stored in that sample's 10x file (a nucleotide sequence with a trailing `-1`);
- `cluster` — the group label (an integer-like string); use it verbatim as the group identifier.

A cell of the pooled analysis is identified by the pair (`sample`, `barcode`), which is unique across the two samples. The table covers exactly the analysis population defined below (it already accounts for the quality filtering) and contains no missing values.

## Population, identifiers, and normalization (conventions of the source analysis)

1. For each sample, read its 10x matrix and keep only features whose feature type is `Gene Expression`; the gene identifier is the feature's gene symbol. Values are raw integer UMI counts.
2. For each sample separately, make duplicate gene symbols unique: the first occurrence keeps its name; subsequent occurrences get `-1`, `-2`, … appended, in feature order. These suffixed identifiers are the gene identifiers for the entire analysis and must appear in your outputs.
3. Pool the cells of both samples (the row order itself does not affect the requested quantities). The pooled gene universe is the **intersection** (inner join) of the two samples' suffixed gene-identifier sets.
4. Quality filtering, applied **pooled across both samples** (not per sample): first keep cells with at least 100 detected genes; then, on the cell-filtered matrix, keep genes detected in at least 3 cells. "Detected" means a strictly positive count. (Computing QC summaries or doublet scores is not needed; the source applied only these two thresholds, and nothing else in the pipeline alters the expression values used below.)
5. Normalization: for each cell *i* let `total_i` be the sum of its retained counts, and let `T` = median over all cells of `total_i`. Scale each cell to `T` (i.e. value_ij = count_ij × T / total_i) and transform with the natural log1p: x_ij = ln(1 + value_ij). The whole filtered gene set is used for the totals, for `T`, and for the test.
6. Attach cluster labels by joining (`sample`, `barcode`) to `cell_groups.csv`. Your filtered population must match the supplied table one-to-one in both directions; any mismatch indicates a preprocessing deviation.

## Per-cluster marker test

For every supplied cluster label c, with n_c = number of cells in c and N = population size:

- **Groups**: in-group = cells assigned to c; "rest" = all other cells of the pooled population, regardless of their cluster or sample.
- **Statistic** per gene: a two-sided Wilcoxon rank-sum (Mann–Whitney) z-score computed on the log-normalized values. Rank the N cells' values of the gene with **average ranks** (ties receive the mean of the ranks they span); let W_c be the sum of the ranks of the cluster's cells. Then

  `z = ( W_c − n_c (N + 1) / 2 ) / sqrt( n_c (N − n_c) (N + 1) / 12 )`

  This is the source convention: average ranks, normal approximation with **no** tie-variance correction and **no** continuity correction. (If the denominator were zero, report z = 0.)
- **Uncorrected p-value**: two-sided, `p = 2 · (1 − Φ(|z|))` with Φ the standard-normal CDF. Report `0` if the value underflows below the smallest positive representable double.
- **Multiple-testing correction**: Benjamini–Hochberg FDR across **all tested genes within each cluster** — the full filtered gene universe, not merely the reported top genes.
- **Effect size** (the source's definition, on the log-normalized values): with μ_c and μ_rest the arithmetic means of the cluster's and the rest cells' values,

  `log2fc = log2( (e^μ_c − 1 + 1e-9) / (e^μ_rest − 1 + 1e-9) )`

  (natural exponential; the `1e-9` stabilization constants are part of the definition.)
- Genes are ranked within each cluster by descending z-value; exact ties may be broken in any deterministic order.

## Required outputs

1. `outputs/marker_genes.csv` — for each cluster, the 50 genes with the highest z-value (the cluster's markers). Header exactly:

   `cluster,rank,gene,score,pval,pval_adj,log2fc`

   - `cluster` — supplied label, verbatim; `rank` — 1..50 within the cluster, in ascending-score order; `gene` — suffixed gene identifier; `score` — z; `pval` — uncorrected two-sided p-value; `pval_adj` — within-cluster BH-adjusted p-value; `log2fc` — effect size as defined above.
   - Rows ordered by ascending numeric cluster label, then ascending rank. No missing values; all values finite; underflowed p-values written as 0. Report non-zero numeric values with at least 6 significant digits.
2. `outputs/group_sizes.csv` — header `cluster,n_cells`, one row per supplied cluster label.
3. `outputs/analysis_summary.json` — keys `n_cells` (analysis population size), `n_tested_genes` (size of the filtered gene universe actually tested), `target_sum` (the median normalization scale T), `n_groups`.

Consistency requirements: use one cluster identity/label mapping across all three outputs; `n_cells` must equal the per-cluster counts of the supplied grouping; `n_tested_genes` and `n_groups` must describe the test actually performed.

Comparison conventions (finalized during grading validation): gene identity is compared by exact suffixed identifier and marker sets per cluster; numeric fields are compared with tolerances that accommodate single-precision rounding in the recorded values; p-values that underflow to zero on both sides are treated as equal.

## Resources and constraints

- 4 CPU cores, 8 GiB RAM, 10 GiB disk; 600 s wall-clock limit; no network access.
- The required computation is deterministic; no random seeds are involved. If you use any randomized component, fix it so your results are reproducible.
- Software choice is open. A prebuilt offline Python environment containing the scanpy/anndata/h5py/pandas/scipy stack is available for convenience, but any implementation is acceptable (e.g. direct h5py reading plus a scipy-based rank-sum test) as long as the conventions above are met. Note that a standard `scanpy.tl.rank_genes_groups` call with default options, on data prepared as above, implements these same conventions.

## Data provenance and license

- Expression data: figshare doi:10.6084/m9.figshare.22716739.v1 (NeurIPS 2021 benchmark dataset, CC BY 4.0).
- The supplied cell-group table is derived from the recorded Leiden (resolution 0.50) clustering run of this dataset, computed on the pooled, filtered, log-normalized data as described above; it fixes the grouping for this task and is not claimed to be a validated biological annotation.
