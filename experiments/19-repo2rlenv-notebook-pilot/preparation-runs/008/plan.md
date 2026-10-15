# Preparation worker output

Rendered from [plan.json](plan.json). Generated commands and source edits have not been executed. Only structural checks have run; scientific fidelity is unreviewed.

## Decision

prepare

Every terminal result of this pipeline already exists on the final adata or in a named variable: per-cell QC metrics, scrublet doublet_score/predicted_doublet, four Leiden clustering solutions and the manual cell_type_lvl1 annotation (adata.obs); gene QC flags/metrics and highly-variable-gene results (adata.var); the UMAP layout (adata.obsm['X_umap']); the Wilcoxon cluster-vs-rest differential-expression ranking (adata.uns['rank_genes_groups']); and the named top-5 cluster-7 marker list dc_cluster_genes. The appended code only serializes these existing values into five CSV files under /work/outputs; the DE structured arrays are reformatted into a tidy table (the same extraction the tutorial demonstrates with sc.get.rank_genes_groups_df), with the per-group fraction-expressing table joined by gene identifier when scanpy stored it. No computation, filtering or ranking is added, plotting calls are untouched, and mixed analysis-state content (count/normalized matrices, PCA, neighbor graph, whole-object h5ad) is excluded in favor of the endpoint fields.

## Artifact: cell_annotations.csv

Final per-cell result table from the QC, doublet-detection, clustering and annotation branches: sample label, per-cell QC metrics (n_genes_by_counts, total_counts and mt/ribo/hb percentages with log1p variants), scrublet doublet_score and predicted_doublet, Leiden labels at the default setting and at resolutions 0.02/0.50/2.00, and the manual cell_type_lvl1 annotation; row index is the unique cell barcode.

Source evidence: All values are existing adata.obs fields written by the original script: sc.pp.calculate_qc_metrics, sc.pp.scrublet(batch_key='sample'), sc.tl.leiden (default key and the key_added loop over resolutions 0.02/0.5/2.0), and the cell_type_lvl1 mapping applied to obs['leiden_res_0.02']. None of these obs columns is overwritten afterwards, so the final state is the endpoint of those branches.

## Artifact: gene_annotations.csv

Final per-gene result table: mitochondrial/ribosomal/hemoglobin flags, per-gene QC metrics (n_cells_by_counts, mean/dropout counts, total counts and log1p variants) from sc.pp.calculate_qc_metrics, and the feature-selection result (highly_variable plus means/dispersions/dispersions_norm); row index is the unique gene symbol.

Source evidence: Existing adata.var fields set by the adata.var['mt'/'ribo'/'hb'] assignments, sc.pp.calculate_qc_metrics and sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key='sample'); adata.var is not overwritten after these steps.

## Artifact: umap_embedding.csv

Per-cell 2-D UMAP coordinates (umap_1, umap_2): the final embedding on which the script reads sample mixing, cluster structure, QC re-assessment and marker-gene expression.

Source evidence: Existing adata.obsm['X_umap'] produced by sc.tl.umap(adata) after sc.pp.neighbors(adata); the coordinates already exist outside the later sc.pl.umap calls, so the plotted endpoint values are exported without touching plotting.

## Artifact: rank_genes_groups.csv

Tidy Wilcoxon cluster-vs-rest differential-expression results per leiden_res_0.50 cluster: group, ranked gene names, scores, p-values, pvals_adj, logfoldchanges, and the per-group fraction of expressing cells (pts) when scanpy stored it; groups are concatenated in scanpy's ranking order. The uns entry's 'params' dict (groupby/method settings) is run configuration rather than per-gene data, so it is documented here instead of being written as a column; 'pts_rest' is absent because the reference is 'rest'.

Source evidence: sc.tl.rank_genes_groups(adata, groupby='leiden_res_0.50', method='wilcoxon') stores the result in adata.uns['rank_genes_groups']; the appended code only reformats those existing structured arrays (the extraction the tutorial itself performs with sc.get.rank_genes_groups_df).

## Artifact: cluster7_top5_de_genes.csv

Top-5 differentially-expressed marker genes for cluster 7 (rank, gene): the tutorial's worked example of marker-driven cell-type interpretation.

Source evidence: The named variable dc_cluster_genes = sc.get.rank_genes_groups_df(adata, group='7').head(5)['names'] is created after the DE step and only used for plotting afterwards; it persists unchanged to script completion.

## Worker-returned export code

