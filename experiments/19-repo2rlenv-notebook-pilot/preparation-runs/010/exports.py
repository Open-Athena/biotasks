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