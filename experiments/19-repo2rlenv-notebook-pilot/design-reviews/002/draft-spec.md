# Preprocessing, clustering and marker-based annotation of bone marrow scRNA-seq

## Task
Run a scanpy-style preprocessing and clustering workflow on 10X bone marrow mononuclear cell data, then identify the NK-cell cluster via Wilcoxon differential expression and report its defining markers.

## Agent-Visible Task Brief
**Goal**: From raw 10X count matrices, perform QC, filtering, doublet scoring, normalization, HVG selection, dimensionality reduction, Leiden clustering and cluster-level DE testing; produce deterministic tabular outputs and identify which cluster corresponds to NK cells.

**Inputs**:
- `/input/s1d1_filtered_feature_bc_matrix.h5` — 10X Genomics filtered feature-barcode matrix (donor s1d1, bone marrow mononuclear cells, NeurIPS 2021 Open Problems dataset; ~8,000 cells, 36,601 genes; CC BY 4.0).
- `/input/s1d3_filtered_feature_bc_matrix.h5` — second donor sample, same format.
- Gene identifiers are 10X-style symbols; must be made unique before use.

**Methodology** (order matters):
1. Load both samples, concatenate with a `sample` label column (s1d1, s1d3), make obs and var names unique.
2. Annotate gene sets: `mt` = names starting `MT-`; `ribo` = starting `RPS`/`RPL`; `hb` = regex `^HB[^(P)]`. Compute QC metrics with log1p variants (n_genes_by_counts, total_counts, pct_counts_mt, etc.).
3. Permissive filtering: remove cells with < 100 detected genes; remove genes detected in < 3 cells.
4. Doublet detection: Scrublet-style doublet scores with `sample` as batch key (fix random seed to 0). Doublets need not be removed yet.
5. Save raw counts, then normalize to median total counts and apply log1p (log1PF).
6. Select top 2000 highly variable genes, using batch-aware selection keyed on `sample`.
7. PCA on HVG-scaled data (default scanpy behavior acceptable), then kNN graph (10 neighbors) on PCA representation, then UMAP embedding.
8. Leiden clustering with the igraph implementation, `n_iterations=2`, resolution 0.50, seed 0. Optionally also report resolutions 0.02 and 2.00.
9. Wilcoxon rank-genes test (each cluster vs rest) on log-normalized data using the resolution-0.50 labels.
10. Identify the NK-cell cluster: the cluster whose cells show highest mean expression of NKG7 and GNLY (the tutorial identifies cluster 7 as NK via these markers).

**Acceptance Criteria**: All outputs to `/output/`:
- `metrics.json`: JSON with keys `n_cells_initial`, `n_genes_initial`, `n_cells_filtered`, `n_genes_filtered`, `n_doublets_predicted`, `n_hvgs`, `n_pcs`, `n_clusters` (at resolution 0.50), `nk_cluster` (string cluster label).
- `per_cell_qc.csv`: one row per retained cell — columns `obs_name, sample, n_genes_by_counts, total_counts, pct_counts_mt, doublet_score, predicted_doublet, leiden`.
- `deg_nk_cluster.tsv`: top 50 DE genes for the NK cluster — columns `names, scores, pvals_adj, pct_in, pct_out` (pct columns optional).
- `hvg.txt`: the 2000 selected highly variable gene symbols, one per line.
- Numbers must be derived from the real data; tolerances below.

**Environment Constraints**: Offline; CPU-only (4 vCPU, 8 GiB RAM); solve within 10 minutes wall clock. scanpy, anndata, numpy, scipy, pandas, leidenalg, igraph, umap-learn are available in the image. Fixed seeds (0) required for Scrublet, Leiden and UMAP so results are reproducible.

**Visible Paths**: inputs at `/input/*.h5`; all outputs under `/output/` as above.

## Builder-Only Notes
**Reference implementation**: the server notebook workflow, executed exactly as above on both samples. Run at build time to capture reference values: filtered cell/gene counts, doublet count, cluster count at res 0.50, NK cluster label, top-10 DE gene list for the NK cluster, median total counts, PCA variance ratios (PC1/PC2), mean NKG7/GNLY expression per cluster.

**Dependency Chain**: QC → filtering → normalization → HVG → PCA → neighbors → Leiden → DEG → NK identification. Each stage writes into a single AnnData; checkpoint intermediate `n_cells_filtered` etc. so partial failures are diagnosable.

Grading tolerances (justified by cross-implementation variation of HVG/PCA/Leiden):
- `n_cells_filtered`, `n_genes_filtered` within ±1% of reference (these are deterministic given the filter specs).
- `n_clusters` within ±30% of reference or ±2 clusters, whichever is larger (Leiden resolution covers vary with backend choices).
- `nk_cluster` must be a cluster whose mean log1p expression of both NKG7 and GNLY is in the top 2 clusters — grade by recomputing this from `per_cell_qc.csv`… actually grade by checking the submitted `deg_nk_cluster.tsv` contains NKG7 and GNLY among its 25 top genes (this is the scientifically meaningful invariant; the label itself may differ between implementations).
- `pct_counts_mt` values for 20 spot-checked cells within 0.1 percentage points.
- `hvg.txt` allows flexible selection flavor; require ≥1200/2000 overlap with reference list OR a self-consistency check (genes must be from the filtered set and scored as variable under a Seurat-like flavor run by the grader).