```python
# ---------------------------------------------------------------------------
# Endpoint export: save the terminal scientific results computed above.
# Only already-existing values are serialized; nothing is recomputed.
# ---------------------------------------------------------------------------
import os

import pandas as pd

_EXPORT_DIR = "/work/outputs"
os.makedirs(_EXPORT_DIR, exist_ok=True)

# 1) Final per-cell results: sample identity, per-cell QC metrics, Scrublet
#    doublet score/call, Leiden clusterings (default plus resolutions
#    0.02/0.50/2.00) and the manual cell_type_lvl1 annotation.
_cells = adata.obs.copy()
_cells.index.name = "cell_barcode"
_cells.to_csv(os.path.join(_EXPORT_DIR, "cell_annotations.csv"))

# 2) Final per-gene results: gene QC flags/metrics and the highly-variable
#    gene annotations from feature selection.
_genes = adata.var.copy()
_genes.index.name = "gene"
_genes.to_csv(os.path.join(_EXPORT_DIR, "gene_annotations.csv"))

# 3) UMAP embedding: the 2-D cell layout used for the script's sample,
#    cluster, QC and marker-gene visualizations.
_umap = pd.DataFrame(
    adata.obsm["X_umap"],
    index=pd.Index(adata.obs_names, name="cell_barcode"),
    columns=["umap_1", "umap_2"],
)
_umap.to_csv(os.path.join(_EXPORT_DIR, "umap_embedding.csv"))

# 4) Wilcoxon cluster-vs-rest differential expression per leiden_res_0.50
#    cluster, reformatted from the existing structured arrays stored by
#    sc.tl.rank_genes_groups into a tidy table (same content the tutorial
#    extracts with sc.get.rank_genes_groups_df).
_rgg = adata.uns["rank_genes_groups"]
_fields = [
    f
    for f in ("names", "scores", "pvals", "pvals_adj", "logfoldchanges")
    if f in _rgg
]
_pts = _rgg.get("pts")
_frames = []
for _g in _rgg["names"].dtype.names:
    _frame = pd.DataFrame({f: _rgg[f][_g] for f in _fields})
    _frame.insert(0, "group", _g)
    if _pts is not None and _g in getattr(_pts, "columns", ()):
        _frame["pts"] = _frame["names"].map(_pts[_g])
    _frames.append(_frame)
pd.concat(_frames, ignore_index=True).to_csv(
    os.path.join(_EXPORT_DIR, "rank_genes_groups.csv"), index=False
)

# 5) The tutorial's example extraction: top-5 DE genes of cluster 7, kept
#    in the named variable dc_cluster_genes.
_dc_genes = dc_cluster_genes.rename("gene")
_dc_genes.index.name = "rank"
_dc_genes.to_csv(os.path.join(_EXPORT_DIR, "cluster7_top5_de_genes.csv"))

```

## Controller-assembled reference script

[reference.py](reference.py): untouched original script followed by the export code above.

## Controller-computed diff

