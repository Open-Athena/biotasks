# Public task brief — Reproduce the scanpy "Preprocessing and clustering" workflow

## 1. Scientific objective

Reproduce, from the two raw 10x Genomics filtered feature–barcode matrices of the NeurIPS 2021 bone-marrow benchmark dataset, the complete preprocessing-and-clustering analysis of the scanpy tutorial (scverse/scanpy, docs/tutorials/basics/clustering.ipynb at revision 8c1463d5): quality-control annotation, permissive filtering, doublet scoring, median-count normalization with log1p, batch-aware feature selection, PCA, kNN graph construction, UMAP embedding, Leiden clustering at four resolutions, manual broad-lineage annotation of the coarsest solution, and per-cluster Wilcoxon differential expression. The graded deliverables are the per-cell clustering/annotation/embedding table, the per-cluster ranked gene table, and the DE run parameters.

Every stochastic step is seeded (seed 0). A faithful implementation is deterministic; the comparison rules in §5 additionally cover benign numerical variation.

## 2. Inputs

Two binary files (task-relative; packaging assigns their root):

- `s1d1_filtered_feature_bc_matrix.h5` — 22,848,647 bytes, provider md5 `a99285913ea3f3d22600d3d2f8a88e34`
- `s1d3_filtered_feature_bc_matrix.h5` — 20,432,298 bytes, provider md5 `825f7f7578e3dc0b8955f5a97a402338`

Both are 10x v3 HDF5 filtered matrices (datasets `matrix/{data,indices,indptr,shape}`, `matrix/barcodes`, `matrix/features/{name,id,feature_type}`). Sample identities: the file whose name starts `s1d1` is sample `s1d1`; the other is sample `s1d3`. The **processing order s1d1 before s1d3 is fixed** and matters for cell identifiers and row order.

Inputs are read-only; no network access is available or required. Do not use any precomputed intermediate (neighbor graph, embedding, HVG set, cluster solution) — the full pipeline from these two files must be executed.

The reference implementation uses scanpy 1.12.4 (with anndata 0.13.4, igraph 1.0.0, umap-learn 0.5.12, scikit-learn 1.9.1) on CPython 3.13; any conforming software stack is allowed. The algorithmic statements below anchor the semantics; where a step says "the reference computes X", reproducing X (by any means that matches these definitions within the tolerances) is what is graded.

## 3. Analysis procedure

**Step 1 — Read (per sample, s1d1 first).** Build a cells × genes CSR integer count matrix from `matrix/{data,indices,indptr,shape}` (rows = barcodes, in stored order; columns = `features/name`, in stored order). Keep only features whose `feature_type` equals `"Gene Expression"`. Then make gene names unique: scanning left to right, the first occurrence of a name is kept; every later duplicate of name `G` becomes `G-1`, `G-2`, …, skipping any name already present in the (growing) index.

**Step 2 — Concatenate.** Vertically stack s1d1's cells above s1d3's cells, aligning genes by name (intersection; both files share the same feature panel, genes are keyed by name and their column order is an internal detail). Add an observation column `sample` holding `s1d1`/`s1d3` (a categorical whose category order is s1d1, s1d3). Then make cell (barcode) names unique with the same rule as Step 1: the s1d1 copy of a barcode duplicated across the two samples keeps the barcode; the s1d3 copy becomes `<barcode>-1` (or the next free suffix). These deduplicated barcode strings are the permanent cell identifiers (`cell_id`) used in the output; they are unique and must not be collapsed.

**Step 3 — QC annotation (diagnostic; executes but is not graded).** From the raw counts compute the scater-style QC metrics: per cell, total counts; number of genes with positive counts; cumulative share of counts in the 50/100/200/500 most-expressed genes; and the proportion of counts in three gene sets, plus the natural-log `log1p` transforms of the count-based quantities; per gene, number of cells with positive counts and total counts plus `log1p` transforms. The gene-set flags are defined on the deduplicated gene names: `mt` = name starts with `"MT-"`; `ribo` = name starts with `"RPS"` or `"RPL"`; `hb` = name contains a match of the regular expression `^HB[^(P)]`.

