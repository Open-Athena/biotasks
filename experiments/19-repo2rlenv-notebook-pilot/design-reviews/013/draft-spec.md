## Task
Reproduce the scanpy preprocessing-and-clustering workflow for two human bone-marrow 10x samples (s1d1, s1d3), producing a filtered, normalized, batch-annotated, multi-resolution-clustered and coarse-cell-type-labeled AnnData object, plus cluster marker genes from Wilcoxon testing.

## Agent-Visible Task Brief

**Inputs (staged, read-only):** `/data/s1d1_filtered_feature_bc_matrix.h5`, `/data/s3d1..` → exactly `/data/s1d1_filtered_feature_bc_matrix.h5` and `/data/s1d3_filtered_feature_bc_matrix.h5` (bytes from figshare DOI 10.6084/m9.figshare.22716739.v1, CC BY 4.0; provider MD5s a99285913ea3f3d22600d3d2f8a88e34 and 825f7f7578e3dc0b8955f5a97a402338). Original 10x output: ~8,000 cells/sample × 36,601 genes.

**Environment:** CPU-only Debian/Python 3.12, 4 vCPU, 8 GiB RAM, 10 GiB disk; 600 s total solver budget; internet unavailable at solve time. Use any implementable software. All stochastic steps must use `random_state=0` (scrublet, PCA, neighbors, UMAP, leiden). Visualization/plotting is NOT required and is not graded.

**Requirements**

- **S1 Ingest and batch-annotate.** Read each h5 with the 10x reader semantics (gene `var_names_make_unique()`), concatenate with `label="sample"`, make `obs_names` unique. Cells/genes keep the resulting identifier order. Integer counts in `X`.
- **S2 QC metrics.** Annotate `var["mt"]` (`^MT-`), `var["ribo"]` (`^RPS|^RPL`), `var["hb"]` (regex `^HB[^(P)]` substring match). Compute per-cell/per-gene QC metrics for vars `mt,ribo,hb` with `log1p=True` (fields `n_genes_by_counts`, `total_counts`, `pct_counts_*`, `log1p_total_counts`, `log1p_n_genes_by_counts`, per-gene `n_cells_by_counts` etc.).
- **S3 Filtering.** `filter_cells(min_genes=100)` then `filter_genes(min_cells=3)` (whole dataset, not per sample; per-sample QC is out of scope — see Source Context).
- **S4 Doublet annotation.** Run Scrublet doublet detection with `batch_key="sample"` (simulated doublets per sample; default downstream params), adding `doublet_score` and `predicted_doublet` to `obs`. Do NOT remove cells; annotate only.
- **S5 Normalization.** Store the post-filter integer counts in `layers["counts"]`. Then apply median count-depth scaling (size factor = median post-filter `total_counts`) and log1p ("log1PF"); result in `X`.
- **S6 Feature selection.** Highly variable genes, `n_top_genes=2000`, `batch_key="sample"`, default "seurat" flavor, computed on the log-normalized `X`. Flag genes in `var["highly_variable"]` + accompanying `means/dispersions/dispersions_norm`.
- **S7 PCA.** PCA on the HVG subset of `X`, 50 components in `obsm["X_pca"]`; store variance ratio.
- **S8 Neighborhood graph.** kNN graph from `X_pca`, Euclidean metric, `n_neighbors=15`, all 50 PCs, default UMAP/pynndescent method, `random_state=0`; store `obsp["distances"]` (kNN, self excluded) and `obsp["connectivities"]` (symmetric).
- **S9 UMAP.** 2D UMAP of the graph in `obsm["X_umap"]`, `random_state=0`.
- **S10 Leiden clustering.** Leiden on the S8 graph, igraph flavor, `n_iterations=2`, `random_state=0`, modularity objective, at resolutions 0.02, 0.50, 2.00, stored as categorical strings in keys exactly `leiden_res_0.02`, `leiden_res_0.50`, `leiden_res_2.00`.
- **S11 Level-1 annotation.** Assign each `leiden_res_0.02` cluster one lineage label, written to `obs["cell_type_lvl1"]`: vocabulary {Lymphocytes, Monocytes, B Cells, Erythroid}, using these positive marker panels (mean log-normalized expression per cluster): Erythroid {HBA1, HBB, HBM, GYPA}; Monocytes {FCN1, CD14, CST3}; B Cells {MS4A1, IGHD, IGHM}; Lymphocytes {IL7R, CD247, NKG7, GZMK, CD8A}. Residual clusters must be absorbed into the best-matching label; every cell carries exactly one label. Record the cluster→label map in `uns` or `summary.json`.
- **S12 Marker DE.** For `leiden_res_0.50`: one-vs-rest Wilcoxon rank-sum (asymptotic, no tie correction) over ALL genes, per cluster; report top 50 genes per cluster by z score.

