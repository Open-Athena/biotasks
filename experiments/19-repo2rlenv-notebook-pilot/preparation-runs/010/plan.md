# Preparation worker output

Rendered from [plan.json](plan.json). Generated commands and source edits have not been executed. Only structural checks have run; scientific fidelity is unreviewed.

## Decision

prepare

The notebook's terminal scientific outcomes are (i) the Leiden clustering solutions, the UMAP embedding they are interpreted on, and the manual broad-lineage cell-type annotation derived from the coarsest solution, and (ii) the per-cluster differentially expressed genes (Wilcoxon) used to annotate the 0.50-resolution clusters. The appended code only serializes values that exist at completion: selected adata.obs columns plus adata.obsm['X_umap'] in one per-cell CSV, and the stored adata.uns['rank_genes_groups'] rankings flattened group-by-group into a CSV, with the stored DE run parameters written as context. No values are recomputed, filtered, re-ranked or plotted; the source analysis is untouched.

## Artifact: cell_clusters_umap.csv

Per-cell terminal results: cell barcode index; originating sample; Leiden cluster assignment at the default resolution and at resolutions 0.02/0.50/2.00; the manual broad-lineage cell-type annotation (cell_type_lvl1); and the 2-D UMAP coordinates (umap_1, umap_2).

Source evidence: The clustering/annotation branch is the notebook's stated end product: 'we recommend the Leiden graph-clustering method' (sc.tl.leiden(adata, flavor='igraph', n_iterations=2) fills adata.obs['leiden']); 'let's generate a set of clustering solutions which we can then use to annotate our cell types' (the resolution loop writes adata.obs['leiden_res_0.02'/'leiden_res_0.50'/'leiden_res_2.00'] via key_added); the marker patterns are used 'to label our coarsest clustering with broad lineages' (adata.obs['cell_type_lvl1'] mapped from leiden_res_0.02); the UMAP embedding is interpreted in its own right ('we only observe a minor batch effect', and it is the surface for cluster, QC and marker visualization) and is stored by sc.tl.umap(adata) in adata.obsm['X_umap']. adata.obs['sample'] (from ad.concat(adatas, label='sample')) is the per-cell sample identifier needed to read the embedding. All keys are fixed and survive to script completion.

## Artifact: rank_genes_groups_leiden_res_0.50.csv

Differentially expressed genes per cluster of the leiden_res_0.50 solution (Wilcoxon vs rest): one row per ranked gene per cluster with group, names, scores, pvals_adj, pvals and logfoldchanges, in the stored group and rank order.

Source evidence: The marker-gene/DE branch yields an independent interpreted outcome: 'one can also calculate marker genes per cluster and then look up whether we can link those marker genes to any known biology, such as cell types and/or states', and the result is directly read as a finding ('Cluster 7 is expressing NKG7 and GNLY, suggesting these are NK cells'). It is produced by sc.tl.rank_genes_groups(adata, groupby='leiden_res_0.50', method='wilcoxon') and stored in adata.uns['rank_genes_groups']; the notebook itself notes the results 'can be extracted in a convenient format with scanpy.get.rank_genes_groups_df' (called with group='7'), confirming this stored object is the readable result table. The export flattens those same stored recarrays (all stored fields, groups and ranking order preserved) without recomputation.

## Artifact: rank_genes_groups_params.json

Run parameters stored with the DE result (groupby, method, reference, correction method), identifying which clustering and test produced the exported DE table.

Source evidence: Written from adata.uns['rank_genes_groups']['params'], populated by the sc.tl.rank_genes_groups(groupby='leiden_res_0.50', method='wilcoxon') call in the baseline; these identifiers are the context needed to interpret the endpoint table.

## Worker-returned export code