**Step 4 — Permissive filtering.** (a) Keep cells with **≥ 100 genes having positive counts** (recomputed directly from the current matrix, not from the QC columns). (b) Then, on the surviving cells, keep genes with **positive counts in ≥ 3 cells** (recomputed after (a)). The order (cells, then genes) is fixed; both operations preserve order.

**Step 5 — Doublet detection (diagnostic; executes but is not graded).** Run Scrublet-style detection **independently within each sample**, with the reference defaults: `sim_doublet_ratio=2.0` synthetic doublets per observed cell (raw counts of random cell pairs summed; UMI subsampling rate 1.0), `expected_doublet_rate=0.05` (stdev 0.02), seed 0. Internal per-batch preprocessing (all on a copy): drop genes expressed in <3 cells of the batch and cells expressing <3 genes; total-count normalize; select highly variable genes of the batch with the Seurat flavor defaults (`min_mean 0.0125`, `max_mean 3`, `min_disp 0.5`, `max_disp ∞`, 20 mean bins); normalize both observed and simulated matrices to totals of 1e6; z-score genes (mean-center and unit variance); embed with 30-component PCA (seed 0); score each observed cell by the kNN classifier with `round(0.5·sqrt(n_obs))` neighbors; threshold automatically at the minimum between the two modes of the simulated-score histogram. Per cell, store `doublet_score` (float) and `predicted_doublet` (boolean) in `obs`. This step must not change the cell set, gene set or expression matrix — the notebook never filters on its outputs.

**Step 6 — Keep raw counts.** Retain a copy of the filtered raw count matrix as internal layer `counts` (internal; not exported).

**Step 7 — Normalization.** Size-factor normalization with the median total count as target: let `t` = median over cells of the cell's total counts (the reference computes it over cells with non-zero totals, which is all cells here); divide every entry of a cell by (its total)/`t`. Then `log1p` with the natural logarithm: `x → ln(x+1)` (no change of base).

**Step 8 — Feature selection (batch-aware, Seurat flavor, top 2000).** Per sample, on the log1p matrix: exponentiate back to the count scale (`expm1`), compute per-gene mean `m` and sample variance `v` (ddof = 1); set `m=1e-12` where `m=0` and treat zero dispersions as missing; dispersion `d = v/m`; take `ln(d)` and `mean' = ln(1+m)`. Genes with no positive count in the batch are excluded from the statistics and re-added afterwards with means, dispersions and normalized dispersions of 0 and not highly variable. Bin the remaining genes by `mean'` into 20 equal-width bins; within each bin normalize: `z = (ln d − mean_bin)/std_bin`; a bin containing a single gene gets `z = 1` (its std is treated as its bin mean and the bin mean as 0). A gene is highly variable in that batch if it is among the batch's top-2000 by `z` (the cutoff value is inclusive: `z ≥` the 2000th-highest value). Merge batches: for each gene average its per-batch means, dispersions and normalized dispersions (zero-fills from unexpressed batches included) and count `nb` = number of batches in which it was highly variable; sort genes by (`nb` descending, averaged normalized dispersion descending, missing values last) and mark the top 2000 overall as `highly_variable`.

**Step 9 — PCA.** Compute a zero-centered PCA of the log1p matrix restricted to the 2000 highly-variable genes, retaining **50 components** (seed 0; the reference uses an ARPACK-style solver on the sparse matrix; the sign convention of each component is arbitrary). Keep the 50-dimensional cell scores.

**Step 10 — Neighbor graph.** For each cell find its **15 nearest neighbors by euclidean distance in the 50-dimensional PCA score space** (the reference uses an approximate search: `n_trees = min(64, 5 + round(sqrt(n_cells)/20))`, `n_iters = max(5, round(log2(n_cells)))`, seed 0 — the neighbor sets must match a 15-NN euclidean search in that space). From the kNN indices and distances build the weighted, symmetrized connectivity graph with UMAP's fuzzy-simplicial-set construction: per-cell smooth distance (local connectivity 1), local membership strengths, and a fuzzy union of the per-cell graphs (set-op mix ratio 1).

