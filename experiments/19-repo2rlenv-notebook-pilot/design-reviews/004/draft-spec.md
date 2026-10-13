## Task
Reproduce the Scanpy single-cell preprocessing and clustering workflow on two real bone marrow 10x Multiome samples, producing QC-filtered, doublet-annotated, normalized, HVG-reduced, Leiden-clustered cells with per-cluster marker genes, and report the intermediate quantities as deterministic artifacts.

## Agent-Visible Task Brief
**Goal**: Starting from two raw 10x Gene Expression count matrices (s1d1, s1d3), execute the full preprocessing-and-clustering pipeline from the source notebook (QC metrics, filtering, doublet detection, log1pF normalization, HVG selection, PCA, neighbor graph, Leiden clustering at three resolutions, Wilcoxon marker genes) and write the annotated AnnData object plus a JSON summary of pipeline checkpoints.

**Inputs**:
- `/inputs/data/s1d1_filtered_feature_bc_matrix.h5` and `/inputs/data/s1d3_filtered_feature_bc_matrix.h5` (10x Cell Ranger HDF5, ~8,000 cells and 36,601 genes each; healthy human donor bone marrow mononuclear cells, NeurIPS 2021 Open Problems benchmark; CC BY 4.0).
- Read each with `scanpy.read_10x_h5` (or any correct 10x H5 reader), make gene names unique, concatenate with `label="sample"`, make cell barcodes unique. The `sample` column must hold values `s1d1` and `s1d3`.

**Methodology** (all parameters public requirements, taken from the source notebook):
1. Gene annotation: `mt` = gene names starting `MT-`; `ribo` = starting `RPS` or `RPL`; `hb` = matching regex `^HB[^(P)]`. Compute per-cell QC metrics for these three gene sets with `log1p=True`.
2. Filtering: remove cells with fewer than 100 detected genes (`min_genes=100`); remove genes detected in fewer than 3 cells (`min_cells=3`). Permissive thresholds are intentional — do not apply extra QC filtering.
3. Doublet detection: `sc.pp.scrublet(adata, batch_key="sample")` (or an equivalent batch-aware Scrublet implementation), storing `doublet_score` and `predicted_doublet` in `.obs`. Do NOT remove doublets; keep them annotated.
4. Store raw counts in `adata.layers["counts"]`, then normalize to median total counts (`sc.pp.normalize_total` with default target_sum=None, i.e. median) and apply `log1p`.
5. Highly variable genes: Seurat-flavor HVG with `n_top_genes=2000`, `batch_key="sample"`, computed on the log-normalized data.
6. PCA on HVG-scaled-independent defaults of `sc.tl.pca` (default flavor; deterministic zero-centered PCA on the log-normalized HVG subset; set seed 0 for any stochastic component).
7. Neighbor graph with `sc.pp.neighbors` defaults on the PCA representation (seed 0).
8. Leiden clustering with igraph flavor, `n_iterations=2`, at resolutions 0.02, 0.50 and 2.00, stored as `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00` (zero-padded to 2 decimals); run with a fixed seed (0).
9. Wilcoxon rank-sum differential expression per cluster of `leiden_res_0.50` (one-vs-rest, `sc.tl.rank_genes_groups(..., method="wilcoxon")`).

**Acceptance Criteria**:
- `/outputs/adata_processed.h5ad`: the final AnnData with `sample`, `doublet_score`, `predicted_doublet`, QC metrics (`n_genes_by_counts`, `total_counts`, `pct_counts_mt`, `pct_counts_ribo`, `pct_counts_hb`), `layers["counts"]` (raw integer counts post-filtering), log1p-normalized `.X`, `var["highly_variable"]`, PCA (`obsm["X_pca"]`), neighbors, and the three Leiden columns.
- `/outputs/summary.json` with: `n_cells_initial` (per sample and total after concatenation), `n_genes_initial`, `n_cells_filtered`, `n_genes_filtered`, `n_doublets_predicted`, `median_total_counts` (pre-normalization median of the size factors), `n_hvg`, `pca_variance_ratio` (list of all computed components), `leiden_cluster_sizes` (object mapping each resolution to cluster-label → cell count), `top5_markers` (map of each `leiden_res_0.50` cluster label to list of top-5 upregulated gene names by Wilcoxon score).

