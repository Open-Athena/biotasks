## Task
Reproduce the preprocessing, clustering and marker-gene analysis of two healthy human bone-marrow 10X scRNA-seq samples (NeurIPS 2021 multiome dataset, s1d1 and s1d3): QC annotation, cell/gene filtering, median count-depth log1p normalization, batch-aware HVG selection, PCA, kNN graph, Leiden clustering at resolution 0.50, and per-cluster Wilcoxon differential expression, delivered as a processed AnnData object and a DE results table.

## Agent-Visible Task Brief

### Goal and inputs
Process two 10X filtered feature-barcode matrices into a clustered AnnData object plus a cluster-vs-rest differential-expression (DE) table. The only inputs are the staged files (do not fetch anything at solve time):
- `data/s1d1_filtered_feature_bc_matrix.h5` (provider md5 a99285913ea3f3d22600d3d2f8a88e34)
- `data/s1d3_filtered_feature_bc_matrix.h5` (provider md5 825f7f7578e3dc0b8955f5a97a402338)

Any language/software may be used as long as the stated methods are implemented faithfully. CPU-only container, 4 vCPUs, 8 GiB RAM; solver budget 600 s wall time. Seeded stochastic steps (approximate neighbors, Leiden) must use `random_state=0` unless the step is deterministic.

### Requirements
**R1 — Ingestion and concatenation.** Read each `.h5` as a 10X matrix (genes as features, cells as observations), make gene names unique within each sample, and concatenate with a `sample` annotation so `adata.obs["sample"]` is exactly `s1d1` or `s1d3` per cell; cell (obs) names are made unique after concatenation. Cell identity is (sample, original barcode); no barcodes may be invented or dropped.

**R2 — QC gene sets and metrics.** On the concatenated var frame, define boolean gene masks over the made-unique human gene symbols with exactly these semantics: `mt` = names starting with `MT-`; `ribo` = names starting with `RPS` or `RPL`; `hb` = names matching the contains-regex `^HB[^(P)]` (a gene is `hb` iff `str.contains("^HB[^(P)]")` is true, i.e. some substring begins `HB` followed by a character that is not `P`). Compute standard QC metrics with these three qc_vars and log1p variants: per cell `n_genes_by_counts`, `total_counts`, `pct_counts_{mt,ribo,hb}` and `log1p_` forms; per gene `n_cells_by_counts`, `mean_counts`, `total_counts` (+ `log1p_`), `pct_dropout_by_counts`. All QC numbers must describe the pre-filter concatenated matrix and be carried along unchanged through later subsetting (values computed once, then subset — never recomputed on the filtered matrix).

**R3 — Filtering.** First remove cells with `n_genes_by_counts < 100`; then, on the cell-filtered matrix, remove genes detected in fewer than 3 cells (`n_cells_by_counts` recomputed on the post-cell-filter matrix for this decision). Order is consequential.

**R4 — Normalization.** Before normalization, store the filtered raw counts in `layers["counts"]` (must remain raw integer counts). Then scale each cell to the median cell total count over the filtered matrix (count-depth scaling to the median, i.e. `normalize_total` with default `target_sum`), followed by natural `log1p`. `adata.X` after R4 is the log-normalized matrix.

**R5 — Feature selection.** On the log-normalized data, select exactly 2000 highly variable genes using the Seurat flavor (mean/dispersion binning, dispersion normalization), computed per batch (`sample`) and reconciled across batches by the median normalized-dispersion rank across batches (scanpy `n_top_genes` + `batch_key` semantics). Record a boolean `highly_variable` var column plus dispersion/rank columns.

**R6 — PCA.** Compute 50 principal components of the zero-centered log-normalized matrix restricted to the 2000 HVGs, with no per-gene scaling/z-scoring and `random_state=0`. Store the embedding in `obsm["X_pca"]` (n_cells x 50), per-component variance ratio in `uns["pca"]["variance_ratio"]` (length 50) and raw variances in `uns["pca"]["variance"]`.

