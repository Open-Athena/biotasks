## Scope decision (per approved_scope)

Target = the notebook's terminal **marker-gene / differential-expression branch**: `sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")` on the pooled, permissively filtered, log-normalized data, with each cluster tested against the union of all other cells.

- **Excluded** (per approved scope): Leiden cluster discovery, UMAP coordinates, `cell_type_lvl1` transcription, QC diagnostics, scrublet doublet scores, HVG/PCA/neighbors intermediates. Verified from pinned source that these do **not** change the DE inputs: `pp.scrublet` works on `adata_obs = adata.copy()` and writes only `.obs`/`.uns` (`scanpy/preprocessing/_scrublet/__init__.py:190-235, 262-308`); `highly_variable_genes`/`pca`/`neighbors` only annotate `var`/`obsm`/`uns`. Only `filter_cells(min_genes=100)`, `filter_genes(min_cells=3)`, `normalize_total` (default median) and natural `log1p` precede the DE test on `X`.
- **Scope reduction made explicit**: cluster labels are supplied as a fixed derived input (one recorded Leiden-0.50 run), not ground truth; the DE analysis conditional on those groups is substantial and deterministic (no randomness anywhere in the retained branch).
- **Projection**: the endpoint export is the full per-group ranking (398,259 rows). I request a **top-50-per-cluster projection** with all six stored fields. This retains the marker result (the notebook reads the top 5 per cluster) while still forcing full-universe statistics: `pvals_adj` is BH over **all** tested genes per group (`scanpy/tools/_rank_genes_groups.py:613-622` runs `multipletests` on the full p-value array before the top-n selection), so a solver cannot shortcut the correction universe. `n_tested_genes` is additionally reported in a summary JSON, which directly catches gene-universe deviations.

## Measured facts (recorded execution, `trial/result.json`, `output-audit.json`)

- Reference run completed: exit 0, 147.5 s, peak child RSS ≈5.18 GiB (full pipeline incl. plotting) — the DE-only branch is a subset, so the 600 s / 8 GiB solver budget has ample headroom (DE-alone runtime unmeasured).
- Artifacts: `cell_clusters_umap.csv` (17,041 rows: cell_id, sample, leiden, leiden_res_0.02/0.50/2.00, cell_type_lvl1, umap_1, umap_2); `rank_genes_groups_leiden_res_0.50.csv` (398,259 rows = 17 groups × 23,427 genes; columns group/names/scores/pvals_adj/pvals/logfoldchanges); `rank_genes_groups_params.json` = {groupby: leiden_res_0.50, reference: rest, method: wilcoxon, use_raw: false, layer: null, corr_method: benjamini-hochberg}.
- Value ranges: scores [-67.24, 85.90]; log2fc [-29.89, 25.74]; pvals/pvals_adj ∈ [0,1] with exact 0s (underflow at |z| ≳ 38). Sample counts before cell filter: s1d1 8,785, s1d3 8,340.
- Inputs hash-pinned (h5 sha256 322c30a7…, ca40b287…; md5 verified against provider by staging).

## Methodological facts from pinned sources (scanpy 1.12.4 / anndata 0.13.4)

- Wilcoxon convention (`scanpy/tools/_rank_genes_groups.py`): average (mid)ranks incl. ties (47-65); `tie_correct=False` default (671), used as σ = sqrt(n·(N−n)·(N+1)/12) with **no** tie correction and **no** continuity correction (505-535); z = (W − n(N+1)/2)/σ, NaN→0; p = 2·norm.sf(|z|) (533); all genes tested (`n_genes=None` → all, 856-861); ranking by descending score (argpartition/argsort, 37-44); per-group vs **rest = all other cells** (`_stats_vs_rest`, 345-377); BH per group via statsmodels `fdr_bh` (613-622).
- log2fc = log2((expm1(μ_g)+1e-9)/(expm1(μ_rest)+1e-9)), natural expm1, means of the **log-normalized** values (208-211, 624-635). Storage dtypes: scores/log2fc float32, pvals(pvals_adj) float64 (888-899) — CSV values are float32-rounded for scores/log2fc.
- Normalization: `normalize_total` default → target = median of positive per-cell totals (`_normalization.py:20-26, 104-119`); `log1p` natural (`_simple.py:370-381`); counts read as float32 from 10x int32 (`readwrite.py:279-287`).
- Filtering: "detected" = count > 0; keep cell if ≥100 detected genes, then keep gene if detected in ≥3 cells of the cell-filtered matrix (`_simple.py:169-175, 286-292`).
- Identifiers: `read_10x_h5` defaults (gex_only=True, gene-symbol var_names; `readwrite.py:178-215, 273-300`); per-sample `var_names_make_unique` ('-1','-2',… after first occurrence, `anndata/utils.py:226-249`); `ad.concat` inner join on gene indices in dict (sample) order (`anndata/_core/merge.py:1444, 1664-1671, 1709-1711`); `obs_names_make_unique` appends '-1' to later duplicate barcodes.

Equality with scipy's `mannwhitneyu(asymptotic, use_continuity=False)` was checked algebraically (same U/W transform, same variance), so a clean-room implementation is feasible — software independence is real, not nominal.

## Fidelity risks and how the draft handles them

1. **p-value underflow**: reference reports 0.0 for most top markers; the brief states 0-on-underflow and the checker must treat both-underflow as equal (proposal in handoff).
2. **Tie conventions** (tie correction, continuity correction, alternative='two-sided') materially change the statistic → specified in the brief as the definition of the requested statistic, not left implicit; still flagged for executable validation.
3. **Identity conventions** (gene-symbol suffixes, inner-join universe, pooled filtering, natural log1p, median-of-totals target) are given as population/identifier definitions, not as a library transcription.
4. **Boundary ties at rank 50** and tolerance calibration are unmeasured → validation items.
5. One passing reference execution only; portability and tolerances are **not** established. All comparison rules below are proposals pending validation, and `semantic_fidelity_validated` is currently false.

## Proposed derived input (NOT yet built or validated)

`inputs/cell_groups.csv` from the reference artifact `cell_clusters_umap.csv` (sha256 6f2fc91d…): keep `sample` + renamed `leiden_res_0.50` → `cluster`, and normalize `cell_id` back to the raw 10x barcode so the join key is (sample, barcode), independent of the reference's `obs_names_make_unique` suffixing. Other per-cell columns (UMAP coordinates, other resolutions, `cell_type_lvl1`) are withheld; no DE/marker answers are present in the file. Materialization recipe and fallback in the handoff.

## Public-brief hygiene

The brief states rules symbolically; it does not disclose 17,041 cells, 23,427 genes, 17 clusters, label range, sample cell counts, or any marker identities. Resource/network limits from policy are stated, software choice is open, and the environment offer is non-binding.