**Unresolved Questions**:
- Builder must verify wall-clock: full pipeline on 16k cells × ~21k filtered genes is expected ~3–5 min on 4 vCPU (PCA and neighbors dominate). If it exceeds 6 minutes, fall back to s1d1 only (drop step 1 concatenation; note in the brief) — the tutorial's s1d3 path is not scientifically essential.
- Scrublet with `batch_key` may occasionally fail on tiny simulated-doublet batches; the reference run must confirm it works with seed 0. Fallback: skip doublet step and adjust acceptance criteria (n_doublets absent).
- Provider MD5s were not verified in the input provenance; builder must hash both h5 files at download and record checksums.

## Instructions
1. At build time, download both h5 files from figshare (URLs in provenance), verify MD5 (`a99285913ea3f3d22600d3d2f8a88e34`, `825f7f7578e3dc0b8955f5a97a402338`), stage at `/input/`, make read-only.
2. Install environment: Debian base, Python 3.12, scanpy (≥1.10), anndata, leidenalg, igraph, umap-learn, pooch, pandas, numpy, scipy, pytest.
3. Run reference solution; record all reference values into a private `expected.json` (kept out of `/output` and `/input`).
4. Run test suite against reference to confirm it passes; time the reference and confirm < 8 minutes.
5. Write `instruction.md` from the agent-visible brief and `task.toml`; keep grading in a private pytest module.

## Source Context
Notebook: scanpy basics clustering tutorial (scanpy commit 8c1463d5, BSD-3-Clause). Data: NeurIPS 2021 Open Problems bone marrow samples s1d1/s1d3, DOI 10.6084/m9.figshare.22716739.v1, CC BY 4.0. The tutorial workflow (QC → doublets → log1PF normalization → 2000 HVGs → PCA → neighbors → UMAP → Leiden → Wilcoxon DEG → annotation; NK identified via NKG7/GNLY in cluster 7) is reproduced essentially unchanged. Proposed reductions: possibly s1d1-only if time-limited; marker dotplots and UMAP plots are omitted (not gradeable artifacts); resolution sweep reduced to required 0.50.

## Environment Setup
- Base: `python:3.12-slim` Debian; apt install build-essential, git, jq, sqlite3, tmux, curl; install uv.
- `uv pip install scanpy anndata leidenalg igraph umap-learn pooch pytest pandas numpy scipy`.
- Stage data at build time (network allowed then); solver runs offline. Record sha256 of staged files in build log.
- Ensure `/input` read-only, `/output` writable, grading assets in a non-solver-visible path.

## Reasoning Steps Required
1. Load and concatenate the two 10X matrices. 2. Define mt/ribo/hb gene masks and compute QC metrics. 3. Filter cells (min_genes=100) and genes (min_cells=3). 4. Score doublets per batch. 5. Save counts; normalize (median) + log1p. 6. Select 2000 HVGs batch-aware. 7. PCA → 10-NN graph → UMAP. 8. Leiden (igraph, n_iterations=2, res 0.50, seed 0). 9. Wilcoxon DEG per cluster. 10. Identify NK cluster via NKG7/GNLY and emit outputs.

## Testing
1. **Output contract**: metrics.json exists, is valid JSON with all required keys and integer/string types; missing or null values fail.
2. **Filtering correctness**: `n_cells_filtered`/`n_genes_filtered` within ±1% of reference values.
3. **QC correctness**: recompute `pct_counts_mt` for 20 sampled cells from raw h5s and compare to submitted per_cell_qc.csv within 0.1 pp; rejects fake/manually-plausible submissions.
4. **Filter consistency**: subset of per_cell_qc rows must include every cell passing n_genes≥100 (checked directly against raw data); count matches `n_cells_filtered`.
5. **Clustering sanity**: `n_clusters` between 5 and 15, and within ±2 or ±30% of reference; self-consistency: `leiden` column labels form exactly `n_clusters` groups, all non-empty.
6. **NK identification**: `deg_nk_cluster.tsv` contains NKG7 and GNLY within top 25 genes; `nk_cluster` matches the group with maximal mean doublet… rather: matches the cluster containing the top NKG7-expressing cells (grader recomputes from raw data per submitted cluster assignment).
7. **HVG plausibility**: `hvg.txt` has exactly 2000 unique genes from the filtered gene set; test-selection flexibility: if overlap with reference < 60%, run a grader-side scanpy HVG computation on the submitted normalized matrix and require ≥1200 overlap, so a different valid flavor still passes.
8. **DEG quality**: top-50 scores monotone non-increasing; pvals_adj all ≤ 1.
9. **Negative case**: a submission skipping normalization (raw counts DEG) yields NK-cluster z-scores far from reference — tested via a deliberately wrong reference-run fixture that tests must catch.
10. **Determinism**: run reference twice; cluster count and NK top-10 genes identical.

## Difficulty
medium: a well-documented standard scanpy pipeline; difficulty comes from correct ordering, deterministic seeding, batch-aware HVGs, and scientific interpretation of DEG results rather than from algorithmic invention.

## Core Skills Tested
scRNA-seq preprocessing, AnnData data handling, QC and filtering, normalization, feature selection, graph clustering, Wilcoxon DE testing, marker-based cell type annotation, reproducible scientific scripting.

## Key Technologies
scanpy, anndata, leidenalg/igraph, umap-learn, numpy/scipy/pandas (all installed in image; any equivalent methodology-fulfilling implementation is permitted).

## External Resources
- Notebook: https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering.ipynb (BSD-3-Clause)
- Data: https://ndownloader.figshare.com/files/40347877 and https://ndownloader.figshare.com/files/40347880 (DOI 10.6084/m9.figshare.22716739.v1, CC BY 4.0); provider MD5s listed in provenance, to be verified at build time (not yet verified).
- scverse tutorial marker-gene reference: https://www.sc-best-practices.org/cellular_structure/annotation.html