**Environment Constraints**: Offline; CPU-only container with 4 vCPUs / 8 GiB RAM; complete within 600 s wall clock. Python 3.12 with scanpy, anndata, igraph, leidenalg, numpy, scipy, h5py, pooch installed. Random seeds set to 0 wherever stochasticity can be seeded (scrublet, PCA, neighbors, leiden).

**Visible Paths**: inputs in `/inputs/data/`, outputs in `/outputs/`.

## Builder-Only Notes
**Dependency Chain**: QC metrics → filtering → scrublet (on filtered data, batch-aware) → normalization → HVG → PCA → neighbors → Leiden (three resolutions) → Wilcoxon markers. Each stage's outputs feed the next; summary.json values are read from the corresponding intermediate states.

**Unresolved Questions**:
- Exact runtime on the target hardware must be measured at build time; if scrublet or the full 36k-gene PCA exceeds the budget, subsample NearestNeighbors defaults must be tuned — flag before changing the scientific method.
- Leiden igraph with seed 0 is nominally deterministic, but the builder must confirm bit-stability across two fresh runs; if label ordering differs between runs, tests must compare partitions up to label permutation (see Testing).
- The number of clusters at each resolution must be recorded at build time from the reference run; expected: coarse resolution yields ~5 clusters, 0.50 yields ~10–15, 2.00 more. These are reference observations for the builder only.

## Instructions
Builder must: (1) stage both h5 files at `/inputs/data/` with md5 verification against the provider checksums given in provenance; (2) build reference solution with pinned package versions (scanpy ≥1.10, igraph, leidenalg); (3) run the full pipeline twice to confirm determinism; (4) measure runtime and confirm it fits ≤600 s (if not, report back — do not silently drop stages); (5) write pytest tests as described below using an independently rerun reference pipeline (stored outside solver-visible paths) rather than hand-copied numbers; (6) record md5s of staged inputs in the environment manifest.

## Source Context
Source: Scanpy tutorial "Preprocessing and clustering" (scverse/scanpy, commit 8c1463d, BSD-3-Clause). The notebook: loads s1d1/s1d3 from figshare DOI 10.6084/m9.figshare.22716739.v1, computes QC metrics for mt/ribo/hb gene sets, filters min_genes=100 / min_cells=3, runs batch-aware scrublet, median-normalizes and log1p-transforms, selects 2000 HVGs with batch_key, PCA, neighbors, UMAP, Leiden (igraph, n_iterations=2, resolutions 0.02/0.5/2.0), and Wilcoxon marker genes on leiden_res_0.50. Adaptations proposed here: (a) UMAP embedding and all plotting are omitted — visualization is not verifiable artifact science and costs runtime; (b) manual cell-type annotation from the dotplot is omitted — it relies on human visual judgment; solver-level annotation is replaced by the algorithmic DEG output; (c) fixed random seed 0 is specified where the notebook left defaults, for determinism; (d) summary.json output format is added so grading is artifact-based. No input reduction: both full samples are used (total ~230 MB on disk, in-memory sparse feasible).

## Environment Setup
Debian base, Python 3.12, uv-managed env: scanpy, anndata, leidenalg, igraph, numpy, scipy, pandas, h5py, pytest. Build-time downloads of the two h5 files from figshare (URLs in provenance), md5-verified (a99285913ea3f3d22600d3d2f8a88e34 and 825f7f7578e3dc0b8955f5a97a402338). Reference pipeline output (reference adata + summary) generated at build time and stored outside `/outputs` and outside solver-readable input paths.