```python
# ---------------------------------------------------------------------------
# Endpoint exports (appended stage): serialize existing terminal results only.
# No new scientific computation, filtering, ranking or plotting is added.
# ---------------------------------------------------------------------------

import json
import os

import pandas as pd

_export_dir = "/work/outputs"
os.makedirs(_export_dir, exist_ok=True)

# Endpoint 1 -- per-cell terminal results: Leiden cluster assignments
# (default resolution and the three annotation resolutions), the manual
# cell-type annotation, the sample identifier and the UMAP embedding.
_per_cell_obs = adata.obs[
    [
        "sample",
        "leiden",
        "leiden_res_0.02",
        "leiden_res_0.50",
        "leiden_res_2.00",
        "cell_type_lvl1",
    ]
].copy()
_umap_table = pd.DataFrame(adata.obsm["X_umap"])
_umap_table.columns = ["umap_1", "umap_2"]
_umap_table.index = adata.obs_names
_per_cell = pd.concat([_per_cell_obs, _umap_table], axis=1)
_per_cell.index.name = "cell_id"
_per_cell.to_csv(os.path.join(_export_dir, "cell_clusters_umap.csv"), index=True)

# Endpoint 2 -- differentially expressed genes per cluster of the
# leiden_res_0.50 solution, flattened from the stored rankings in
# adata.uns["rank_genes_groups"]; stored group order and rank order are kept.
_rgg = adata.uns["rank_genes_groups"]
_de_fields = [
    _f
    for _f in ("names", "scores", "pvals_adj", "pvals", "logfoldchanges")
    if _f in _rgg
]
_de_parts = []
for _grp in _rgg["names"].dtype.names:
    _part = {"group": _grp}
    for _f in _de_fields:
        _part[_f] = _rgg[_f][_grp]
    _de_parts.append(pd.DataFrame(_part))
_rank_genes_groups_table = pd.concat(_de_parts, ignore_index=True)
_rank_genes_groups_table.to_csv(
    os.path.join(_export_dir, "rank_genes_groups_leiden_res_0.50.csv"),
    index=False,
)

# Context for endpoint 2: the stored run parameters of the DE test.
with open(
    os.path.join(_export_dir, "rank_genes_groups_params.json"), "w"
) as _params_fh:
    json.dump(dict(_rgg["params"]), _params_fh, indent=2, default=str)
```

## Controller-assembled reference script

[reference.py](reference.py): untouched original script followed by the export code above.

## Controller-computed diff

```diff
--- baseline.py
+++ reference.py
@@ -321,3 +321,64 @@
 )
 
 # You may have noticed that the p-values found here are extremely low. This is due to the statistical test being performed considering each cell as an independent sample. For a more conservative approach you may want to consider "pseudo-bulking" your data by sample (*e.g.* `sc.get.aggregate(adata, by=["sample", "cell_type"], func="sum", layer="counts")`) and using a more powerful differential expression tool, like {doc}`pydeseq2 <pydeseq2:index>`.
+
+
+# ---------------------------------------------------------------------------
+# Endpoint exports (appended stage): serialize existing terminal results only.
+# No new scientific computation, filtering, ranking or plotting is added.
+# ---------------------------------------------------------------------------
+
+import json
+import os
+
+import pandas as pd
+
+_export_dir = "/work/outputs"
+os.makedirs(_export_dir, exist_ok=True)
+
+# Endpoint 1 -- per-cell terminal results: Leiden cluster assignments
+# (default resolution and the three annotation resolutions), the manual
+# cell-type annotation, the sample identifier and the UMAP embedding.
+_per_cell_obs = adata.obs[
+    [
+        "sample",
+        "leiden",
+        "leiden_res_0.02",
+        "leiden_res_0.50",
+        "leiden_res_2.00",
+        "cell_type_lvl1",
+    ]
+].copy()
+_umap_table = pd.DataFrame(adata.obsm["X_umap"])
+_umap_table.columns = ["umap_1", "umap_2"]
+_umap_table.index = adata.obs_names
+_per_cell = pd.concat([_per_cell_obs, _umap_table], axis=1)
+_per_cell.index.name = "cell_id"
+_per_cell.to_csv(os.path.join(_export_dir, "cell_clusters_umap.csv"), index=True)
+
+# Endpoint 2 -- differentially expressed genes per cluster of the
+# leiden_res_0.50 solution, flattened from the stored rankings in
+# adata.uns["rank_genes_groups"]; stored group order and rank order are kept.
+_rgg = adata.uns["rank_genes_groups"]
+_de_fields = [
+    _f
+    for _f in ("names", "scores", "pvals_adj", "pvals", "logfoldchanges")
+    if _f in _rgg
+]
+_de_parts = []
+for _grp in _rgg["names"].dtype.names:
+    _part = {"group": _grp}
+    for _f in _de_fields:
+        _part[_f] = _rgg[_f][_grp]
+    _de_parts.append(pd.DataFrame(_part))
+_rank_genes_groups_table = pd.concat(_de_parts, ignore_index=True)
+_rank_genes_groups_table.to_csv(
+    os.path.join(_export_dir, "rank_genes_groups_leiden_res_0.50.csv"),
+    index=False,
+)
+
+# Context for endpoint 2: the stored run parameters of the DE test.
+with open(
+    os.path.join(_export_dir, "rank_genes_groups_params.json"), "w"
+) as _params_fh:
+    json.dump(dict(_rgg["params"]), _params_fh, indent=2, default=str)
```