**Required artifacts**
- **A1 `solution.h5ad`** (AnnData h5ad): `X` sparse log-normalized; `layers["counts"]` integer filtered counts; `obs` = S1 sample, S2 metrics, `doublet_score`, `predicted_doublet`, three leiden keys, `cell_type_lvl1`; `var` = S2 flags/metrics + S6 columns; `obsm` = `X_pca`, `X_umap`; `obsp` = `distances`, `connectivities`; `uns` = `log1p` marker + pipeline seeds/versions. Row/col order = S1 order restricted by S3.
- **A2 `de_markers.csv`**: columns `cluster,rank,gene,score,pval,padj` (cluster = string label, rank 1..50 by descending score); exactly 50 rows per cluster present in `leiden_res_0.50`.
- **A3 `summary.json`**: `n_cells_raw, n_genes_raw, n_cells_filtered, n_genes_filtered, median_total_counts, n_hvg, doublet_rate, cluster_counts` (per resolution, dict label→size), `cell_type_lvl1_counts` (label→size), `random_states`, dependency versions.

**Equivalence rules (public):** cluster/cell-type label strings are arbitrary — graded permutation-invariantly; `X`/`X_pca` float32 vs float64 accepted; PCA component signs may be flipped; UMAP orientation arbitrary (graded by neighborhood-preservation only); categorical vs string dtypes accepted. Any software implementing the stated methods is allowed. Documentation of the chosen implementations must be included (in `summary.json`).

**Numerical tolerances:** exact match for discrete sets (filtered cell/gene ids, HVG flags, DE top-50 gene sets per cluster); deterministic continuous quantities (QC metrics, size factor, log-normalized `X`, Wilcoxon scores) at rtol ≤ 1e-5 vs reference recomputation. Stochastic outputs (doublet scores, UMAP, cluster labels) vs reference: thresholds `tolerance unresolved: construction gates G1–G4` below; the builder publishes the calibrated numbers before release.

## Source Context
Notebook: scanpy `docs/tutorials/basics/clustering.ipynb` @ 8c1463d (BSD-3-Clause, sha256 9716c6e5…0000a6). Data: NeurIPS-2021 openproblems bone-marrow subset, figshare 22716739.v1, CC BY 4.0 (license per figshare API). All pipeline stages S1–S12 follow the notebook's operation order: cells 5 (load/concat), 9–10 (QC), 16 (filter), 18 (scrublet), 22–23 (counts/normalize/log1p), 25 (HVG), 28 (PCA), 34 (neighbors), 36 (UMAP), 41/52 (leiden, igraph flavor, n_iterations=2 as in cell 41), 62 (level-1 map), 67 (Wilcoxon DE). Adaptations: (1) plots (cells 12,14,26,30,32,38,42,45,46,54,60,63,69,73) omitted — line plots/dotplots are inspection aids, not analysis outputs; annotation is instead driven by the marker panels, which are the notebook's cell-59 lists restricted to the four lineages of cell 62. (2) The notebook's hard-coded cluster-number→label map (cell 62) cannot be a contract because cluster numbering is not part of the scientific semantics; the equivalent requirement (assign each coarse cluster its dominant lineage from the same marker panels) preserves semantics. (3) Scrublet: notebook only annotates; we make "annotate, don't filter" explicit (both options discussed in cells 19/45). (4) Seededness (`random_state=0` everywhere) is added because the notebook leaves defaults implicit — scientific effect: pins one draw of these stochastic algorithms. (5) Per-sample QC threshold setting (cell 15 remark) omitted; the whole-dataset permissive filter of cell 16 is used. Provider MD5s are unverified by the supplier (`verification.data_files_downloaded: false`) → build-time gate.

## Environment Setup
Stage via pip/uv: `scanpy`, `anndata`, `numpy`, `scipy`, `pandas`, `leidenalg`, `igraph`, `umap-learn`, `pynndescent`, `h5py`. Download during build from `https://ndownloader.figshare.com/files/40347877` and `/40347880`, verify MD5 against provider values, retry/halt on mismatch (blocking gate: provenance). Pin exact versions used for the reference in a lockfile; record versions. Keep reference pipeline and expected outputs private (not solver-readable). Disk: inputs ~43 MB, solution h5ad (sparse, ~16k×~21k genes, 2 layers) est. < 1 GB — within budget (builder confirms G5).

## Testing
Grading recomputes S1–S3, S5, S6, and S12 independently from the staged h5 inputs with the private reference implementation, then checks the submitted artifacts against that derivation (internal consistency of submitted files alone never suffices).

