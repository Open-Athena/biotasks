# Reference task: scanpy "Preprocessing and clustering" endpoints for two bone-marrow 10x samples

*Draft specification. Comparison rules, tolerances and acceptable output variations are pending executable validation and will be part of the final public grading contract before any solving attempt. This draft does not promise that arbitrary scientifically reasonable implementations will be accepted.*

## 1. Scientific objective and input semantics

Reproduce the terminal scientific outcomes of the scanpy tutorial "Preprocessing and clustering" (scverse/scanpy documentation, notebook revision `8c1463d5d97272d5811ad3f4efb57483e23b4c7e`, BSD-3-Clause) applied to two donor samples of bone-marrow mononuclear cells from healthy human donors, measured with the 10x Multiome kit (sample labels `s1d1` and `s1d3`; NeurIPS 2021 openproblems benchmark data, CC BY 4.0). The workflow: read and combine the two samples, compute QC metrics, apply a deliberately permissive cell/gene filter, score doublets per sample (without removing any), preserve raw counts, normalize per cell to median count depth and log1p-transform, select the 2000 most variable genes batch-aware, run PCA, build a nearest-neighbor graph, embed it with UMAP, run Leiden clustering at four resolutions, manually annotate the coarsest partition with broad lineages, and compute one-vs-rest Wilcoxon differentially expressed genes per cluster of the 0.50-resolution partition.

Deliverables: (A) per-cell endpoints — sample of origin, the four Leiden assignments, the manual lineage annotation, and the 2-D UMAP coordinates; (B) per-cluster endpoints — the complete Wilcoxon gene ranking per 0.50-resolution cluster; (C) the recorded run parameters of that DE test.

**Inputs (task-relative paths; verify identity before running):**

- `inputs/s1d1_filtered_feature_bc_matrix.h5` — 10x filtered feature–barcode count matrix for sample `s1d1`; 22,848,647 bytes; md5 `a99285913ea3f3d22600d3d2f8a88e34`; sha256 `322c30a7a4905f7f113472442d4aa2c81a1ad736c86651f6c0b81e5b2ff94ac8`.
- `inputs/s1d3_filtered_feature_bc_matrix.h5` — same format for sample `s1d3`; 20,432,298 bytes; md5 `825f7f7578e3dc0b8955f5a97a402338`; sha256 `ca40b287fac57ac2048f11f56f1b630c7c188718908fc217c6baf2e49bdb1982`.

Each file is a 10x Genomics filtered feature–barcode matrix (HDF5): a cell × gene count matrix with barcode identifiers and feature metadata for one donor sample, as produced by 10x pipelines. `s1d1`/`s1d3` are the sample labels used by the source and by the `sample` output column.

## 2. Pinned reference environment

Python 3.13 (CPython 3.13.x). The reference run resolved, among others: `scanpy==1.12.4`, `anndata==0.13.4`, `pandas==3.0.6`, `numpy==2.5.4`, `scipy==1.18.1`, `scikit-learn==1.9.1`, `umap-learn==0.5.12`, `igraph==1.0.0`, `leidenalg==0.12.0`, `h5py==3.16.0`, `pooch==1.9.0`, `matplotlib==3.11.2`, `seaborn==0.13.2`, `statsmodels==0.15.0`, `scikit-image==0.26.0`, `numba==0.68.0`. The pinned operations at these versions — with their defaults — define the reference behavior of every argument not written explicitly below. A complete resolved-environment record exists for the reference run.

## 3. Ordered reference recipe

The reference mutates a single annotated data matrix (AnnData) step by step. Each step lists the exact operation and version, the explicit source arguments, plain-language purpose and the resulting state. Arguments not listed retain the pinned version's defaults; the named operation at that version is the definition of any omitted behavior.

1. **Load and combine the two samples.** For sample ids in order `s1d1`, `s1d3`, read the matching input with `scanpy.read_10x_h5(<path>)` (scanpy 1.12.4, default arguments) into an AnnData of cells × genes, then apply `AnnData.var_names_make_unique()` (anndata 0.13.4) to disambiguate repeated gene symbols. Combine with `anndata.concat(adatas, label="sample")` (anndata 0.13.4), which stacks the samples along the cell axis and annotates each cell's `sample`. Then `AnnData.obs_names_make_unique()` (anndata 0.13.4) makes barcode identifiers unique across the two samples; these identifiers become the `cell_id` values of the per-cell output.
   *Purpose:* one joint count matrix over both donors with unique gene and cell identifiers and sample of origin per cell.

