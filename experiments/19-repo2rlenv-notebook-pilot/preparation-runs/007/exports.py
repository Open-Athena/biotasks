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