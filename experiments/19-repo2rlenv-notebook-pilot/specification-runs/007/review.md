## Coverage — all eligible terminal results are represented

`inputs/original.py` stores exactly two families of terminal, interpreted results that survive to completion:

1. **Clustering / annotation / embedding**: `adata.obs['leiden']` (default call: resolution 1, `n_iterations=2`), `leiden_res_0.02/0.50/2.00` (loop with `key_added`), the manual annotation `cell_type_lvl1` (map of `leiden_res_0.02`), `adata.obs['sample']` and `adata.obsm['X_umap']` — exported as `cell_clusters_umap.csv` (endpoint 1 in `inputs/exports.py`).
2. **Per-cluster DE rankings**: `adata.uns['rank_genes_groups']` (wilcoxon vs rest on `leiden_res_0.50`) plus its `params` — exported as the flattened CSV + params JSON (endpoints 2–3).

The `inputs/plan.json` exclusions are verified against the source and run:
- **QC metrics/plots** are diagnostics; the permissive filters (`min_genes=100`, `min_cells=3`) are recomputed from the count matrix, not from QC columns (scanpy 1.12.4 `scanpy/preprocessing/_simple.py:167-175` computes `number_per_cell` from `data > 0` sums), so no endpoint depends on `calculate_qc_metrics`.
- **Scrublet** results are diagnostics with doublet filtering left unexecuted in the source; `scanpy/preprocessing/_scrublet/__init__.py:195-199,285,302-304` shows it runs on a copy and writes only `.obs`/`.uns`, leaving `X` untouched, and the batched obs-replacement preserves prior columns (audit: `sample`/`cell_type_lvl1` blank=0).
- **HVG / X_pca / neighbor graph / `layers['counts']` / normalized matrix**: intermediates consumed downstream.
- **`dc_cluster_genes`** and the group-"7" `head(5)` display: top-5 subsets of records fully contained in the exported DE table.
- **`marker_genes` and dotplots**: prior-knowledge input / plot-only; the duplicated `sc.pl.umap(..., legend_loc="on data")` call is a redundant view. Plot-only results have no stored values, so nothing further is owed.

Plot side effect noted: the `leiden_res_0.50` dotplot auto-runs `sc.tl.dendrogram` (execution log); it writes `.uns` only, is inert for endpoints, and is correctly not claimed as verified.

## Fidelity

- **Adaptations** (`trial/source.diff`): only `matplotlib.use("Agg")`, `XDG_CACHE_HOME=/work/cache`, and `load_registry(registry.txt)` replacing `load_registry_from_doi()`. No scientific call changed; the rest is byte-identical to `inputs/original.py`. The offline registry supplies the same file names + provider md5s; staging verified both md5s against the provider (`trial/result.json` setup log, `trial/inputs-before.json`), and pooch still md5-checks each file at fetch time, so the dataset bytes are the original provider files.
- **Execution**: exit 0; 147.5 s of the 600 s budget; peak child RSS ≈ 4.93 GiB of 8 GiB; setup 3.3 s; all three declared artifacts present. `output-audit.json` (scope: structural only) is coherent: no blanks/non-finite values; cluster-label ranges mutually consistent between the two tables; `cell_type_lvl1` fully populated over the observed 0..4 resolution-0.02 labels, matching the source's 5-entry map; DE rows = 17 groups × 23,427 filtered genes, group range matching `leiden_res_0.50`; params JSON matches the scanpy-1.12.4 `params` dict (`scanpy/tools/_rank_genes_groups.py:830-837`).
- The plan's open assumption (whether `leiden_res_0.02` yields exactly clusters 0–4) is resolved by execution: `cell_type_lvl1` has no missing values.

## Consequential defaults — established from installed sources (scanpy 1.12.4 unless noted)

- `read_10x_h5` keeps only Gene Expression features (`scanpy/readwrite.py:179-246`); deduplication suffix rule `anndata/utils.py:251-285` (first occurrence unsuffixed); `ad.concat` inner join + `label`, original indices kept (`anndata/_core/merge.py:1440-1493`); `obs_names_make_unique` applies to later duplicates (s1d1 first ⇒ s1d1 barcodes unsuffixed).
- `normalize_total`: target = median of per-cell totals (`scanpy/preprocessing/_normalization.py:20-26,104-105`).
- HVG: `seurat` flavor, 20 bins, batch merge ranks by (nbatches desc, mean normalized dispersion desc) (`scanpy/preprocessing/_highly_variable_genes.py:565-627`).
- PCA: restricted to the `highly_variable` mask by default (`scanpy/preprocessing/_pca/__init__.py:431-442`), 50 components (`:231-233`), zero-centered arpack on sparse X (`:483-506`).
- `neighbors`: n=15, euclidean, all of `X_pca` (`scanpy/neighbors/__init__.py:81-95`); pynndescent backend at this n_obs (`:733-738,776-788`); connectivities via the UMAP kernel.
- UMAP: min_dist 0.5, spread 1.0, spectral init, seed 0, 200 epochs for n_obs > 10,000 (`scanpy/tools/_umap.py:44-58,215`).
- Leiden: igraph `community_leiden`, modularity objective, edge weights, beta 0.01 (igraph 1.0.0 `src/igraph/community.py:455-527`), scanpy-seeded igraph RNG (`scanpy/_utils/random.py:59-71`), natsorted string labels (`scanpy/tools/_leiden.py:173-198`). **Checked per invocation**: the default call passes `n_iterations=2`; the resolution-loop calls do not, so they inherit −1 (run-until-stable) — preserved by the adaptation.
- `rank_genes_groups`: wilcoxon vs rest, `tie_correct=False`, BH, all genes, `use_raw=False` (no raw slot), group order = category order (`scanpy/tools/_rank_genes_groups.py:656-673,786-787`; `scanpy/_utils/__init__.py:802-849`), within-group order by descending score (`:37-44,594-609`), logfoldchange formula (`:624-635`).

## Remaining gaps / provisional status (not drafting blockers)

- `solver_timeout_seconds` is provisional per `task_policy`; the reference completed with a large margin (147.5 s of 600 s).
- Numeric equivalence tolerances (cluster agreement under label permutation, UMAP agreement after rigid alignment, DE rank agreement, tie handling) are not yet calibrated; these are future validation measurements with named wrong-method controls, permitted because the scientific contract itself (inputs, procedure, parameters, seeds, schemas, row identities) is fully determined by the source, the installed package sources, and one executed reference run, with no guessing required.