**R7 — Neighborhood graph and clustering.** Build the kNN graph on `X_pca` using exactly 50 PCs, 15 neighbors, Euclidean metric, `random_state=0`. Run Leiden on that graph with flavor igraph, resolution exactly 0.50, `n_iterations=2`, `random_state=0`; store cluster labels as strings in `adata.obs["leiden_res_0.50"]`. Every cell receives exactly one label; no cell is dropped.

**R8 — Marker genes.** For each `leiden_res_0.50` cluster vs all other cells (one-vs-rest, log-normalized data), compute a two-sided Wilcoxon rank-sum test without tie correction, with Benjamini-Hochberg adjusted p-values. The test score is the z-score computed from ranks as in scanpy's `rank_genes_groups(method="wilcoxon")` (equivalent to `scipy.stats.mannwhitneyu` z-scores without continuity correction). The log2 fold change is computed exactly as: means of the log-normalized values within group and out of group, transformed back to count scale via `expm1`, i.e. `log2((expm1(mean_in) + 1e-9) / (expm1(mean_out) + 1e-9))`. Export every (cluster, gene) pair for all genes in the filtered object.

### Required artifacts
- **A1 — `output/adata_processed.h5ad`** (AnnData H5AD) containing: `obs` columns `sample`, all R2 QC columns, `leiden_res_0.50`; `var` columns `mt`, `ribo`, `hb`, `n_cells_by_counts`, `highly_variable` and HVG dispersion/rank columns; `layers["counts"]` raw counts; `X` log-normalized; `obsm["X_pca"]`; `uns["pca"]` (variance_ratio, variance); `uns["hvg"]` and `uns["neighbors"]` metadata. Cell identity equivalence: `obs_names` may be prefixed/annotated in any style as long as (sample, original barcode) is uniquely recoverable from `obs_names` + `obs["sample"]`; gene identity by symbol.
- **A2 — `output/de_results.tsv`** (tab-separated, header). Columns exactly: `group`, `names`, `scores`, `pvals`, `pvals_adj`, `logfoldchanges`; one row per (cluster, gene) for all clusters and all genes of the filtered var frame; `group` values are the R7 labels.

### Equivalence rules (public)
- Cluster labels are arbitrary strings; grading compares partitions up to bijective relabeling of the induced cell-to-cluster assignment.
- PCA: two results are equivalent if, for each component i independently, the submitted embedding column equals +X or -X of the reference column (signs free per component, independently choosable); variance and variance_ratio comparisons are sign-invariant.
- Gene and cell identity is by symbol / (sample, barcode), never by row position; H5ADs with different internal orderings are equivalent if joinable by these keys with identical values.
- Floating-point tolerances are **unresolved: construction gate**: the builder must calibrate and publish absolute/relative tolerances (via reference and cross-implementation runs) in this brief before release, covering `X`, `X_pca`, variance ratios, HVG dispersions, and all A2 numeric columns. Until published, discrete quantities (gene/cell sets, masks, partitions, top-ranked gene orders) are compared exactly.

## Source Context
The notebook is the scanpy "Preprocessing and clustering" tutorial (commit 8c1463d, BSD-3-Clause) using two bone-marrow samples from the NeurIPS 2021 Open Problems dataset (figshare DOI 10.6084/m9.figshare.22716739.v1, CC BY 4.0; files ~22.8 MB and ~20.4 MB with provider md5s above; download not yet verified per provenance).

Consequential source choices preserved: two-sample concat with `label="sample"`; `var_names_make_unique` per sample then `obs_names_make_unique`; gene sets `MT-`, `RPS|RPL`, regex `^HB[^(P)]`; `calculate_qc_metrics(..., log1p=True)`; `filter_cells(min_genes=100)` then `filter_genes(min_cells=3)`; counts layer saved pre-normalization; median-depth `normalize_total` + `log1p`; `highly_variable_genes(n_top_genes=2000, batch_key="sample")`; default `pca`; default `neighbors`; Leiden with `flavor="igraph"` at res 0.5 (cell 52); `rank_genes_groups(method="wilcoxon")` on `leiden_res_0.50`.

