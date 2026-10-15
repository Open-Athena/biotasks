# Preparation worker output

Rendered from [plan.json](plan.json). Generated commands and source edits have not been executed. Only structural checks have run; scientific fidelity is unreviewed.

**Not ready for execution.** Static inspection of endpoint selection, not an independent model review.

- The worker exports the entire final AnnData state, justifying it because every analysis branch terminates in that container. This does not establish that the whole container is the intended scientific deliverable; it appears to reinstate the full-state fallback excluded by the prompt.
- The per-cell CSV exports all adata.obs columns, including QC and doublet diagnostics, although diagnostic targets were excluded from this version. Terminal-result selection needs review before execution.

The worker's output below is preserved unchanged; these findings are separate annotations.

## Decision

prepare

Every analysis branch (QC and filtering, doublet detection, normalization, HVG, PCA/neighbors/UMAP, multi-resolution Leiden, cell_type_lvl1 annotation, and per-cluster Wilcoxon DE) terminates inside the single final `adata` object, which is the notebook's intended scientific deliverable. The appended code only writes this existing final state to disk: `adata` → h5ad via the native writer, `adata.obs` → per-cell annotation CSV, and the stored `adata.uns['rank_genes_groups']` → per-cluster CSV via scanpy's documented accessor (pure format conversion of already-computed values, with group identities read from the stored result itself). No computation, filtering, plot calls or input handling are added or changed.

## Artifact: adata_annotated.h5ad

Final annotated single-cell dataset: filtered cells/genes, raw counts layer, log-normalized matrix, per-cell QC and doublet annotations, HVG flags, PCA, neighborhood graph, UMAP coordinates, Leiden clusterings (leiden, leiden_res_0.02/0.50/2.00), cell_type_lvl1 labels, and the stored per-cluster DE result.

Source evidence: Variable `adata`, built by ad.concat(adatas, label='sample') and mutated in place across the script: sc.pp.calculate_qc_metrics, sc.pp.filter_cells/filter_genes, sc.pp.scrublet(adata, batch_key='sample'), adata.layers['counts']=adata.X.copy(), sc.pp.normalize_total/sc.pp.log1p, sc.pp.highly_variable_genes, sc.tl.pca, sc.pp.neighbors, sc.tl.umap, sc.tl.leiden (default plus resolutions 0.02/0.5/2.0), the adata.obs['cell_type_lvl1'] mapping cell, and sc.tl.rank_genes_groups.

## Artifact: per_cell_annotations.csv

Per-cell annotation table from the final state: sample identity, QC metrics, doublet_score/predicted_doublet, all Leiden cluster assignments, and cell_type_lvl1, with cell barcodes as row identifiers.

Source evidence: `adata.obs` at script completion; its endpoint columns are produced by sc.pp.scrublet, the sc.tl.leiden calls (including leiden_res_{0.02,0.50,2.00}), and the manual adata.obs['cell_type_lvl1'] mapping from leiden_res_0.02.

## Artifact: rank_genes_groups_leiden_res_0.50.csv

Differentially expressed genes per cluster of the leiden_res_0.50 clustering (Wilcoxon): gene names, scores, fold changes and p-values per group, in the stored rank order.

Source evidence: adata.uns['rank_genes_groups'] produced by sc.tl.rank_genes_groups(adata, groupby='leiden_res_0.50', method='wilcoxon'); serialized via scanpy's documented accessor sc.get.rank_genes_groups_df without recomputation.

## Worker-returned export code

```python
import os as _os

import pandas as _pd

# Endpoint exports (appended by the preparation stage)
_EXPORT_DIR = "/work/outputs"
_os.makedirs(_EXPORT_DIR, exist_ok=True)

# Terminal deliverable: the fully processed and annotated AnnData object.
# Holds filtered cells/genes, raw counts layer, log-normalized matrix,
# QC and doublet annotations, highly-variable-gene flags, PCA, neighborhood
# graph, UMAP, all Leiden clusterings, cell_type_lvl1, and the stored
# Wilcoxon rank_genes_groups results.
adata.write_h5ad(_os.path.join(_EXPORT_DIR, "adata_annotated.h5ad"))

# Per-cell annotation table from the final state of adata.obs (cell
# barcodes as row index): sample, QC metrics, doublet_score/
# predicted_doublet, leiden clusterings at all resolutions, cell_type_lvl1.
adata.obs.to_csv(_os.path.join(_EXPORT_DIR, "per_cell_annotations.csv"))

# Differential-expression endpoint: convert the existing
# adata.uns["rank_genes_groups"] result (Wilcoxon, leiden_res_0.50)
# to a long table with scanpy's documented accessor. Groups are taken
# from the stored result's own identifiers; no test is recomputed.
_rg_groups = adata.uns["rank_genes_groups"]["names"].dtype.names
_de_frames = []
for _rg in _rg_groups:
    _frame = sc.get.rank_genes_groups_df(
        adata, group=_rg, key="rank_genes_groups"
    )
    _frame.insert(0, "group", str(_rg))
    _de_frames.append(_frame)
_pd.concat(_de_frames, ignore_index=True).to_csv(
    _os.path.join(_EXPORT_DIR, "rank_genes_groups_leiden_res_0.50.csv"),
    index=False,
)
```