2. **QC gene populations and metrics.** Annotate gene populations exactly as in the source: `adata.var["mt"] = adata.var_names.str.startswith("MT-")` (mitochondrial), `adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL"))` (ribosomal), `adata.var["hb"] = adata.var_names.str.contains("^HB[^(P)]")` (hemoglobin). Then `scanpy.pp.calculate_qc_metrics(adata, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True)` (scanpy 1.12.4): per-cell and per-gene QC metrics including proportions of counts in the three populations, plus log1p variants.
   *Purpose:* QC diagnostics that motivate the fixed thresholds in step 3; not exported.

3. **Permissive filtering.** `scanpy.pp.filter_cells(adata, min_genes=100)` (scanpy 1.12.4) removes cells with fewer than 100 detected genes; then `scanpy.pp.filter_genes(adata, min_cells=3)` (scanpy 1.12.4) removes genes detected in fewer than 3 cells.
   **Every exported endpoint refers to this retained cell population and gene set.** No further cell or gene removal occurs anywhere in the workflow (doublets are scored but never filtered; no cluster is removed).

4. **Doublet detection.** `scanpy.pp.scrublet(adata, batch_key="sample")` (scanpy 1.12.4): Scrublet doublet scoring run separately per sample; adds per-cell doublet diagnostics to `.obs`.
   *Purpose:* quantify likely doublets as a QC diagnostic; the source deliberately leaves doublet removal unexecuted, and these values are not exported endpoints.