Parameters the notebook leaves to library defaults, made explicit here as design choices (not claimed as source-given): PCA `n_comps=50`, `zero_center=True`, `random_state=0`, no scaling; neighbors `n_neighbors=15`, `n_pcs=50`, `metric="euclidean"`, `random_state=0`; Wilcoxon `tie_correct=False`, BH `corr_method`; HVG flavor `seurat`. Each pinned value must match the pinned scanpy version's actual default at construction or be reported as a deviation.

**Adaptation (Leiden n_iterations):** the notebook's res-0.5 call (cell 52) sets only `flavor="igraph"` and inherits the library default; the tutorial's other Leiden call (cell 41) explicitly uses `n_iterations=2`, the recommended igraph setting. This design pins `n_iterations=2` so the contract does not depend on an unverified default. Scientific consequence: if the pinned library default would iterate differently, the partition could differ (more/fewer communities); a construction gate must verify the pinned version's default and confirm whether 2 coincides with it — if not, this is a documented deviation from cell 52, justified by cell 41 and by fixing a deterministic, reproducible contract.

**Adaptation (logFC formula exposed):** cell 67 uses `rank_genes_groups` default fold-change computation, which is not narrated in the notebook; R8 states it explicitly (expm1 back-transform with 1e-9 epsilon, then log2). Effect: pinning the formula removes ambiguity; a solver computing log2 of ratio of log-means would produce a numerically different, non-equivalent column, and that deviation is rejected.

Omissions (all without downstream effect on graded artifacts): scrublet doublet scores (cell 18) — the notebook annotates but never filters on them, so cell/gene sets, normalization, HVG, PCA, graph, clusters and DE are unchanged; UMAP and all plots — visualization only, Leiden runs on the kNN graph; Leiden at res 0.02/2.0 and the manual `cell_type_lvl1` mapping — manual annotation requiring expert judgment and reference-specific cluster identities; pseudobulk DE (cell 74) — a suggestion, not executed; batch integration — the notebook observes only a minor batch effect and performs none.

Reductions: none; both samples and all cells are used.

## Environment Setup
- Data: at build time download `https://ndownloader.figshare.com/files/40347877` and `https://ndownloader.figshare.com/files/40347880`, verify provider md5s (a99285913ea3f3d22600d3d2f8a88e34, 825f7f7578e3dc0b8955f5a97a402338), stage to `data/`. Provenance has not verified these checksums; failure = broken-seed gate, reported not absorbed.
- Software: pin exact versions at build time (scanpy, anndata, numpy, scipy, igraph, leidenalg, pandas, h5py) and stage an offline-installable environment. Scanpy is a suggested implementation only — the contract is method-level; the R8 z-score and logFC formulas are stated so any implementation can reproduce them.
- Resource hypotheses (to be measured): ~16k cells x ~36k genes; h5 load <30 s; HVG/PCA/neighbors/Leiden/full Wilcoxon DE well within 600 s and 8 GiB. Gate failures must be reported, never handled by dropping data or steps.