## Controller-assembled reference script

[reference.py](reference.py): untouched original script followed by the export code above.

## Controller-computed diff

```diff
--- baseline.py
+++ reference.py
@@ -321,3 +321,41 @@
 )
 
 # You may have noticed that the p-values found here are extremely low. This is due to the statistical test being performed considering each cell as an independent sample. For a more conservative approach you may want to consider "pseudo-bulking" your data by sample (*e.g.* `sc.get.aggregate(adata, by=["sample", "cell_type"], func="sum", layer="counts")`) and using a more powerful differential expression tool, like {doc}`pydeseq2 <pydeseq2:index>`.
+
+
+import os as _os
+
+import pandas as _pd
+
+# Endpoint exports (appended by the preparation stage)
+_EXPORT_DIR = "/work/outputs"
+_os.makedirs(_EXPORT_DIR, exist_ok=True)
+
+# Terminal deliverable: the fully processed and annotated AnnData object.
+# Holds filtered cells/genes, raw counts layer, log-normalized matrix,
+# QC and doublet annotations, highly-variable-gene flags, PCA, neighborhood
+# graph, UMAP, all Leiden clusterings, cell_type_lvl1, and the stored
+# Wilcoxon rank_genes_groups results.
+adata.write_h5ad(_os.path.join(_EXPORT_DIR, "adata_annotated.h5ad"))
+
+# Per-cell annotation table from the final state of adata.obs (cell
+# barcodes as row index): sample, QC metrics, doublet_score/
+# predicted_doublet, leiden clusterings at all resolutions, cell_type_lvl1.
+adata.obs.to_csv(_os.path.join(_EXPORT_DIR, "per_cell_annotations.csv"))
+
+# Differential-expression endpoint: convert the existing
+# adata.uns["rank_genes_groups"] result (Wilcoxon, leiden_res_0.50)
+# to a long table with scanpy's documented accessor. Groups are taken
+# from the stored result's own identifiers; no test is recomputed.
+_rg_groups = adata.uns["rank_genes_groups"]["names"].dtype.names
+_de_frames = []
+for _rg in _rg_groups:
+    _frame = sc.get.rank_genes_groups_df(
+        adata, group=_rg, key="rank_genes_groups"
+    )
+    _frame.insert(0, "group", str(_rg))
+    _de_frames.append(_frame)
+_pd.concat(_de_frames, ignore_index=True).to_csv(
+    _os.path.join(_EXPORT_DIR, "rank_genes_groups_leiden_res_0.50.csv"),
+    index=False,
+)
```

## Excluded outputs

- All plotting outputs (sc.pl.violin, sc.pl.scatter, sc.pl.highly_variable_genes, sc.pl.pca_variance_ratio, sc.pl.pca, all sc.pl.umap panels including the duplicated clustering panel, and both sc.pl.dotplot calls including rank_genes_groups_dotplot): figures rendered for display only; no figure capture or plot modification is added, so their numerical content is not separately exported.

- dc_cluster_genes: a head(5) subset of DE gene names for cluster 7 used only as input to the final UMAP plot; its content is fully contained in the exported rank_genes_groups CSV.

- adatas / per-sample sample_adata objects: per-sample intermediates merged into `adata`; remain in scope but are not the deliverable (post-filtering raw counts are preserved in adata.layers['counts'] within the h5ad export).

- marker_genes dict: curated prior-knowledge input for annotation, not a computed result.

- PCA coordinates, UMAP coordinates, HVG flags and connectivity graph: contained in adata_annotated.h5ad (obsm/var/obsp/uns) and not written as separate files.

## Unresolved assumptions

- Whether the full pipeline (scrublet, PCA, neighbors, UMAP, Leiden, Wilcoxon DE on roughly 16k cells by tens of thousands of genes) plus the h5ad write fits the 8 GiB memory and 600 s reference time limits is an execution-stage question; it is unverified here.

- h5ad write compatibility of pandas nullable/boolean columns (e.g. predicted_doublet) and sparse layers depends on the installed anndata version.

- sc.get.rank_genes_groups_df availability and column set depend on the installed scanpy version; the per-group loop was chosen for robustness but has not been executed.

- Exact size of adata_annotated.h5ad (two sparse matrix layers) is unverified; expected well within the 10 GiB disk limit.

- Availability of the figshare example data and pooch retrieval during network-enabled setup is owned by the execution stage and was not tested.