## Excluded outputs

- QC metrics and QC figures (adata.obs n_genes_by_counts, total_counts, pct_counts_{mt,ribo,hb} and log1p variants; violin and scatter plots): diagnostics used to motivate the deliberately permissive filtering and re-assessed on the UMAP; no thresholds beyond min_genes/min_cells are derived from them.

- Scrublet doublet results (adata.obs['doublet_score'], adata.obs['predicted_doublet']): diagnostic QC supporting cluster assessment; the notebook only inspects them alongside the clusters and explicitly leaves doublet-based filtering as an unexecuted option.

- Highly variable gene annotations (adata.var highly_variable, dispersions/means columns): feature-selection intermediate feeding PCA; the HVG set is not itself interpreted as an independent result.

- PCA results (adata.obsm['X_pca'], variance ratio): intermediate consumed by the neighbor graph; the variance-ratio and PCA plots are checks on parameter choice and batch effects.

- Count layer adata.layers['counts'] and the normalized/log1p matrix adata.X: intermediates consumed by HVG, PCA, dotplots and the DE test; excluded on role, not size.

- dc_cluster_genes and the unnamed sc.get.rank_genes_groups_df(adata, group='7').head(5) display: a top-5 display subset of the cluster-7 ranking fully contained in the exported DE table; the follow-up UMAP coloring of those genes is computed inside sc.pl.umap and is not exported.

- marker_genes dictionary and the marker-gene dotplots: the dictionary is prior-knowledge input, and dotplot values are computed inside the plotting function; neither is a stored computed result eligible for export.

## Unresolved assumptions

- The export assumes the baseline completes and the fixed keys it reads exist at append time ('leiden', 'leiden_res_0.02'/'leiden_res_0.50'/'leiden_res_2.00', 'cell_type_lvl1' in adata.obs; 'X_umap' in adata.obsm with 2 components; 'rank_genes_groups' in adata.uns). cell_type_lvl1 is defined only for leiden_res_0.02 clusters 0-4, matching the notebook's hardcoded map; whether the clustering yields exactly those clusters is untested.

- Staging of the two 10x .h5 inputs via pupper/pooch and figshare plus headless behavior of the scanpy plotting calls are execution-stage concerns that determine whether the baseline reaches completion; this preparation does not assume observed runtimes.

- Whether the full two-sample workflow (scrublet, PCA, neighbors, UMAP, Wilcoxon DE) fits the 600-second CPU-only, 8 GiB limit is untested; the size of the DE table (number of leiden_res_0.50 clusters x stored genes) is likewise unobserved and not assumed.