## Testing
| Req | Artifact (stage) | Trusted check | Rule | Meaningful wrong result rejected |
|---|---|---|---|---|
| R1 | A1 obs sample/cell set | Independent recompute of barcode sets from the raw h5 files with h5py, no scanpy | Exact set equality of (sample, barcode) | Loading only s1d1, or incorrect dedup/renaming of barcodes, fails the exact set check |
| R2 | A1 var masks + QC columns | Recompute masks from reference var_names; recompute n_genes/total/pct columns for a random cell subset from the raw counts | Boolean equality; numeric equality within published tolerance | `hb` computed as `startswith('HB')` (wrongly includes HBP1) fails the mask check; QC recomputed on the filtered matrix fails the subset recompute |
| R3 | A1 post-filter cell/gene sets | Reference partition recomputed independently from raw counts | Exact set equality, order irrelevant | Reversed filter order (genes filtered on unfiltered matrix), or `min_genes=50`/`min_cells=10`, yields a different gene/cell set and fails exactly |
| R4 | A1 `layers['counts']` and `X` | Recompute `log1p(counts * median(total)/total)` per cell from the raw counts for a cell sample plus a full-matrix median check; counts bit-exact vs raw | Formula equality within published tolerance; counts exact | CP10k (`target_sum=1e4`) or missing log1p fails the formula recompute; any mutated counts layer fails bit-exactness |
| R5 | A1 `var['highly_variable']` set | Private reference HVG set from the reference pipeline | Exact gene-set equality | `cell_ranger` flavor, wrong `n_top_genes`, no `batch_key`, or selection pre-normalization — each yields a different 2000-gene set |
| R6 | A1 `X_pca`, `uns['pca']` | Private reference PCA from the independently validated log-normalized HVG matrix (not from A1) | Per-component sign-free comparison (independent per-component sign); variance_ratio within published tolerance | PCA on all genes, non-zero-centered, or on z-scored data fails; uncentered PCA has different variance ratios |
| R7 | A1 `obs['leiden_res_0.50']` partition | Private reference partition | Partition equality up to bijective relabeling | Resolution 0.02 or 2.0, graph on pre-PCA data, or a dropped/merged cluster yields a strictly different partition |
| R8 | A2 full table | Private reference Wilcoxon table; cross-implementation spot check vs `scipy.stats.mannwhitneyu` z-scores for sampled (cluster, gene) pairs; BH column re-derived from A2's own pvals; internal consistency of A2 group labels vs A1 partition and gene set vs A1 var_names | Per cluster, top-20 up-regulated genes by score match the reference ranking in order (tie-aware rule per gate); full numeric columns within published tolerance; BH exact re-derivation | t-test instead of Wilcoxon, DE on raw counts, missing BH adjustment (fails re-derivation), or logFC from log-means (numerically different column) each fail; labels not bijective to reference clusters fail cross-check |

## Builder-Only Notes
Private assets: reference solution pipeline outputs (A1, A2) produced at construction with the pinned environment; reference HVG set, PCA, partition, and DE table stored where the solver cannot read them.

Construction gates (each must pass before release; failures are reported, never absorbed):
1. **Input integrity:** download both files, verify md5s against provider values. Failure = broken seed.
2. **Pinning and defaults:** stage the offline environment with pinned versions; record the pinned scanpy defaults actually in force (leiden `n_iterations` for igraph flavor, pca `n_comps`/`zero_center`/`svd_solver`/`random_state`, neighbors `n_neighbors`/`n_pcs`/`metric`/`random_state`, rank_genes_groups `tie_correct`/`corr_method`, hvg default flavor). Confirm each R-numbered parameter; specifically resolve the F4 question — if the igraph-flavor default is not 2, record the deviation explicitly and decide whether to revise the contract (the published contract value 2 stands unless evidence shows the source run differs materially, which would require reporting back for a revised design).
3. **Resources:** measure reference wall time and peak memory on the 4 vCPU / 8 GiB / 10 GiB container against the 600 s budget; report failure rather than reducing data or steps.
4. **Tolerance calibration:** compare the pinned reference against an independent implementation (e.g. scipy mannwhitneyu for z-scores) and across repeated runs; publish absolute/relative tolerances for X, X_pca, variance ratios, dispersions, and all A2 numeric columns in the public brief before release.
5. **Determinism:** verify repeated-run reproducibility of pynndescent neighbors (random_state=0) and igraph Leiden (random_state=0); if the exact partition is not reproducible, report back for a revised equivalence rule rather than weakening the test.
6. **Ranking tie stability:** measure the minimum score gap at rank 20 per cluster; if near-ties exist, publish a tie-aware top-20 rule before release.
7. **Controls:** run reference-solution, empty-output, and meaningful-wrong-output controls — `target_sum=1e4` normalization, `cell_ranger` HVG flavor, resolutions 0.02/2.0, raw-counts DE, `hb` via `startswith('HB')`, logFC from log-means — and confirm each is rejected by the corresponding independent check.

No silent changes to the public contract: any parameter settled by a gate (defaults, tolerances, tie rules) must be published in the brief before release. LLM opinions are not used for grading.

## Difficulty
medium — the pipeline is a well-trodden scanpy workflow with modest compute on ~16k cells, but strict artifact-level verification (cross-implementation numerical tolerances for PCA/Wilcoxon, label-permutation-invariant cluster comparison, exact logFC formula, and reproducible stochastic graph/Leiden steps) requires careful engineering.