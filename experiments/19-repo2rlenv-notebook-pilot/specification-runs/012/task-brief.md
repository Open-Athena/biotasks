# Preprocessing and clustering of human bone-marrow scRNA-seq (two 10x samples)

## 1. Scientific objective and inputs

Reproduce the recorded reference workflow: a basic preprocessing-and-clustering analysis of bone-marrow mononuclear cells from two healthy human donors (OpenProblems NeurIPS 2021 benchmarking dataset; 10x Multiome gene-expression libraries), jointly processed across the two samples. The workflow permissively quality-filters cells and genes, detects putative doublets, median-normalizes and log1p-transforms counts, selects highly variable genes, reduces to principal components, builds a cell-cell neighborhood graph, embeds it with UMAP, clusters it with Leiden at a default and three explicit resolutions, manually annotates the coarsest solution with broad lineages, and computes per-cluster differentially expressed (marker) genes with a Wilcoxon one-vs-rest test.

Terminal deliverables of the reference workflow are (i) the per-cell Leiden cluster assignments at all computed resolutions, the manual broad-lineage annotation, the originating sample, and the 2-D UMAP coordinates; and (ii) the per-cluster ranked differentially expressed genes at the 0.50-resolution clustering, together with the run parameters of that test.

Inputs (task-relative, the complete data basis of the analysis; identical bytes to the provider files, CC BY 4.0):

- `inputs/s1d1_filtered_feature_bc_matrix.h5` — 10x filtered feature-barcode matrix, sample s1d1 (figshare doi:10.6084/m9.figshare.22716739.v1; provider md5 `a99285913ea3f3d22600d3d2f8a88e34`).
- `inputs/s1d3_filtered_feature_bc_matrix.h5` — 10x filtered feature-barcode matrix, sample s1d3 (provider md5 `825f7f7578e3dc0b8955f5a97a402338`).

No other biological inputs are used. The reference staged the two files through a pooch cache that md5-checks them against the provider registry; a solver may read the files directly by any equivalent mechanism. Matrices hold raw UMI counts over genes (10x feature space; gene symbols as `var_names`).

## 2. Reference recipe (ordered; pinned versions)

Recorded reference environment: CPython 3.13, scanpy 1.12.4, anndata 0.13.4, igraph 1.0.0, leidenalg 0.12.0, umap-learn 0.5.12, pynndescent 0.6.0, numba 0.68.0, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, pandas 3.0.6, h5py 3.16.0, pooch 1.9.0. All operations below are named with their qualified names and these pinned versions; every argument not listed is that version's default. Figures are rendered off-screen (headless backend); plotting steps are part of the recorded workflow but add no exported result.