**Step 11 — UMAP.** Embed this graph in 2 dimensions with UMAP: spectral initialization on the graph, `min_dist 0.5`, `spread 1.0` (curve parameters from `find_ab_params(spread=1.0, min_dist=0.5)`), initial learning rate 1.0, repulsion strength 1.0, negative sampling rate 5, **200 epochs** (the reference uses 200 epochs when the dataset has more than 10,000 cells), RNG seed 0. The result is the two per-cell coordinates `umap_1`, `umap_2`.

**Step 12 — Leiden clustering (modularity objective).** Cluster the weighted undirected connectivity graph with the Leiden algorithm maximizing modularity, with the resolution normalized by the graph's total edge weight and refinement randomness `beta = 0.01`, RNG seed 0, using the graph's edge weights:

- (a) default solution stored as `leiden`: resolution **1.0**, **2 iterations**;
- (b) three further solutions, each **iterated until stable** (no iteration cap): resolutions **0.02, 0.5, 2.0**, stored as `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00` (two-decimal formatting).

Community ids are made contiguous (in the reference, renumbered in order of first appearance when scanning the cells in analysis order) and rendered as decimal strings `"0"`, `"1"`, …; each column is a categorical whose category order is the natural (numeric-string) sort of the labels.

**Step 13 — Manual broad-lineage annotation.** Annotate the coarsest solution with the notebook's fixed dictionary applied to `leiden_res_0.02`:

```
"0": "Lymphocytes", "1": "Monocytes", "2": "B Cells", "3": "Erythroid", "4": "Erythroid"
```

A cell whose `leiden_res_0.02` label is not in the dictionary receives no lineage (missing value). The dictionary is part of the source; do not substitute another mapping.

**Step 14 — Differential expression (Wilcoxon, one-vs-rest).** For every category `g` of `leiden_res_0.50` and every gene retained after Step 4 (all genes; the raw count layer is not used; the log1p values are used):

- score: pool all cells and rank the gene's log1p values (average ranks for ties); `W` = sum of the ranks of `g`'s cells; with `n` cells in total and `n_g` cells in `g`, `z = (W − n_g(n+1)/2) / sqrt(n_g(n−n_g)(n+1)/12)` (no tie correction), with `z → 0` where undefined;
- `pvals` = `2·(1 − Φ(|z|))` (two-sided normal approximation), undefined values set to 1;
- `pvals_adj` = Benjamini–Hochberg adjusted p-value over all genes **within the group**;
- `logfoldchanges` = `log2( (expm1(mean of log1p values in g) + 1e−9) / (expm1(mean of log1p values in the rest) + 1e−9) )`, where "rest" is every cell not in `g`.

Within each group the genes are listed in **descending order of score**; the order among genes with exactly equal scores is arbitrary.

## 4. Required output files

Write these three files to the run's designated output directory.

**4.1 `cell_clusters_umap.csv`** — one row per cell, header exactly:

```
cell_id,sample,leiden,leiden_res_0.02,leiden_res_0.50,leiden_res_2.00,cell_type_lvl1,umap_1,umap_2
```

- `cell_id`: the deduplicated barcode string of Step 2 (the row key; unique);
- `sample`: `s1d1` or `s1d3`;
- the four cluster columns: decimal-string cluster labels as computed in Step 12;
- `cell_type_lvl1`: the lineage string from Step 13;
- `umap_1`, `umap_2`: floating-point coordinates from Step 11.

Any row order is accepted (grading joins on `cell_id`); any float text formatting is accepted (values are parsed as numbers).

**4.2 `rank_genes_groups_leiden_res_0.50.csv`** — one row per (group, gene), header exactly:

```
group,names,scores,pvals_adj,pvals,logfoldchanges
```

