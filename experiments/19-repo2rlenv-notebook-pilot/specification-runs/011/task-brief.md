# Bone marrow scRNA-seq: Preprocessing and Clustering (scanpy tutorial)

## Scientific objective

Reproduce the reference single-cell RNA-seq preprocessing and clustering workflow from the scanpy "Preprocessing and clustering" tutorial: per-cell quality control, doublet detection, normalization, feature selection, dimensionality reduction, neighborhood-graph construction, UMAP embedding, Leiden clustering at multiple resolutions, broad-lineage cell-type annotation, and per-cluster marker-gene detection. The workflow is applied jointly to two 10x samples (s1d1, s1d3) from bone-marrow mononuclear cells of healthy human donors (NeurIPS 2021 Open Problems benchmark; 10x Multiome gene-expression data).

**Required outputs**: (1) per-cell table of cluster assignments, cell-type labels and UMAP coordinates; (2) per-cluster differentially expressed genes (Wilcoxon vs rest) at the leiden_res_0.50 resolution; (3) the DE run-parameter record.

**Inputs** (task-relative paths; two 10x filtered-feature-barcode h5 matrices, CC BY 4.0):

- `inputs/s1d1_filtered_feature_bc_matrix.h5` (~8,785 cells, provider md5 `a99285913ea3f3d22600d3d2f8a88e34`)
- `inputs/s1d3_filtered_feature_bc_matrix.h5` (~8,340 cells, provider md5 `825f7f7578e3dc0b8955f5a97a402338`)

 ## Reference recipe (pinned package versions)

Software pinning: Python 3.13, scanpy 1.12.4, anndata 0.13.4, igraph 1.0.0, leidenalg 0.12.0, umap-learn 0.5.12, pynndescent 0.6.0, numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, scipy 1.18.1, pooch 1.9.0, scikit-image 0.26.0. Any software may be used, provided the required outputs match the eventual public grading contract.

### 0. Data loading

For each sample in order `s1d1`, then `s1d3`:

1. Read the 10x h5 file with `scanpy.read_10x_h5(path)` — keep only `feature_types == "Gene Expression"` (default `gex_only=True`); rows are cell barcodes, columns are gene names (`var_names` from gene symbols), `gene_ids` in `var`.
2. `var_names_make_unique()`: gene symbols that repeat within a sample are made unique by appending `-1`, `-2`, ... to the second and later occurrences.

Then concatenate:

3. `anndata.concat({s1d1: adata1, s1d3: adata3}, label="sample")` with the default join (intersection of the two samples' gene sets) and `index_unique=None`; this adds `adata.obs['sample'] ∈ {s1d1, s1d3}`.
4. `obs_names_make_unique()`: barcodes duplicated across samples become e.g. `AAACCCAAGGATGGCT-1` vs `...-2` (anndata `make_index_unique`, join character `-`). These post-concatenation, unique-between-samples barcodes are the **cell_id** identity used in output 1.

### 1. Quality control (per-cell)

5. `adata.var['mt'] = var_names.str.startswith("MT-")`; `adata.var['ribo'] = var_names.str.startswith(("RPS","RPL"))`; `adata.var['hb'] = var_names.str.contains("^HB[^(P)]")`.
6. `sc.pp.calculate_qc_metrics(adata, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True)` — populates `n_genes_by_counts`, `total_counts`, `pct_counts_*` (and `log1p_` variants) in `.obs`, and per-gene metrics in `.var`. These are diagnostics that motivate the deliberately permissive filtering below.
7. `sc.pp.filter_cells(adata, min_genes=100)` then `sc.pp.filter_genes(adata, min_cells=3)` — the only filtering applied.

### 2. Doublet detection

8. `sc.pp.scrublet(adata, batch_key="sample")` — scanpy 1.12.4 default parameters (`sim_doublet_ratio=2.0`, `expected_doublet_rate=0.05`, `n_prin_comps=30`, `random_state=0`), executed per sample on a copy with its own internal `filter_genes(min_cells=3)`/`filter_cells(min_genes=3)`, median-normalization + CPM normalization, `flavor="seurat"` HVG selection, and kNN doublet classification; results are mapped back onto the original cell order, adding `adata.obs['doublet_score']` and `adata.obs['predicted_doublet']`. Cells are **not** removed (the tutorial only scores doublets, filtering is deferred to interpretation).

### 3. Normalization

9. `adata.layers['counts'] = adata.X.copy()` — save the unnormalized counts (not exported as a deliverable).
10. `sc.pp.normalize_total(adata)` with `target_sum=None` — scale each cell to the median of total counts across all cells (log1PF normalization).
11. `sc.pp.log1p(adata)` — natural-log(1 + x) transform of `adata.X`.

### 4. Feature selection

12. `sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")` — default `flavor="seurat"`; with `n_top_genes` set, the default mean/dispersion cutoffs are replaced by top-n selection, computed per batch and merged by number-of-batches-then-dispersion ordering. Variable names are NOT subsetted; the `highly_variable` column drives downstream PCA masking.

### 5. Dimensionality reduction

13. `sc.tl.pca(adata)` — default `n_comps` resolves to 50 (scanpy `settings.N_PCS`); because `highly_variable` is present in `.var`, PCA is computed on the 2,000 HVG columns only (auto `mask_var='highly_variable'`); default dense/sparse solver `'arpack'`; `zero_center=True`, `random_state=0`. Stores `obsm['X_pca']`, `varm['PCs']`, `uns['pca']` (`variance_ratio`, `variance`).

### 6. Neighborhood graph

14. `sc.pp.neighbors(adata)` — defaults: `n_neighbors=15`, `n_pcs=None` (use all 50 PCs of `X_pca`), `knn=True`, `method='umap'` (connectivity kernel), `metric='euclidean'`, `random_state=0`. With >4,096 cells the kNN backend is `pynndescent` (PyNNDescentTransformer with n_trees/n_iters as in UMAP's nearest_neighbors). Stores `obsp['distances']`, `obsp['connectivities']`, `uns['neighbors']`.

### 7. Visualization embedding

15. `sc.tl.umap(adata)` — UMAP on the neighborhood graph, defaults `min_dist=0.5`, `spread=1.0`, `n_components=2`, `init_pos='spectral'`, `negative_sample_rate=5`, `random_state=0`, 200 epochs for >10,000 cells. Stores `obsm['X_umap']` (17,041 × 2 float array; units are arbitrary UMAP coordinates).

### 8. Clustering

16. `sc.tl.leiden(adata, flavor="igraph", n_iterations=2)` — the igraph implementation of the Leiden modularity algorithm on the neighborhood connectivities (undirected, edge weights used, `objective_function='modularity'`, `resolution=1`, `random_state=0`; `n_iterations=2` is a fixed 2-iteration run). Result in `adata.obs['leiden']` (categorical string labels `0`, `1`, ...; ≤25 groups observed: 0-24).

Then, for each `res` in `[0.02, 0.5, 2.0]` (in this order):

17. `sc.tl.leiden(adata, key_added=f"leiden_res_{res:4.2f}", resolution=res, flavor="igraph")` — note `n_iterations` is **omitted** here, so the default `-1` (run until optimal) applies; otherwise same operation as step 16. Results in `adata.obs['leiden_res_0.02']` (5 groups: 0-4), `adata.obs['leiden_res_0.50']` (17 groups: 0-16), `adata.obs['leiden_res_2.00']` (36 groups: 0-35), each a categorical with natsorted string categories. Key naming uses `:4.2f` formatting (`leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`).

### 9. Cell-type annotation

18. `adata.obs['cell_type_lvl1'] = adata.obs['leiden_res_0.02'].map({"0": "Lymphocytes", "1": "Monocytes", "2": "B Cells", "3": "Erythroid", "4": "Erythroid"})` — a manual look-up from the coarsest Leiden clusters to broad lineages, using the marker-gene evidence referenced in the source. This map is source-defined; clusters 3 and 4 both map to "Erythroid". Every cell receives exactly one label.

### 10. Differential expression per cluster

19. `sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")` — defaults `reference='rest'`, `groups='all'` (i.e., all 17 groups of the leiden_res_0.50 categorical in category order), `n_genes=None` (rank **all** genes in the dataset per group, not just positives), `corr_method='benjamini-hochberg'`, `use_raw=False` (no `.raw` is set; the log-normalized `adata.X` is tested), `layer=None`, `rankby_abs=False`, `tie_correct=False`, `pts=False`. Statistics: Wilcoxon rank-sum z-scores per gene, `pvals` from the z-scores, `pvals_adj` after Benjamini-Hochberg correction, `logfoldchanges` approximated from difference of mean log1p values. Stored in `adata.uns['rank_genes_groups']` as one structured array per field (`names`, `scores`, `pvals_adj`, `pvals`, `logfoldchanges`), each indexed by group; within each group genes appear in descending score order. Parameter record under `adata.uns['rank_genes_groups']['params']`.

### 11. Exports

Serialize exactly these terminal values (no new computation, filtering, or sorting):

20. `cell_clusters_umap.csv` — rows: the 17,041 final cells (one row per cell), index `cell_id` (the unique barcode from step 4); columns in order: `cell_id` (index), `sample`, `leiden`, `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`, `cell_type_lvl1`, `umap_1`, `umap_2` (the latter two from `X_umap` columns 0 and 1). Cluster labels are the string categorical values as stored.
21. `rank_genes_groups_leiden_res_0.50.csv` — the flattened DE table: one row per (group, gene) pair, in the stored group order (groups "0".."16", following the leiden_res_0.50 category ordering) and within each group in the stored rank order (descending score, all genes). Columns in order: `group` (string label), `names` (gene name/unique var name), `scores`, `pvals_adj`, `pvals`, `logfoldchanges` (all numeric; `scores` and `logfoldchanges` as float32 in the stored representation, `pvals`/`pvals_adj` as float64).
22. `rank_genes_groups_params.json` — the stored `params` dict of `rank_genes_groups`, with keys `groupby`, `reference`, `method`, `use_raw`, `layer`, `corr_method` (values `leiden_res_0.50`, `rest`, `wilcoxon`, false, null, `benjamini-hochberg` respectively in the reference run; keep a faithful, JSON-compilable mapping of the stored values).

## Semantics and relationships between outputs

- Output 1 cell identities are the unique barcodes after concatenation and `obs_names_make_unique` (suffix `-1`, `-2` only where the same 10x barcode occurred in both samples — the reference convention).
- `cell_type_lvl1` deterministically follows `leiden_res_0.02` (fixed source-defined map; no re-derivation).
- Output 2 group values ("0".."16") are the `leiden_res_0.50` labels, the same set used to partition cells in output 1; group membership per cell matches output 1 row-wise (one-to-one on cell ids when grouped).
- Output 2 rank ordering is a property of the stored arrays; the reference flattening writes groups as blocks in stored order and retains every gene including negative-score tail entries. The method used by the notebook's `sc.get.rank_genes_groups_df(adata, group="7")` returns the same per-group columns and order for any single group.
- Cluster labels across the columns of output 1 are independent solutions of one shared neighborhood graph: `leiden` (resolution 1, n_iterations=2) predates and is not derived from the others; the `leiden_res_*` columns share the graph and differ only by the resolution/iteration settings above.
- Output 3 identifies the settings under which output 2 was computed; consistency (e.g., groupby equals the leiden_res_0.50 column of output 1, method/model `wilcoxon` vs rest with BH correction) is part of the endpoint agreement to be finalized in validation.

## Constraints

- Solver-side software choice is open (other implementations are allowed) but must reproduce the endpoints above to the tolerances and acceptance rules to be set by later executable validation; using the reference packages/versions is one valid way but not the only allowed one. Broad cross-implementation equality (e.g., of UMAP coordinates or cluster IDs) is **not** promised.
- Execution: CPU only (4 cores, 8 GiB RAM, 10 GiB disk), no network at solve time; both h5 inputs are provided locally at the task-relative paths above. Reference runtime (~148 s) is evidence of feasibility, not a solver budget; solver timeout is 600 s (provisional).
- The comparison rules, tolerances and acceptable variations for grading are **pending executable validation**; this document is a draft reference, not a complete grading contract.