## Reasoning Steps Required
1. Load both h5 files, uniquify names, concatenate with sample labels → initial counts.
2. Annotate mt/ribo/hb genes; compute QC metrics.
3. Filter cells (min 100 genes) and genes (min 3 cells).
4. Run batch-aware scrublet; record doublet annotations.
5. Save counts layer; median-normalize + log1p.
6. Select 2000 HVGs per batch; record HVG set.
7. PCA (seeded); record variance ratios.
8. Build neighbor graph (seeded).
9. Leiden at 0.02/0.50/2.00 (igraph, 2 iterations, seed 0); record cluster sizes.
10. Wilcoxon DEG per leiden_res_0.50 cluster; record top-5 genes per cluster.
11. Write adata_processed.h5ad and summary.json.

## Testing
All tests compare against an independently executed reference pipeline (rerun from trusted inputs at grade time or checksummed reference artifacts generated at build time).
1. **Input integrity / initial shape**: `summary.json` reports n_cells/n_genes matching direct recomputation from the staged h5 files after uniquification. Rejects fabricated counts.
2. **Filtering correctness**: recompute min_genes=100 / min_cells=3 filters from raw inputs; compare cell and gene counts exactly (integer equality) and cross-check that `adata.obs` barcodes equal the expected surviving set.
3. **QC metric correctness**: recompute `pct_counts_mt` and `total_counts` per cell from `layers["counts"]` and the mt gene mask; compare (rel tolerance 1e-9 for float sums). Rejects wrong gene masks or wrong count basis.
4. **Normalization correctness**: verify each cell's pseudocount column in `.X` equals log1p(counts / cell_total × median_total_counts) using the submitted counts layer and reported median; tolerance 1e-6. Rejects CP10k or CPM normalization.
5. **Doublet detection performed**: `doublet_score` present for all cells, finite, in [0,1]; `predicted_doublet` boolean; recompute the scrublet doublet count from the reference run (exact integer match given seed 0 — builder must confirm determinism, else relax to |difference| within Poisson tolerance justified at build time) and require summary `n_doublets_predicted` consistency with `.obs`.
6. **HVG selection**: overlap of submitted HVG set vs reference HVG set ≥ 95% (both are deterministic given same input; small deviations possible from library versions — builder calibrates this threshold at build time by running an alternative scanpy version).
7. **Clustering**: cluster-size vectors per resolution compared to reference partition under best label permutation (cluster-label symmetry); require identical number of clusters and identical partitions (adjusted Rand index = 1 vs reference, tolerance unresolved pending determinism confirmation) for at least resolutions 0.02 and 0.50; summary JSON sizes must be consistent with `.obs` value counts.
8. **Marker genes**: for ≥3 randomly chosen clusters (fixed seed for the test), top-5 Wilcoxon genes must match reference exactly for at least 4/5 genes per cluster; full-set test optional if runtime allows. Rejects skipped DEG or wrong groupby.
9. **Structural completeness**: h5ad readable by anndata, contains `sample`, `X_pca`, counts layer, three leiden columns, PCA variance ratio length matches `X_pca.shape[1]` and matches summary list.
10. **Meaningful negative control**: a submission that skips scrublet, uses wrong filtering thresholds, or CP10k normalization is rejected by tests 3–5.

## Difficulty
medium: the pipeline is fully specified and uses standard scanpy calls, but requires correct ordering, batch-aware stages, determinism care, and correct artifact serialization within the time budget.

## Core Skills Tested
Single-cell RNA-seq preprocessing, batch-aware QC and doublet detection, normalization semantics, feature selection, graph clustering interpretation, marker-gene DE testing, reproducible scientific computation.

## Key Technologies
scanpy (methodology reference implementation), anndata, leidenalg/igraph (neighbors/leiden), NumPy/SciPy (verification recomputation), pytest (grading). Any software implementing the stated methodology is permitted; scanpy is the natural choice.

## External Resources
- Notebook: https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb (BSD-3-Clause).
- Data: figshare DOI 10.6084/m9.figshare.22716739.v1, files https://ndownloader.figshare.com/files/40347877 (s1d1, md5 a99285913ea3f3d22600d3d2f8a88e34) and https://ndownloader.figshare.com/files/40347880 (s1d3, md5 825f7f7578e3dc0b8955f5a97a402338), CC BY 4.0. Metadata verified via figshare API; file downloads not yet verified — builder must do so.