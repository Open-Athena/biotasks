# Preprocessing, clustering and marker-gene identification of two bone-marrow scRNA-seq samples

## Objective

Starting from two supplied 10x Genomics filtered feature-barcode matrices (gene expression) from the NeurIPS 2021 benchmark bone-marrow dataset — sample **s1d1** and sample **s1d3** — run the standard single-cell preprocessing, clustering and annotation workflow described below and produce three tabular output files:

1. per-cell clustering assignments and a coarse lineage annotation,
2. a per-cell 2D UMAP embedding,
3. a per-cluster table of differentially expressed (marker) genes.

The methodology below is expressed in scientific terms and corresponds to the standard scanpy 1.11 single-cell workflow. A pinned environment is supplied for convenience (scanpy 1.11.5, anndata 0.11.3, leidenalg 0.12.0 / igraph 1.0.0, umap-learn 0.5.12, scikit-learn 1.9.1, scipy 1.18.1, numpy 2.5.4, pandas 2.3.3), but you may use any software that produces outputs meeting this contract.

## Inputs

- `inputs/s1d1_filtered_feature_bc_matrix.h5` — 10x filtered feature-barcode matrix (sample s1d1)
- `inputs/s1d3_filtered_feature_bc_matrix.h5` — 10x filtered feature-barcode matrix (sample s1d3)

Both are 10x Genomics filtered feature-barcode matrices in 10x HDF5 format (barcodes × features), with each feature record carrying a feature type in addition to its name. These files are multimodal: each contains both **Gene Expression** features (gene symbols as feature names, which serve as the gene identifiers) and **Antibody Capture** features. Only the `Gene Expression` features are used as genes in this workflow (in file order, as the standard scanpy 10x reader does); the Antibody Capture features are excluded from the gene set and from all counts, filters and downstream analysis. The network is **offline**: all data you need is supplied; do not fetch anything.

## Pipeline specification

1. **Load and combine.** Read each matrix into a cell × gene expression matrix keeping only Gene Expression features and using the gene symbols as gene identifiers (in each file's feature order). Within each sample, disambiguate duplicated gene symbols (append numeric suffixes). Concatenate the two samples vertically, adding a per-cell `sample` label with values `s1d1` / `s1d3`, and make cell barcodes unique across the combined dataset.
2. **Filtering (order matters).** First remove cells detecting fewer than 100 genes, then remove genes detected in fewer than 3 cells. The surviving cell and gene populations are the analysis population for everything downstream. (Quality-control metric computation, doublet detection by Scrublet per sample, and all plotting do not modify the expression data or any requested output.)
3. **Normalization.** Scale each cell to the dataset median of total counts (median count-depth normalization over all retained cells), then apply `log(1+x)`. All downstream computation uses this log-normalized matrix.
4. **Feature selection.** Select the **2000 most highly variable genes** using the Seurat-style dispersion-based criterion (scanpy `flavor="seurat"` with `n_top_genes=2000`), computed **per sample** and aggregated across samples (batch-aware selection).
5. **Dimensionality reduction.** Run PCA on the **log-normalized expression of the selected highly variable genes** (zero-centered), retaining the leading **50** principal components (fewer only if the retained gene/cell dimensions forbid it).
6. **Neighborhood graph.** Build a k-nearest-neighbor graph on the PCA representation (Euclidean distance, **k = 15**), converted to a UMAP-connectivity weighted graph as is standard in this workflow.
7. **UMAP embedding.** Compute the default 2-dimensional UMAP embedding of the neighborhood graph with library-default parameters (deterministic seed).
8. **Clustering.** Leiden community detection on the neighborhood graph (igraph implementation, modularity-based RB-configuration partition, default random seed):
   - one run at **resolution 1.0 with at most 2 refinement iterations** (the column `leiden`);
   - runs at **resolutions 0.02, 0.50 and 2.00**, each allowed to iterate until convergence (the columns `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`).
   Report cluster labels as integers starting from 0; the label numbering convention is that of the clustering library defaults.
9. **Lineage annotation.** Apply this fixed mapping from `leiden_res_0.02` labels to a per-cell **`cell_type_lvl1`** column:
   `0 → Lymphocytes, 1 → Monocytes, 2 → B Cells, 3 → Erythroid, 4 → Erythroid`.
10. **Marker genes.** For **every cluster of the resolution-0.50 clustering versus all other cells (one-vs-rest)**, test every retained gene with a two-sided Wilcoxon rank-sum test (Mann–Whitney-style, **without tie correction**), ranking genes by descending standardized test score (z-score). Report:
    - `scores`: the standardized z-score,
    - `pvals`: raw two-sided p-value,
    - `pvals_adj`: Benjamini–Hochberg adjusted p-value, computed over **all retained genes within each group's test**,
    - `logfoldchanges`: scanpy-convention approximate log2 fold change between the group mean and the rest mean, computed from the log-normalized data (log2 of [(expm1(group mean) + 1e-9) / (expm1(rest mean) + 1e-9)]).

## Required outputs (CSV, UTF-8, comma-separated, one header row)

### 1. `clustering_annotation.csv`

One row per retained cell, indexed by cell barcode (unique across the combined dataset; write the barcode as the first column with an empty index-column header). Order rows by sample (all `s1d1` cells first, then all `s1d3` cells), preserving each sample's barcode order from its input h5 file.

| column | content |
|---|---|
| (index) | cell barcode (unique across the combined dataset) |
| `sample` | `s1d1` or `s1d3` |
| `leiden` | cluster label of the resolution-1.0 run (integer) |
| `leiden_res_0.02` | cluster label of the resolution-0.02 run (integer) |
| `leiden_res_0.50` | cluster label of the resolution-0.50 run (integer) |
| `leiden_res_2.00` | cluster label of the resolution-2.00 run (integer) |
| `cell_type_lvl1` | lineage label from the fixed mapping in step 9 |

### 2. `umap_embedding.csv`

One row per retained cell, indexed by the same barcodes and in the same row order as `clustering_annotation.csv`.

| column | content |
|---|---|
| (index) | cell barcode |
| `UMAP1` | first UMAP coordinate (arbitrary units) |
| `UMAP2` | second UMAP coordinate (arbitrary units) |

### 3. `de_markers.csv`

One row per (cluster, gene) pair: every retained gene for every cluster present in the resolution-0.50 clustering. Rows are grouped by cluster; the group blocks appear in ascending cluster-label order, and within each cluster genes are **ordered by descending score** (this order encodes the marker ranking).

| column | content |
|---|---|
| `names` | gene symbol (unique gene identifier, i.e. after step-1 disambiguation) |
| `scores` | Wilcoxon z-score |
| `logfoldchanges` | log2 fold change (scanpy convention, step 10) |
| `pvals` | raw two-sided p-value (0 when the test statistic underflows to 0) |
| `pvals_adj` | Benjamini–Hochberg adjusted p-value |
| `group` | cluster label of the resolution-0.50 clustering (integer) |

## Resources and constraints

- Offline network (no downloads permitted; everything needed is supplied).
- 4 CPU cores, 8 GiB RAM, 10 GiB disk.
- Runtime limit 600 seconds (the pinned reference workflow completes well within this budget).
- Numeric formatting: print enough significant digits that values are recoverable to single-precision float accuracy; missing values are not expected in any output column.
- Row populations are defined by the filtering in step 2; do not apply any additional cell or gene filtering, subsetting, or cluster-number trimming beyond what is specified.