5. **Save counts; normalize; log-transform.** `adata.layers["counts"] = adata.X.copy()` preserves the filtered raw counts in a layer; `scanpy.pp.normalize_total(adata)` (scanpy 1.12.4, default `target_sum` — the source's normalization to the median count depth) scales each cell to a common count depth; `scanpy.pp.log1p(adata)` (scanpy 1.12.4) log-transforms in place.
   *Purpose:* `adata.X` becomes the log1p-normalized expression matrix consumed by all later steps.

6. **Feature selection.** `scanpy.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")` (scanpy 1.12.4): annotate the 2000 most variable genes, selected jointly across the two samples (batch-aware), with that version's default selection flavor.
   *Purpose:* the HVG annotation steers the PCA representation (step 7); no genes are removed from the data here.

7. **Dimensionality reduction.** `scanpy.tl.pca(adata)` (scanpy 1.12.4, default arguments): principal component analysis of the log-normalized data, computed on the highly variable genes when the annotation is present (that version's default).
   *Purpose:* capture the main axes of variation and denoise for the neighbor graph.

8. **Nearest-neighbor graph.** `scanpy.pp.neighbors(adata)` (scanpy 1.12.4, default arguments): k-nearest-neighbor graph of cells computed from the PCA representation.
   *Purpose:* the shared substrate for the embedding and all clusterings.

9. **UMAP embedding.** `scanpy.tl.umap(adata)` (scanpy 1.12.4, default arguments, including the version's default random state): 2-dimensional UMAP embedding of that graph, stored as `adata.obsm["X_umap"]`; these are the `umap_1`/`umap_2` values of the per-cell output.

10. **Leiden clustering — four resolutions over the same graph.**
    - `scanpy.tl.leiden(adata, flavor="igraph", n_iterations=2)` (scanpy 1.12.4): resolution omitted, retaining that version's default; assignment stored in `adata.obs["leiden"]`.
    - Then for `res` in `[0.02, 0.5, 2.0]` in that order: `scanpy.tl.leiden(adata, key_added=f"leiden_res_{res:4.2f}", resolution=res, flavor="igraph")` — note `n_iterations` is not passed in these calls, so the pinned version's default applies; the format produces the obs columns `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`.
    *Purpose:* community detection over the cell–cell neighbor graph at four granularity settings; the coarsest result is annotated in step 11 and the 0.50-resolution result is the unit of the DE test in step 12. Cluster labels are algorithm-generated shorthand integer-like strings (a reference label convention), not biological identifiers.

11. **Manual broad-lineage annotation (source literal constant).**
    `adata.obs["cell_type_lvl1"] = adata.obs["leiden_res_0.02"].map({"0": "Lymphocytes", "1": "Monocytes", "2": "B Cells", "3": "Erythroid", "4": "Erythroid"})`.
    *Purpose:* the tutorial author's manual annotation of the coarsest clustering by broad lineage (the two erythroid clusters share one lineage label). The map is applied verbatim; a `leiden_res_0.02` label outside these keys leaves that cell unlabeled. Whether the reference clustering's coarsest labels are fully covered by this map is a coverage property for validation to settle — do not invent labels for unmapped clusters.

12. **Differential expression per cluster.** `scanpy.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")` (scanpy 1.12.4; other arguments at that version's defaults: each cluster tested against all remaining cells, Benjamini–Hochberg correction, computed on the log-normalized `adata.X`). Ranks all analyzed genes for every cluster and stores one leaderboard per cluster with fields `names`, `scores`, `pvals`, `pvals_adj`, `logfoldchanges`, plus the run parameters (themselves exported as endpoint C).
    *Purpose:* per-cluster marker genes used to interpret the 0.50-resolution clusters as cell types.

13. **Plot calls (non-graded).** The source renders diagnostic figures (QC violins/scatter, HVG, PCA variance/components, UMAP, marker-gene dotplots, DE dotplots); the marker-gene sets behind the dotplots are prior knowledge, not computed results. Plot calls produce no exported values and do not feed the endpoints (one dotplot call additionally caches a cluster dendrogram in `.uns` that no export reads). Reproducing figures is not required.

## 4. Required outputs and schemas (cardinalities symbolic, not measured)

### A. `cell_clusters_umap.csv` — per-cell endpoints

Format: UTF-8, comma-separated CSV with one header row; the per-cell index is written as the first column, named `cell_id`.

Row identity: **one row per retained cell** (the population after step 3), keyed by `cell_id` (the unique barcode identifier formed in step 1). Row order: the stored order of the combined dataset (all `s1d1` cells in input order, then all `s1d3` cells).

Columns, in order:
- `cell_id` — unique cell identifier (string; stable identity of the row).
- `sample` — one of the source-defined sample labels `"s1d1"` / `"s1d3"`.
- `leiden` — Leiden cluster label from the default-resolution run (step 10, first call).
- `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00` — Leiden cluster label at each annotation resolution; each column labels the same cell set over the same graph.
- `cell_type_lvl1` — broad-lineage label from the literal step-11 map over `leiden_res_0.02`; unlabeled if that cluster label is not in the map.
- `umap_1`, `umap_2` — the two UMAP coordinates (float; embedding units without physical interpretation).

The cluster/lineage columns are string-valued; each partitions the row set (exactly one label per cell per column). Per-label cell counts are derivable but not separately exported.

### B. `rank_genes_groups_leiden_res_0.50.csv` — per-cluster DE endpoints

Format: UTF-8, comma-separated CSV with one header row; no index column.

Row identity: **one row per (cluster of the 0.50-resolution solution, gene)**. The stored leaderboard ranks every analyzed gene within every cluster, so cardinality = (number of `leiden_res_0.50` clusters) × (number of genes retained after step 3). Rows of the same cluster are consecutive.

Row order: the stored group order (the cluster-category order recorded by scanpy); within each group, the stored rank order (descending score) as computed.

Columns, in order:
- `group` — the `leiden_res_0.50` cluster label; the set of `group` values equals the set of labels present in the `leiden_res_0.50` column of file A (identical reference label convention; label-set identity only — **not** row-count or per-group-population identity).
- `names` — gene identifier (`var_names` after step-1 make-unique processing).
- `scores` — signed Wilcoxon rank-sum statistic for that gene in that cluster vs the rest (float, dimensionless).
- `pvals_adj` — Benjamini–Hochberg-adjusted p-value within that cluster-vs-rest comparison (float in [0, 1]).
- `pvals` — unadjusted p-value (float in [0, 1]). Very small raw and adjusted values may be recorded as exactly `0` (floating-point underflow) — a representation property, not absence of signal.
- `logfoldchanges` — log fold change of mean expression, that cluster vs the rest (float, log2 scale).

### C. `rank_genes_groups_params.json` — DE run context

Format: JSON object (flat mapping). Contents: the run parameters stored by `scanpy.tl.rank_genes_groups` for the step-12 call — identification of which clustering and test produced file B; no measurements. For this call the pinned-version parameters record: `groupby` `"leiden_res_0.50"`, `reference` `"rest"`, `method` `"wilcoxon"`, `use_raw` `false`, `layer` `null`, `corr_method` `"benjamini-hochberg"` (source-documented arguments and recorded defaults, i.e. constants rather than results).

## 5. Execution constraints, software choice and grading status

- Sandbox: 4 CPUs, 8 GiB RAM, 10 GiB disk, no GPU; solver runs offline (no network).
- Time budgets: solver 600 s (provisional), verifier 120 s. Reference-run time and memory do not set solver limits.
- Software choice is open: any implementation whose outputs satisfy the final validated public contract is acceptable; the scanpy 1.12.4 stack is the pinned reference, not a requirement. No claim is made here that alternative implementations or scientifically reasonable variants are automatically accepted — the later validation stage defines what is accepted (including tolerances, label-convention handling and comparison rules).
- This is a draft, not a complete grading contract: comparison rules, tolerances and acceptable variations are pending executable validation.
