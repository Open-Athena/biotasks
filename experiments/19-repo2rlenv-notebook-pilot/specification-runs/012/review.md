## Coverage of the original source (`inputs/original.py`, scanpy tutorial rev 8c1463d)

The notebook has two terminal result branches, and both are covered by the export plan:

1. **Clustering/annotation branch** — `sc.tl.leiden(adata, flavor="igraph", n_iterations=2)` fills `adata.obs["leiden"]`; the resolution loop (`for res in [0.02, 0.5, 2.0]` with `key_added=f"leiden_res_{res:4.2f}"`) fills `leiden_res_0.02/0.50/2.00`; `adata.obs["cell_type_lvl1"]` is the manual broad-lineage map of the coarsest solution; `adata.obsm["X_umap"]` comes from `sc.tl.umap(adata)`; `adata.obs["sample"]` from `ad.concat(adatas, label="sample")`. All are present, fixed-keyed and unmodified at completion. Exported in `cell_clusters_umap.csv`.
2. **DE-marker branch** — `sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")` stores the full per-group, all-gene rankings in `adata.uns["rank_genes_groups"]` (fields `names`, `scores`, `pvals_adj`, `pvals`, `logfoldchanges`, verified present for this method in scanpy 1.12.4 `scanpy/tools/_rank_genes_groups.py:888-914`). The notebook itself treats this stored object as the readable result (`sc.get.rank_genes_groups_df(adata, group="7")`) and reads a finding from it (cluster 7 = NK via NKG7/GNLY). Exported flattened into `rank_genes_groups_leiden_res_0.50.csv` plus its stored run parameters as `rank_genes_groups_params.json`.

**Exclusions reviewed and accepted as role-based** (`inputs/plan.json`): QC metric columns and their plots (diagnostics motivating the deliberately permissive filtering; no derived thresholds); Scrublet `doublet_score`/`predicted_doublet` (diagnostics; the notebook explicitly leaves both doublet-filtering options unexecuted); HVG annotations and PCA (intermediates feeding the neighbor graph); `adata.layers["counts"]` and normalized/log1p `adata.X` (intermediates); `dc_cluster_genes` and the unnamed `head(5)` display (a top-5 subset fully contained in endpoint 2); `marker_genes` dict (prior-knowledge input, consumed only by dotplots); plot-computed values, including the dendrogram that `sc.pl.rank_genes_groups_dotplot` triggers with defaults (display-supporting state added inside a plotting call per the reference run log, not an interpreted result). Leiden `uns` modularity/params entries are clustering-supporting metadata, not read in the notebook. Nothing terminal is lost and no computation was deleted.

## Fidelity of the adaptation (`trial/source.diff`, `candidate/analysis.py`)

The diff is environment-only: `matplotlib.use("Agg")`, `XDG_CACHE_HOME=/work/cache`, and replacing `EXAMPLE_DATA.load_registry_from_doi()` (network fetch of figshare file names/md5s) with `EXAMPLE_DATA.load_registry(registry.txt)` where the registry carries the same provider md5 values (`provenance.json`). Pooch still md5-verifies the staged files at fetch time, confirmed by the setup log in `trial/result.json` ("md5 … verified" for both files). Identical bytes therefore reach `sc.read_10x_h5`; input identities in `trial/inputs-before.json` (sha256 + provider md5) match `provenance.json`. The appended export stage (`inputs/exports.py`) only reads already-stored state; no recomputation, filtering, re-ranking or plotting is added. No scientific content, branch, parameter or population is changed.

## Execution and audit evidence

- `trial/result.json`: exit code 0, 147.5 s, peak child RSS ~5.05 GiB — within the 600 s / 8 GiB policy. Reference runtime does not establish solver runtime.
- All three artifacts exist with stable hashes; `output-audit.json` column names match the export code (`cell_id, sample, leiden, leiden_res_0.02/0.50/2.00, cell_type_lvl1, umap_1, umap_2`; `group, names, scores, pvals_adj, pvals, logfoldchanges`), and the `params` JSON content matches the parameter keys scanpy 1.12.4 stores at `scanpy/tools/_rank_genes_groups.py:830-837` (groupby, reference, method, use_raw, layer, corr_method).
- `cell_type_lvl1`: audit shows zero blank values, i.e. the observed coarsest solution's cluster labels were covered by the notebook's hard-coded 5-key map — this resolves the plan's stated assumption for the reference run, but is a single-run observation, not proof of stability.

## Identity rules resolved by package inspection (recorded versions)

- Group/label order: `sc.tl.leiden` stores categorical labels with `natsorted` categories (`scanpy/tools/_leiden.py:195-198`, scanpy 1.12.4); `rank_genes_groups` with `groups="all"` iterates `adata.obs[groupby].cat.categories` via `select_groups` (`scanpy/_utils/__init__.py:808, 846-849`), so the flattened DE table's group-block order is the natural-sorted category order of the groupby clustering.
- `cell_id`: `AnnData.obs_names_make_unique` uses `anndata.utils.make_index_unique` (anndata 0.13.4, `anndata/utils.py:226-249`), first occurrence unchanged, duplicates suffixed `-1`, `-2`, ….
- Units/dtypes: `scores` = the z-score underlying the p-value, `logfoldchanges` = log2 fold change (approximation from mean-log values), `pvals`/`pvals_adj` raw/BH-corrected (`scanpy/tools/_rank_genes_groups.py:747-762`); reference storage dtypes scores/logfoldchanges float32, pvals/pvals_adj float64 (`:888-894`).

## Blockers

None. The reference recipe and output schemas are fully defined by the source, the named pinned operations and the recorded environment. Remaining items (comparison tolerances, cross-implementation equivalence, run-to-run stability) belong to the later executable validation stage, not this draft. `semantic_fidelity_validated: false` in `trial/result.json` is resolved by this review.
