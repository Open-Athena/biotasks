# Private scope, fidelity and verifiability review

## Scope decision (approved scope)

Target = the notebook's terminal **marker-gene / differential-expression branch**: `sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")` (`inputs/original.py`), i.e. per-cluster vs-rest Wilcoxon DE on the pooled, permissively filtered, median-normalized, log1p data, with within-cluster Benjamini–Hochberg correction. Deliverable = the **full existing endpoint table** (`rank_genes_groups_leiden_res_0.50.csv`, 398,259 rows), replacing the prior top-50 projection per operator feedback; no auxiliary summary outputs are requested.

- **Excluded** (per approved scope + prior pinned-source verification, reused): cluster discovery, UMAP, `cell_type_lvl1`, QC metrics/plots, scrublet (operates on `adata.copy()`, writes only `.obs`/`.uns`; `scanpy/preprocessing/_scrublet/__init__.py:190-235`), HVG/PCA/neighbors (annotate only `var`/`obsm`/`uns`). Nothing in the retained branch consumes them: `adata.X` at DE time is exactly the filtered, median-normalized, log1p matrix.
- **Supplied grouping** (approved scope): `leiden_res_0.50` labels from the recorded run (reference artifact `cell_clusters_umap.csv`), explicitly not ground truth.
- **Proposed additional input**: `gene_identities.csv` identity map — no results, only identity/provenance — added per operator guidance to replace the previously prescribed duplicate-suffix naming algorithm.

## Corrections applied from operator feedback

1. Rank/order contradiction removed: rank 1 = highest score; file sorted by ascending numeric cluster then ascending rank.
2. All invented numeric thresholds and safety factors removed; only comparison families + required evidence are proposed.
3. Top-k projection replaced by the full endpoint table; no new cutoff, so no boundary-tie issue.
4. Auxiliary targets (`analysis_summary.json`, `group_sizes.csv`) dropped; single deliverable.
5. **Retraction**: the prior claim that `scipy.stats.mannwhitneyu(method="asymptotic", use_continuity=False)` is algebraically equivalent to the reference statistic is wrong — asymptotic Mann–Whitney always applies the tie-corrected variance; disabling continuity is separate. The public contract now defines the statistic directly; scipy cannot be used as-is for the no-tie-correction variance.
6. p-value phrasing states the two-sided normal tail quantity and requires stable evaluation, without prescribing arithmetic.
7. Monotone-transform rejection claim removed; instead note that dropping log1p (keeping per-cell median scaling) leaves z/p invariant (rank-based) and changes only the effect-size column — a discriminator to measure, not assert.
8. Identity now via explicit supplied maps: cells keyed by (`sample`, raw barcode); genes keyed by `gene_id` mapped to per-sample `h5_row`.

## Measured facts (recorded execution)

- `trial/result.json`: exit 0, 147.5 s, peak child RSS 5,175,376 KiB (< 8 GiB), no timeout; reference full pipeline (incl. plots/UMAP). Pre-filter sample counts s1d1 8,785 / s1d3 8,340. Warnings confirm **duplicate gene symbols within each sample's Gene Expression features** and **cross-sample duplicate barcodes** — both facts motivate the supplied identity maps.
- `output-audit.json`: `cell_clusters_umap.csv` 17,041 rows (identity source for the grouping input); `rank_genes_groups_leiden_res_0.50.csv` 398,259 rows = complete cluster × gene cross product (17 groups × 23,427 genes), columns group/names/scores/pvals_adj/pvals/logfoldchanges; score range [-67.24, 85.90]; log2fc [-29.89, 25.74] (consistent with the expm1+1e-9 definition, ≈ ±log2(1e9)); pvals/pvals_adj ∈ [0,1] with exact zeros (underflow); `rank_genes_groups_params.json` = {groupby: leiden_res_0.50, reference: rest, method: wilcoxon, use_raw: false, layer: null, corr_method: benjamini-hochberg}. Reference CSV: scores/logfoldchanges written from float32 storage; pvals float64.
- Inputs hash-pinned (h5 sha256 322c30a7…, ca40b287…; provider md5s verified at staging). Full lock retained (`trial/uv.lock`); scanpy 1.12.4, anndata 0.13.4.
- Adaptation fidelity (`trial/source.diff`): only headless/backend and pooch-cache/registry input-path changes; no change to data, populations, algorithms, parameters or analysis branches. No execution defects found (artifacts present, download hashes verified; audit scope disclaims independent reproduction).

## Methodological facts (pinned sources, reused from prior inspection)

- scanpy 1.12.4 wilcoxon (`tools/_rank_genes_groups.py`): average (mid)ranks; `tie_correct=False` default; σ = sqrt(n(N−n)(N+1)/12) with no tie term, no continuity correction; z = (W − n(N+1)/2)/σ (NaN→0); two-sided normal tail; all genes tested (`n_genes=None`); groups vs **rest** = all other cells; per-group BH via statsmodels `fdr_bh`; log2fc = log2((expm1(μ_g)+1e-9)/(expm1(μ_rest)+1e-9)), natural expm1 of means of log-normalized X; scores/log2fc stored float32 — all consistent with the recorded value ranges.
- Preprocessing chain affecting the DE: `read_10x_h5` defaults (Gene Expression features, gene-symbol var_names), per-sample `var_names_make_unique`, `ad.concat` inner join in dict (sample) order, `obs_names_make_unique`, `filter_cells(min_genes=100)` then `filter_genes(min_cells=3)` on the pooled matrix (strictly positive detection), `layers["counts"]` copy, `normalize_total` default (median of per-cell totals of the current X, i.e. the gene-filtered matrix) then natural `log1p`.
- Unverified detail: the export's group block order equals the stored categorical order of the labels; numeric-ascending order is expected but must be confirmed from the artifact at validation (structural check, no new science).

## Verifiability assessment

The DE branch is deterministic (no RNG); the full endpoint table exists as a recorded artifact and is the grading reference. However, only **one** reference execution and a structural audit exist: repeatability, portability and tolerance calibration are unmeasured, and `semantic_fidelity_validated` is false. All comparison rules are therefore proposals pending the validation gate in the handoff. Known comparison hazards: p-underflow to exact 0 on both sides; float32 rounding of scores/log2fc; possible exact score ties within blocks (representation only); BH is a deterministic monotone function of the within-cluster p vector, so small p deviations propagate into `pval_adj`. Identity hazards (duplicate symbols per sample; cross-sample duplicate barcodes) are removed from the solver's burden by the two supplied maps.

## Proposed derived inputs (NOT yet built or validated)

- `inputs/cell_groups.csv`: (`sample`, `barcode`, `cluster`) from `cell_clusters_umap.csv` (sha256 6f2fc91d…), raw barcode recovered from `cell_id`, validated against the h5 barcode lists.
- `inputs/gene_identities.csv`: per-sample Gene Expression feature rows (`sample`, `h5_row`, `gene_id`, `ensembl_id`, `gene_symbol`) with `gene_id` = the recorded reference's post-dedup var_names; `h5_row` pins stored matrix rows.

Neither contains DE results. Recipes, checks and fallbacks in the handoff.

## Blockers before release (not before drafting)

Deriving and validating both inputs; confirming reference block order and per-block lengths; a repeatability re-run; clean-room deviation measurements; discriminator runs; brief hygiene check. None blocks the task definition itself.