1. **Load and combine the two samples.** For each sample (in order s1d1, then s1d3): `scanpy.read_10x_h5(path)` (scanpy 1.12.4) to read the count matrix into an `AnnData`; `AnnData.var_names_make_unique()` (anndata 0.13.4) to disambiguate duplicated gene symbols. Then `anndata.concat(adatas, label="sample")` (anndata 0.13.4) to stack the two objects, writing each cell's sample id into `obs["sample"]`, followed by `AnnData.obs_names_make_unique()` (anndata 0.13.4) so shared 10x barcodes across the two samples become unique cell identifiers. Purpose: one genes x cells matrix with a per-cell sample/batch label.
2. **QC metric annotation.** Gene-population masks in `var`: mitochondrial `var["mt"] = var_names.str.startswith("MT-")`, ribosomal `var["ribo"] = var_names.str.startswith(("RPS", "RPL"))`, hemoglobin `var["hb"] = var_names.str.contains("^HB[^(P)]")`; then `scanpy.pp.calculate_qc_metrics(adata, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True)` — per-cell total counts, genes detected, proportions of counts in each population, and log1p variants. Purpose: diagnostics used only to choose the deliberately permissive filtering below and to re-assess quality on the UMAP later.
3. **Permissive filtering.** `scanpy.pp.filter_cells(adata, min_genes=100)` and `scanpy.pp.filter_genes(adata, min_cells=3)`. Purpose: drop cells with fewer than 100 detected genes and genes detected in fewer than 3 cells; no further cell/gene subsetting occurs anywhere in the workflow (doublets are detected but deliberately not removed).
4. **Doublet detection.** `scanpy.pp.scrublet(adata, batch_key="sample")` — Scrublet run per sample (per-sample simulations), storing per-cell `doublet_score` and `predicted_doublet` in `obs`. Diagnostic only: the tutorial explicitly leaves both doublet-removal options unexecuted.
5. **Normalize.** Keep the filtered raw counts aside as `adata.layers["counts"] = adata.X.copy()`; then `scanpy.pp.normalize_total(adata)` (median count-depth scaling; `target_sum` omitted) followed by `scanpy.pp.log1p(adata)`. Purpose: count-depth scaling plus log1p, applied on the same matrix used for all subsequent steps.
6. **Feature selection.** `scanpy.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")`. Purpose: flag the 2000 most informative genes (batch-aware across the two samples) for the dimensionality reduction.
7. **Dimensionality reduction.** `scanpy.tl.pca(adata)` — PCA on the workflow's PCA-eligible matrix with this version's defaults, storing the cell scores and variance measures in the default `obsm`/`var`/`uns` locations. Purpose: denoise and reveal the main axes of variation.
8. **Neighborhood graph.** `scanpy.pp.neighbors(adata)` — k-NN graph on the PCA representation with this version's defaults. Purpose: the cell-cell similarity graph all clustering and the UMAP embedding derive from.
9. **UMAP embedding.** `scanpy.tl.umap(adata)` — 2-component UMAP of the neighborhood graph, stored in `adata.obsm["X_umap"]`.
10. **Leiden clustering (default resolution).** `scanpy.tl.leiden(adata, flavor="igraph", n_iterations=2)` — Leiden community detection on the neighbor graph using the igraph implementation with 2 iterations and the version's default resolution; assigned cluster labels go to `obs["leiden"]` as string categories (natural-sorted category set).
11. **Leiden clustering at three explicit resolutions.** For each `res` in `[0.02, 0.5, 2.0]`: `scanpy.tl.leiden(adata, key_added=f"leiden_res_{res:4.2f}", resolution=res, flavor="igraph")` (iterations omitted = version default). Purpose: a coarse, a mid- and a fine-grained clustering solution for annotation; results land in `obs["leiden_res_0.02"]`, `obs["leiden_res_0.50"]`, `obs["leiden_res_2.00"]`.
12. **Manual broad-lineage annotation.** `adata.obs["cell_type_lvl1"] = adata.obs["leiden_res_0.02"].map({"0": "Lymphocytes", "1": "Monocytes", "2": "B Cells", "3": "Erythroid", "4": "Erythroid"})` — the tutorial's fixed manual map from the coarsest clustering to broad lineages; cells in clusters outside this map are left unannotated. (This map is the source's fixed methodological constant.)
13. **Differential expression per cluster.** `scanpy.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")` — Wilcoxon rank-sum of each cluster vs the union of all other cells, all groups, over the retained genes of the log1p-normalized `adata.X` (no `raw` is set in this workflow), with the version's default multiple-testing correction. Stores the sorted per-group rankings and the run parameters in `adata.uns["rank_genes_groups"]`.
14. **Display steps (kept, off-screen, non-exported).** `sc.settings.set_figure_params(dpi=50, facecolor="white")`; QC violin and scatter plots; `sc.pl.highly_variable_genes`; PCA variance-ratio and PCA scatter plots; UMAP plots of sample, leiden, doublet/QC overlays and the three resolutions; marker-gene dotplots over the prior-knowledge marker panels below at `leiden_res_0.02` and `leiden_res_0.50`; `sc.pl.rank_genes_groups_dotplot(adata, groupby="leiden_res_0.50", standard_scale="var", n_genes=5)`; `sc.get.rank_genes_groups_df(adata, group="7").head(5)` and the UMAP colored by those five genes. These calls communicate and inspect the results; they add no exported stored result (a dendrogram used by the DE dotplot is computed inside the plotting call with defaults).

Marker panels used only by the dotplots in step 14 (prior knowledge from the source; not an input file): CD14+ Mono: FCN1, CD14; CD16+ Mono: TCF7L2, FCGR3A, LYN; cDC2: CST3, COTL1, LYZ, DMXL2, CLEC10A, FCER1A; Erythroblast: MKI67, HBA1, HBB; Proerythroblast: CDK6, SYNGR1, HBM, GYPA; NK: GNLY, NKG7, CD247, FCER1G, TYROBP, KLRG1, FCGR3A; ILC: ID2, PLCG2, GNLY, SYNE1; Naive CD20+ B: MS4A1, IL4R, IGHD, FCRL1, IGHM; B cells: MS4A1, ITGB1, COL4A4, PRDM1, IRF4, PAX5, BCL11A, BLK, IGHD, IGHM; Plasma cells: MZB1, HSP90B1, FNDC3B, PRDM1, IGKC, JCHAIN; Plasmablast: XBP1, PRDM1, PAX5; CD4+ T: CD4, IL7R, TRBC2; CD8+ T: CD8A, CD8B, GZMK, GZMA, CCL5, GZMB, GZMH (GZMA listed twice in the source); T naive: LEF1, CCR7, TCF7; pDC: GZMB, IL3RA, COBLL1, TCF4.

