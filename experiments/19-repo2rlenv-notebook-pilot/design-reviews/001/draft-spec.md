## Task
Perform quality control, filtering, and normalization of the 3k PBMC single-cell RNA-seq count matrix, producing per-cell QC metrics and a normalized log-transformed matrix.

## Agent-Visible Task Brief
**Goal**: Reproduce the QC and normalization portion of the Scanpy PBMC3k legacy workflow: load the raw 10x count matrix, compute per-cell QC metrics including mitochondrial content, filter low-quality cells and rarely-detected genes, then library-size normalize to 10,000 counts per cell and apply log1p.

**Inputs**: The 10x Genomics PBMC3k filtered gene-barcode matrix, staged at `/input/data/filtered_gene_bc_matrices/hg19/` containing `matrix.mtx`, `barcodes.tsv`, and `genes.tsv` (Matrix Market format, hg19 gene symbols). This is real data: 2,700 cells × 32,738 genes from a healthy donor. Full original source: https://cf.10xgenomics.com/samples/cell/pbmc3k/pbmc3k_filtered_gene_bc_matrices.tar.gz with sha256 `847d6ebd9a1ec9a768f2be7e40ca42cbfe75ebeb6d76a4c24167041699dc28b5` (CC-BY-4.0, 10x Genomics).

**Methodology**:
1. Read the count matrix with gene symbols as variable names; make variable names unique. Work with raw integer counts.
2. Per-gene filtering (before cell QC): keep genes detected (count > 0) in at least 3 cells.
3. Compute per-cell QC metrics on the gene-filtered matrix: `n_genes_by_counts` (number of genes with nonzero counts), `total_counts`, and `pct_counts_mt` where mitochondrial genes are those whose gene symbol starts with `MT-`.
4. Per-cell filtering: keep cells with 200 < `n_genes_by_counts` < 2500 AND `pct_counts_mt` < 5.
5. Preserve the filtered raw counts (e.g., in a layer or separate matrix).
6. Normalize each cell to a total of 10,000 counts (divide by library size, multiply by 10,000).
7. Apply log1p to the normalized values.

Tolerances: normalization is exact arithmetic up to floating-point; per-cell normalized totals after log-transform verification should equal log(10000) to within 1e-4 for every retained cell. QC counts are integers and must match exactly.

**Acceptance Criteria**:
- Output file `/output/normalized.h5ad`: AnnData (h5ad) with the filtered cells × filtered genes, `.X` (or a clearly named layer) containing log1p-normalized values, and a layer or slot named `counts` containing the filtered raw counts.
- `/output/cell_qc.csv`: CSV with one row per retained cell (barcodes as an index or first column named `barcode`), columns `n_genes_by_counts`, `total_counts`, `pct_counts_mt` — QC values computed on the gene-filtered matrix before cell filtering.
- `/output/summary.json`: JSON with keys `n_cells` (after filtering), `n_genes` (after filtering), `n_cells_before_filter` (cells passing gene filter of min 200 genes — note the gene-filtered matrix initially has no cells below 200 genes), `n_mito_genes` (number of genes with `MT-` prefix among retained genes), `mean_total_counts` (raw counts, retained cells, 1 decimal place).

**Environment Constraints**: Offline, CPU-only, 4 vCPUs / 8 GiB RAM; wall-clock limit 600 seconds (the analysis itself runs in well under a minute with scanpy or scipy). No network access at solve or grading time.

**Visible Paths**: Input `/input/data/filtered_gene_bc_matrices/hg19/`; outputs go to `/output/` (create if absent).

## Builder-Only Notes
Reference implementation: scanpy workflow per the source notebook up to and including `sc.pp.log1p` (cells 9, 12, 18, 21, 27, 30, 32). Expected reference values (builder must verify by running the reference solution at build time, not trust these blindly): after `min_cells=3` gene filtering, n_obs=2700, n_vars≈13714 (Seurat-tutorial value; check exact); after cell filtering with 200<n_genes<2500 and pct_mt<5, n_obs≈2638. The 10x matrix uses hg19 gene symbols; note the matrix file may be gzipped (`matrix.mtx.gz`) depending on the archive version — the builder must verify the actual filenames during staging and adapt reader settings. `sc.pp.calculate_qc_metrics` with `qc_vars=['mt']`, `percent_top=None`, `log1p=False` gives the required obs columns. Keep reference h5ad and expected QC CSV as private grading assets outside solver-visible paths.

**Dependency Chain**: count loading → gene filter → QC metrics (on gene-filtered matrix) → cell filter → raw counts layer → normalize_total → log1p → outputs. Each step depends on the previous; cell filtering must happen after QC computation.

**Unresolved Questions**: (1) exact gene count after `min_cells=3` filtering (approx. 13,714 expected from Seurat/scanpy tutorials — builder must confirm from actual data); (2) whether the staged matrix files are gzip-compressed (archive contents should be inspected at build time); (3) exact retained cell count (approx. 2638) — builder must recompute, since scanpy version differences could shift edge cases.