| Req | Artifact (stage) | Trusted check | Rule | Wrong result rejected |
|---|---|---|---|---|
| S1–S3 | A1 counts layer, ids, A3 counts | reference recompute from raw h5 | exact id-set equality; counts identical (sparse sum + spot-check batch) | skipped `min_cells`/`min_genes` filter, wrong threshold, dropped sample |
| S2 | A1 obs/var metrics | recompute from counts | rtol 1e-5 on every numeric metric; flags exact | wrong gene classes (e.g. `HB[P]` included) |
| S4 | A1 doublet fields | reference scrublet | G1-calibrated score correlation + [0,1] range + plausibly low rate | missing/constant scores |
| S5 | A1 X, A3 size factor | recompute median + log1p | rtol 1e-5 elementwise | CP10k instead of median; log before scaling |
| S6 | A1 HVG flags, A3 n_hvg | reference recompute | G2-calibrated: nominal exact flag match | wrong flavor/no batch_key/n_top≠2000 |
| S7 | A1 X_pca, variance ratio | reference PCA | G3-calibrated; sign-flip invariant; variance ratio rtol 1e-4 | PCA on all genes; unnormalized data |
| S8 | A1 obsp | reference + structure | symmetry of connectivities; degree ≤ 2·(15−1); self excluded; G3-calibrated overlap with reference kNN | empty graph |
| S9 | A1 X_umap | reference | G4: kNN-preservation vs own X_pca kNN (self-computed, permutation/rotation invariant) | random coordinates |
| S10 | A1 leiden cols, A3 sizes | reference clustering | permutation-invariant ARI vs reference, G4-calibrated threshold | permuted labels, single-cluster lumping, wrong resolutions |
| S11 | A1 cell_type_lvl1, A3 counts | reference map + derivation | (a) label-permutation match vs reference (4! search) ≥ G4; (b) independent marker-ordering: for each label L, mean over panel(L) in cells labeled L exceeds the same mean in cells labeled L′ for every L′ | random or swapped lineage labels |
| S12 | A2, A1 uns | recompute Wilcoxon from submitted X+labels | top-50 gene sets exact per cluster; score/pval recomputed rtol 1e-5, ties via published G3 rule | shuffled rows, t-test instead of Wilcoxon, scores not matching submitted data |

Order-independent: every test derives from A1/A2/A3 plus staged inputs only. Sampling bounds: full-matrix comparisons where cheap; S5 sampled rows/cols (1000×1000) with exact row/col sums — misses only errors confined to unsampled entries, which also shift sums. Controls in construction: reference solution (must pass fully), empty-output (must fail all), meaningful-wrong-output variants above (must each be caught by its row).

## Builder-Only Notes
Private assets: pinned-version reference pipeline, its outputs (filtered dimensions, median size factor, doublet rate, cluster sizes, full DE table, obs/var ids), expected A3 numbers, calibration harness. **Construction gates (empirical, blocking; publish results before release):**
- **G0 provenance:** download, MD5-verify both h5 files; on failure halt (seed unsuitable).
- **G1 doublet:** run reference scrublet ≥3× with `random_state=0`; if scores vary, acceptance = Pearson r vs reference and rate within observed spread; calibrate against a corrupted run (wrong batch_key).
- **G2 HVG:** reference exact-match across ≥2 independent conforming runs and ≥1 nearest-incompatible variant (no batch_key); if not exact, publish overlap threshold from observed spread.
- **G3 numeric tolerances:** pairwise same-data reruns (varying BLAS threads) establish per-quantity observed error; set published rtols at ≥10× that spread, verify corrupted variants (target_sum=1e4; permutation of one cluster's counts) are still rejected.
- **G4 stochastic graphs/UMAP/leiden/labels:** seed-resampled correct runs vs reference give the correct-run similarity distribution (ARI, kNN-preservation); label-permuted and lumped outputs give the wrong-run distribution; thresholds must separate the two with margin — if not separable, escalate for design revision (no plausibility fallback).
- **G5 resources:** measure reference runtime on 4 vCPU/8 GiB; require ≤ 480 s and peak RSS ≤ 6 GiB. If exceeded, do NOT drop stages — report and request design revision (candidate: restrict A2 depth or resolution 2.00).
- **G6 determinism:** grading recomputation time must be ≤ reference runtime; no order dependence between tests.
Blocking design questions: none identified at design time.

## Difficulty
Medium — the pipeline is a well-documented standard scanpy workflow with no algorithmic novelty, but correct end-to-end reproduction requires exact handling of operation order, batch-aware steps (scrublet, HVG), seeded stochastic methods, and multiple artifact schemas with permutation-invariant semantics, all under a 600 s CPU-only budget.