## 3. Required output files and schemas

Three files, exactly as serialized by the reference export stage (CSV with a header line; JSON). Row identity and ordering follow the reference's stored state; see the identity rules below each table.

### 3.1 `cell_clusters_umap.csv` — per-cell terminal results

One row per retained cell (every cell that survives step 3; the workflow removes no cells afterwards). Columns, in order:

- `cell_id` (index column, named): the reference's unique observation names — a 10x barcode plus its sample-level suffix, and, where concatenating the two samples produced duplicate barcodes, an additional `-<k>` numeric suffix on the second and later occurrences (the anndata 0.13.4 `obs_names_make_unique` convention; the first occurrence keeps the unmodified name). Rows appear in the reference's observation order: all s1d1 cells first, then all s1d3 cells (the source's sample ordering).
- `sample`: the originating sample id, `s1d1` or `s1d3` (categorical string).
- `leiden`: cluster label of the default-resolution Leiden solution (step 10), as a string category.
- `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`: cluster labels of the three resolution-specific solutions (step 11), string categories.
- `cell_type_lvl1`: broad-lineage annotation from the step 12 map applied to `leiden_res_0.02`; the label set is the map's values, and cells in clusters not covered by the map are blank/NaN.
- `umap_1`, `umap_2`: the two components of `X_umap` (dimensionless embedding coordinates), aligned row-by-row with `cell_id`.

Cluster labels are the natural-sorted string categories produced by `sc.tl.leiden` (scanpy 1.12.4); the number of clusters per solution is itself a computed result of the analysis, not a constant. The leiden columns are reference label conventions, not portable biological identities.

### 3.2 `rank_genes_groups_leiden_res_0.50.csv` — per-cluster DE genes (Wilcoxon vs rest)

One row per (cluster group of the `leiden_res_0.50` solution) x (ranked gene): the test ranks **all** retained genes for **every** group, so the row count equals (#groups of the 0.50-resolution solution) x (#retained genes after step 3). Columns, in order:

- `group`: the cluster label (string) — the same label convention and label set as the `leiden_res_0.50` column of `cell_clusters_umap.csv`.
- `names`: gene identifier (10x gene symbol, made unique with the same `-<k>` suffix convention on duplicate symbols).
- `scores`: the Wilcoxon rank-sum z-score underlying the group-vs-rest comparison (group minus rest; positive = enriched in group).
- `pvals_adj`: Benjamini–Hochberg corrected p-value; `pvals`: raw p-value (both probabilities in [0, 1]).
- `logfoldchanges`: log2 fold change (the scanpy approximation computed from mean log-expression values).

Layout: rows are laid out group block by group block; blocks follow the reference's stored group order, which is the category order of the `leiden_res_0.50` categorical (natural-sorted cluster labels); within each block rows follow the reference's stored rank order of the test. In the reference run these values were stored at float32 precision for `scores`/`logfoldchanges` and float64 for the two p-value columns before CSV serialization.

### 3.3 `rank_genes_groups_params.json` — DE run parameters

A JSON object holding the run parameters stored with the DE result, identifying which clustering and test produced section 3.2: keys `groupby`, `reference`, `method`, `use_raw`, `layer`, `corr_method`, recording the recipe's choices (`leiden_res_0.50`, `rest`, `wilcoxon`, no raw used, no alternate layer, the default correction method).

### Relationships between outputs

- The `group` set and the group-block row counts of section 3.2 mirror, respectively, the distinct values of `leiden_res_0.50` and the per-cluster cell counts in section 3.1; the two files describe the same clustering solution.
- `names` in section 3.2 lives in the same uniquified gene-symbol space as the analysis's `var_names`.
- Section 3.3 must be consistent with the test that produced section 3.2.

## 4. Execution constraints, open software choice, pending validation

- Constraints: offline (no network), 4 CPUs, 8 GiB memory, 10 GiB disk, no GPU; analysis timeout 600 s (solver timeout provisional and separately revisitable before solver execution).
- Software choice is open: the solver may use any implementation or package stack, including one other than scanpy/anndata, provided its outputs satisfy the eventual public grading contract. Implementations differing in numerics, algorithm variants or defaults beyond those specified here are not promised to be acceptable.
- **This is a draft reference recipe and output schemas, not a complete grading contract.** The comparison rules, tolerances and acceptable variations (including treatment of cluster-label conventions, embedding geometry, float precision and p-value underflow) are pending the later executable validation stage and will be stated in the public task before any solver attempt.