- `group`: the `leiden_res_0.50` label of the cluster the row belongs to;
- `names`: the gene name (deduplicated name of Step 1);
- `scores`, `pvals`, `pvals_adj`, `logfoldchanges`: the Step 14 values. All genes of the filtered matrix appear exactly once per group; rows within a group are in non-increasing `scores` order (ties in any order); group blocks may appear in any order (rows are keyed by (`group`, `names`), which is unique).

**4.3 `rank_genes_groups_params.json`** — the run parameters of the DE test, with exactly these six fields and values:

```json
{"groupby": "leiden_res_0.50", "reference": "rest", "method": "wilcoxon", "use_raw": false, "layer": null, "corr_method": "benjamini-hochberg"}
```

## 5. Identity, alignment and equivalence rules

These rules define what counts as the same scientific result; they are the only equivalences applied.

- **Cell identity.** Rows of 4.1 are keyed by `cell_id`. The deduplication suffix rule of Steps 1-2 is part of the identity: a barcode present in both samples appears twice (once unsuffixed under `s1d1`, once suffixed under `s1d3`). The `sample` column must match the reference per cell.
- **Cluster labels are arbitrary; partitions are not.** For each of the four cluster columns and for the `group` column of 4.2, the grader may align labels by a bijection (optimal matching of the cell partitions) before comparing. The bijection used for `group` must be the one used for `leiden_res_0.50` (the DE groups are the clusters of that column). After alignment, cell membership in every cluster must match exactly.
- **`cell_type_lvl1` is a per-cell annotation, not a label-keyed value.** It is compared per cell against the reference lineage values and is **not** remapped by any label bijection. Consequence, worked through: if a solution's `leiden_res_0.02` numbering differs from the reference's, the fixed dictionary of Step 13 assigns different lineages to cells, and the annotation will not match — so a conforming run reproduces the reference numbering for the coarsest solution (the pipeline is seeded and deterministic). The accepted relabeling of a correct result renames cluster labels while leaving each cell's lineage, sample, coordinates and the (group, gene) DE rows unchanged; re-applying the Step 13 dictionary to renamed labels is not an accepted transformation.
- **UMAP coordinates are defined up to a similarity transform of the plane.** The grader first finds the optimal similarity alignment (translation, rotation, optional reflection, single positive scale factor) of the submitted coordinates to the reference coordinates; the residual after that alignment must be within a fixed tolerance. Absolute orientation, position and scale of the embedding are therefore not graded.
- **Numerical tolerances.** Scores, p-values, log-fold changes and the aligned UMAP residual are compared with fixed numeric tolerances (`τ_score`, `τ_p`, `τ_lfc`, `τ_umap`); the released task states these values. Conforming outputs are expected to agree to floating-point accuracy; the tolerances exist only to absorb benign numerical variation, not different methods.
- **Nothing else is equivalent**: different filtering thresholds, normalization targets, neighborhood sizes, HVG selections, resolutions, iteration counts, objectives, DE methods or corrections produce wrong answers.

## 6. Determinism, seeds and resources

- Every stochastic step uses seed 0 (doublet simulation, approximate kNN, PCA, UMAP, Leiden RNG). Do not vary seeds.
- Resource envelope: 4 CPUs, 8 GiB memory, no GPU, 600 s wall-clock, offline.
- The reference run completed within these limits; your runtime need not match it, only the budget.

## 7. What is not part of the contract

- Plots (violin, scatter, HVG, PCA, UMAP, dotplots) and the marker-gene dictionary: the notebook renders them, but they store no values that any endpoint depends on. Executing them (headless) is allowed but optional.
- The QC metric columns (Step 3), doublet scores (Step 5), the raw-count layer, HVG flags, PCA scores/loadings and the neighbor graph are internal: their values are not exported and are not compared directly; they are graded only through their effect on the endpoints.
- `sc.get.rank_genes_groups_df(adata, group="7")` and the top-5 gene list are views of the 4.2 table and are not separate outputs.