```diff
--- baseline.py
+++ reference.py
@@ -321,3 +321,65 @@
 )
 
 # You may have noticed that the p-values found here are extremely low. This is due to the statistical test being performed considering each cell as an independent sample. For a more conservative approach you may want to consider "pseudo-bulking" your data by sample (*e.g.* `sc.get.aggregate(adata, by=["sample", "cell_type"], func="sum", layer="counts")`) and using a more powerful differential expression tool, like {doc}`pydeseq2 <pydeseq2:index>`.
+
+
+# ---------------------------------------------------------------------------
+# Endpoint export: save the terminal scientific results computed above.
+# Only already-existing values are serialized; nothing is recomputed.
+# ---------------------------------------------------------------------------
+import os
+
+import pandas as pd
+
+_EXPORT_DIR = "/work/outputs"
+os.makedirs(_EXPORT_DIR, exist_ok=True)
+
+# 1) Final per-cell results: sample identity, per-cell QC metrics, Scrublet
+#    doublet score/call, Leiden clusterings (default plus resolutions
+#    0.02/0.50/2.00) and the manual cell_type_lvl1 annotation.
+_cells = adata.obs.copy()
+_cells.index.name = "cell_barcode"
+_cells.to_csv(os.path.join(_EXPORT_DIR, "cell_annotations.csv"))
+
+# 2) Final per-gene results: gene QC flags/metrics and the highly-variable
+#    gene annotations from feature selection.
+_genes = adata.var.copy()
+_genes.index.name = "gene"
+_genes.to_csv(os.path.join(_EXPORT_DIR, "gene_annotations.csv"))
+
+# 3) UMAP embedding: the 2-D cell layout used for the script's sample,
+#    cluster, QC and marker-gene visualizations.
+_umap = pd.DataFrame(
+    adata.obsm["X_umap"],
+    index=pd.Index(adata.obs_names, name="cell_barcode"),
+    columns=["umap_1", "umap_2"],
+)
+_umap.to_csv(os.path.join(_EXPORT_DIR, "umap_embedding.csv"))
+
+# 4) Wilcoxon cluster-vs-rest differential expression per leiden_res_0.50
+#    cluster, reformatted from the existing structured arrays stored by
+#    sc.tl.rank_genes_groups into a tidy table (same content the tutorial
+#    extracts with sc.get.rank_genes_groups_df).
+_rgg = adata.uns["rank_genes_groups"]
+_fields = [
+    f
+    for f in ("names", "scores", "pvals", "pvals_adj", "logfoldchanges")
+    if f in _rgg
+]
+_pts = _rgg.get("pts")
+_frames = []
+for _g in _rgg["names"].dtype.names:
+    _frame = pd.DataFrame({f: _rgg[f][_g] for f in _fields})
+    _frame.insert(0, "group", _g)
+    if _pts is not None and _g in getattr(_pts, "columns", ()):
+        _frame["pts"] = _frame["names"].map(_pts[_g])
+    _frames.append(_frame)
+pd.concat(_frames, ignore_index=True).to_csv(
+    os.path.join(_EXPORT_DIR, "rank_genes_groups.csv"), index=False
+)
+
+# 5) The tutorial's example extraction: top-5 DE genes of cluster 7, kept
+#    in the named variable dc_cluster_genes.
+_dc_genes = dc_cluster_genes.rename("gene")
+_dc_genes.index.name = "rank"
+_dc_genes.to_csv(os.path.join(_EXPORT_DIR, "cluster7_top5_de_genes.csv"))

```

## Excluded outputs

- Raw and normalized expression matrices (adata.layers['counts'], log-normalized adata.X) and the raw per-sample AnnData objects (adatas): intake/processing state, not terminal results; the whole mixed-state adata is deliberately not dumped as .h5ad - its endpoint fields are exported instead.

- PCA results (adata.obsm['X_pca'], adata.varm['PCs'], adata.uns['pca'] including variance ratios) and the neighborhood graph (adata.obsp distances/connectivities): intermediate representations consumed by neighbors, UMAP and clustering, and diagnostics used only to sanity-check PC usage.

- All figures (violin, scatter, highly-variable-genes, PCA/variance-ratio, UMAP overlays, dotplots and rank_genes_groups_dotplot): plot-only summaries computed inside the plotting calls; no figure capture was added. Where plotted values exist outside plotting (QC metrics, cluster labels, UMAP coordinates, DE table) they are exported; the per-cluster mean marker-expression values behind sc.pl.dotplot exist only inside the plotting function.

- marker_genes dict: curated prior-knowledge input defining candidate cell-type markers; it is an annotation input rather than a computed endpoint.

- The standalone display expression sc.get.rank_genes_groups_df(adata, group='7').head(5): never assigned in the baseline; its content is already captured by the named dc_cluster_genes, which is exported.

- Method/configuration records in adata.uns (scrublet, hvg, pca settings and rank_genes_groups 'params'): run diagnostics rather than per-observation results.

## Unresolved assumptions

- Whether leiden_res_0.50 yields a cluster labelled '7' (and the full set of cluster labels, hence the group rows and size of the DE table) is only known at execution; the baseline itself already indexes group '7', so it would fail before export if absent.

- Whether adata.uns['rank_genes_groups']['pts'] is present and its column labels in the installed scanpy version; the export writes the pts column only when present.

- Whether cell_type_lvl1 contains missing values for any leiden_res_0.02 cluster beyond '0'-'4' (the provided mapping covers only five labels) is only known at execution; values are preserved as computed.

- Exact obs/var column sets depend on the installed scanpy's calculate_qc_metrics output; the export serializes the final tables as-is.

- Headless rendering of the sc.pl.* calls, successful pooch retrieval during setup, and whether the full pipeline (scrublet, PCA, neighbors, UMAP, multiple Leiden runs, Wilcoxon DE over all genes x clusters) fits the 600 s / 8 GiB / 4 CPU limits are execution-stage questions.