## Instructions
The builder stages the 10x archive, verifies the sha256, unpacks to `/input/data/filtered_gene_bc_matrices/hg19/`, installs scanpy/anndata (or verifies an equivalent scipy+pandas path works), writes `instruction.md` and `task.toml` implementing the contract above, produces a reference solution using scanpy, saves reference outputs privately, and writes pytest-based grading tests per the testing section. Builder must run the reference solution and record the exact values in private expected files.

## Source Context
Source: scanpy tutorial `clustering-2017.ipynb` at commit 8c1463d5d97272d5811ad3f4efb57483e23b4c7e (BSD-3-Clause). The design uses cells 9–32 (reading, `var_names_make_unique`, `filter_cells min_genes=200` — a no-op here, `filter_genes min_cells=3`, `calculate_qc_metrics` with `mt` annotation, cell QC slicing with 200<n_genes<2500 and pct_counts_mt<5, `layers['counts']`, `normalize_total target_sum=1e4`, `log1p`). Per controller scope, downstream HVG selection, PCA, neighbors, UMAP, clustering and marker discovery are excluded. No input reduction needed: the full archive is 7.6 MB compressed, well within budget. Data license CC-BY-4.0 with 10x Genomics attribution.

## Environment Setup
Debian base, Python 3.12, plus `scanpy`, `anndata`, `numpy`, `pandas`, `scipy`, `pytest` via uv/pip at build time. Stage the 10x tarball (url above, sha256 `847d6ebd9a1ec9a768f2be7e40ca42cbfe75ebeb6d76a4c24167041699dc28b5`), verify checksum, extract into `/input/data/filtered_gene_bc_matrices/`. No solver-time network. Reference outputs and expected-value files stored under a private grading directory not mounted for the solver.

## Reasoning Steps Required
1. Load the 10x mtx directory into a cell×gene count matrix with gene-symbol variables; deduplicate variable names.
2. Filter genes detected in <3 cells.
3. Compute per-cell QC: gene count, total counts, mitochondrial percentage (`MT-` prefix).
4. Filter cells to 200 < n_genes < 2500 and pct_mt < 5.
5. Keep filtered raw counts separate.
6. Scale each cell to 10,000 total counts; log1p.
7. Write h5ad, QC CSV, and summary JSON to `/output/`.

## Testing
1. `test_shapes`: h5ad has expected number of cells and genes matching private reference (exact integers).
2. `test_qc_csv_rowcount`: cell_qc.csv row count equals `n_cells` in summary.json and h5ad n_obs.
3. `test_qc_values`: QC columns computed on gene-filtered matrix match private reference CSV exactly (integer counts) and pct_counts_mt within 1e-6.
4. `test_filtering_bounds`: every retained cell satisfies n_genesby_counts in (200, 2500) and pct_mt < 5 (recomputed from the counts layer — catches unfiltered submissions).
5. `test_gene_filter`: every gene in output has nonzero counts in ≥3 cells (recomputed from counts layer).
6. `test_normalization`: for every retained cell, sum of expm1(X) ≈ 10,000 within 0.5 (i.e., pre-log normalized totals equal 10,000); all values finite and ≥0.
7. `test_log_transform`: spot-check a deterministic sample of (barcode's, gene's) X values against reference h5ad within 1e-5.
8. `test_counts_layer_preserved`: counts layer matches raw integers from the original matrix for the retained cell/gene subset (spot-check via scipy.io.mmread against input, within 0 tolerance).
9. `test_mean_total_counts`: summary.json means match reference within 0.1.
10. `test_invalid_submission_fails`: a submission that skips cell filtering (keeps all 2700 cells) or skips log1p must fail via tests 1/6.
Valid alternative implementations (pure scipy+pandas, no scanpy) pass because tests grade artifacts, not code.

## Difficulty
easy: a linear, well-documented pipeline on a small public dataset; the main challenge is faithfully applying the exact filter ordering and thresholds and matching output formats.

## Core Skills Tested
Single-cell RNA-seq preprocessing, QC metric computation, mitochondrial-content filtering, library-size normalization, log transformation, AnnData/h5ad handling, reproducible scientific data analysis.

## Key Technologies
scanpy + anndata (installed, suggested); scipy.io / pandas for matrix reading are permitted alternatives — the methodology, not the package, is required.

## External Resources
Source notebook: https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering-2017.ipynb (BSD-3-Clause). Dataset: https://cf.10xgenomics.com/samples/cell/pbmc3k/pbmc3k_filtered_gene_bc_matrices.tar.gz (sha256 847d6ebd9a1ec9a768f2be7e40ca42cbfe75ebeb6d76a4c24167041699dc28b5, CC-BY-4.0). No other external resources needed; all data must be staged at build time.