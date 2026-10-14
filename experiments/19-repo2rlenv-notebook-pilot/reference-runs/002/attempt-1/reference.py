# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: nomarker
#       format_version: '1.0'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: notebook
#     language: python
#     name: python3
# ---

# Core scverse libraries
from __future__ import annotations

import anndata as ad

# Data retrieval
import pooch

import scanpy as sc

sc.settings.set_figure_params(dpi=50, facecolor="white")

# export helpers appended for the reference run only; they do not alter the analysis
import json as _json
from pathlib import Path as _Path

import pandas as _pd

EXPORT_DIR = _Path("/work/outputs")


def _save_csv(frame, relname, **kwargs):
    target = EXPORT_DIR / relname
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, **kwargs)


def _save_json(obj, relname):
    target = EXPORT_DIR / relname
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as fh:
        _json.dump(obj, fh, indent=2, default=str)


def _save_figures(relname, dpi=150):
    import matplotlib.pyplot as _plt

    (EXPORT_DIR / relname).parent.mkdir(parents=True, exist_ok=True)
    nums = list(_plt.get_fignums())
    stem = relname[:-4] if relname.endswith(".png") else relname
    for i, num in enumerate(nums):
        fig = _plt.figure(num)
        suffix = "" if len(nums) == 1 else f"_fig{i + 1}"
        fig.savefig(EXPORT_DIR / f"{stem}{suffix}.png", dpi=dpi, bbox_inches="tight")
        _plt.close(fig)

# reference-run offline staging: in the source this pooch.create +
# load_registry_from_doi block resolves the figshare DOI registry over the
# network. It is replaced wholesale by a local loader backed by the
# checksum-verified copies staged under /inputs during setup, so
# EXAMPLE_DATA.fetch(filename) still returns the very same files while no
# DOI registry or network is contacted. This is input retrieval staging only.
import pathlib

_INPUTS = pathlib.Path("/inputs")


class _StagedExampleData:
    def fetch(self, filename):
        path = _INPUTS / filename
        if not path.is_file():
            raise FileNotFoundError(f"staged input missing: {path}")
        return str(path)


EXAMPLE_DATA = _StagedExampleData()

samples = {
    "s1d1": "s1d1_filtered_feature_bc_matrix.h5",
    "s1d3": "s1d3_filtered_feature_bc_matrix.h5",
}
adatas = {}

for sample_id, filename in samples.items():
    path = EXAMPLE_DATA.fetch(filename)
    sample_adata = sc.read_10x_h5(path)
    sample_adata.var_names_make_unique()
    adatas[sample_id] = sample_adata

adata = ad.concat(adatas, label="sample")
adata.obs_names_make_unique()
print(adata.obs["sample"].value_counts())
adata

_save_csv(adata.obs["sample"].value_counts(), "load/sample_value_counts.csv")
_save_json(
    {
        "n_obs": int(adata.n_obs),
        "n_vars": int(adata.n_vars),
        "samples": sorted(adata.obs["sample"].unique().tolist()),
    },
    "load/adata_consolidated_shape.json",
)

# mitochondrial genes, "MT-" for human, "mt-" for mouse
adata.var["mt"] = adata.var_names.str.startswith("MT-")
# ribosomal genes
adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL"))
# hemoglobin genes
adata.var["hb"] = adata.var_names.str.contains("^HB[^(P)]")

sc.pp.calculate_qc_metrics(
    adata, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True
)

_save_csv(adata.obs, "qc/obs_qc_metrics.csv", index_label="obs_id")
_save_csv(adata.var, "qc/var_qc_annotations.csv", index_label="var_id")

sc.pl.violin(
    adata,
    ["n_genes_by_counts", "total_counts", "pct_counts_mt"],
    jitter=0.4,
    multi_panel=True,
)

_save_figures("qc/qc_metrics_violin.png")

sc.pl.scatter(adata, "total_counts", "n_genes_by_counts", color="pct_counts_mt")

_save_figures("qc/scatter_total_counts_vs_n_genes_by_counts.png")

sc.pp.filter_cells(adata, min_genes=100)
sc.pp.filter_genes(adata, min_cells=3)

sc.pp.scrublet(adata, batch_key="sample")

_save_json(
    {
        "n_obs_after_filtering": int(adata.n_obs),
        "n_vars_after_filtering": int(adata.n_vars),
        "filter_cells_min_genes": 100,
        "filter_genes_min_cells": 3,
    },
    "filtering/post_filter_shape.json",
)
_save_csv(
    adata.obs[["sample", "doublet_score", "predicted_doublet"]],
    "doublet_detection/obs_doublet_scores.csv",
    index_label="obs_id",
)

# Saving count data
adata.layers["counts"] = adata.X.copy()

# Normalizing to median total counts
sc.pp.normalize_total(adata)
# Logarithmize the data
sc.pp.log1p(adata)

sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")

_save_csv(adata.var, "feature_selection/var_highly_variable_genes.csv", index_label="var_id")

sc.pl.highly_variable_genes(adata)

_save_figures("feature_selection/highly_variable_genes.png")

sc.tl.pca(adata)

_save_csv(
    _pd.DataFrame(adata.obsm["X_pca"], index=adata.obs_names).rename(
        columns=lambda c: f"PC{c + 1}"
    ),
    "pca/obs_x_pca.csv",
    index_label="obs_id",
)
_save_csv(
    _pd.DataFrame(
        adata.varm["PCs"],
        index=adata.var_names,
        columns=[f"PC{i + 1}" for i in range(adata.varm["PCs"].shape[1])],
    ),
    "pca/varm_pca_loadings.csv",
    index_label="var_id",
)
_save_json(
    {
        "pca_variance_ratio": adata.uns["pca"]["variance_ratio"].tolist(),
        "pca_variance": adata.uns["pca"]["variance"].tolist(),
    },
    "pca/pca_variance.json",
)

sc.pl.pca_variance_ratio(adata, n_pcs=50, log=True)

_save_figures("pca/pca_variance_ratio.png")

sc.pl.pca(
    adata,
    color=["sample", "sample", "pct_counts_mt", "pct_counts_mt"],
    dimensions=[(0, 1), (2, 3), (0, 1), (2, 3)],
    ncols=2,
    size=2,
)

_save_figures("pca/pca_scatter_colored.png")

sc.pp.neighbors(adata)

sc.tl.umap(adata)

sc.pl.umap(
    adata,
    color="sample",
    # Setting a smaller point size to get prevent overlap
    size=2,
)

_neighbors_export = {}
for _k, _v in dict(adata.uns["neighbors"]).items():
    if _k == "params":
        _neighbors_export["params"] = {
            str(_pk): (
                _pv if isinstance(_pv, (bool, int, float, str)) or _pv is None else str(_pv)
            )
            for _pk, _pv in dict(_v).items()
        }
    else:
        _sh = getattr(_v, "shape", None)
        _neighbors_export[str(_k)] = {
            "type": type(_v).__name__,
            "shape": (list(_sh) if _sh is not None else None),
        }
_save_json(_neighbors_export, "embedding/neighbors_config.json")
_save_csv(
    _pd.DataFrame(
        adata.obsm["X_umap"], index=adata.obs_names, columns=["UMAP1", "UMAP2"]
    ),
    "embedding/obs_x_umap.csv",
    index_label="obs_id",
)
_save_figures("embedding/umap_sample.png")

# Using the igraph implementation and a fixed number of iterations can be significantly faster,
# especially for larger datasets
sc.tl.leiden(adata, flavor="igraph", n_iterations=2)

sc.pl.umap(adata, color=["leiden"])

_save_figures("clustering/umap_leiden.png")

sc.pl.umap(
    adata,
    color=["leiden", "predicted_doublet", "doublet_score"],
    # increase horizontal space between panels
    wspace=0.5,
    size=3,
)

_save_figures("clustering/umap_leiden_doublet_qc.png")

sc.pl.umap(
    adata,
    color=["leiden", "log1p_total_counts", "pct_counts_mt", "log1p_n_genes_by_counts"],
    wspace=0.5,
    ncols=2,
)

_save_figures("clustering/umap_leiden_qc_metrics.png")

for res in [0.02, 0.5, 2.0]:
    sc.tl.leiden(
        adata, key_added=f"leiden_res_{res:4.2f}", resolution=res, flavor="igraph"
    )

sc.pl.umap(
    adata,
    color=["leiden_res_0.02", "leiden_res_0.50", "leiden_res_2.00"],
    legend_loc="on data",
)

sc.pl.umap(
    adata,
    color=["leiden_res_0.02", "leiden_res_0.50", "leiden_res_2.00"],
    legend_loc="on data",
)

# the source repeats the identical resolution-comparison UMAP twice; save
# each figure still open from these two calls under its own name
import matplotlib.pyplot as _plt

(EXPORT_DIR / "clustering").mkdir(parents=True, exist_ok=True)
for _i, _num in enumerate(list(_plt.get_fignums())):
    _fig = _plt.figure(_num)
    _fig.savefig(
        EXPORT_DIR / f"clustering/umap_leiden_resolution_comparison_{_i + 1}.png",
        dpi=150,
        bbox_inches="tight",
    )
    _plt.close(_fig)

marker_genes = {
    "CD14+ Mono": ["FCN1", "CD14"],
    "CD16+ Mono": ["TCF7L2", "FCGR3A", "LYN"],
    # Note: DMXL2 should be negative
    "cDC2": ["CST3", "COTL1", "LYZ", "DMXL2", "CLEC10A", "FCER1A"],
    "Erythroblast": ["MKI67", "HBA1", "HBB"],
    # Note HBM and GYPA are negative markers
    "Proerythroblast": ["CDK6", "SYNGR1", "HBM", "GYPA"],
    "NK": ["GNLY", "NKG7", "CD247", "FCER1G", "TYROBP", "KLRG1", "FCGR3A"],
    "ILC": ["ID2", "PLCG2", "GNLY", "SYNE1"],
    "Naive CD20+ B": ["MS4A1", "IL4R", "IGHD", "FCRL1", "IGHM"],
    # Note IGHD and IGHM are negative markers
    "B cells": [
        "MS4A1",
        "ITGB1",
        "COL4A4",
        "PRDM1",
        "IRF4",
        "PAX5",
        "BCL11A",
        "BLK",
        "IGHD",
        "IGHM",
    ],
    "Plasma cells": ["MZB1", "HSP90B1", "FNDC3B", "PRDM1", "IGKC", "JCHAIN"],
    # Note PAX5 is a negative marker
    "Plasmablast": ["XBP1", "PRDM1", "PAX5"],
    "CD4+ T": ["CD4", "IL7R", "TRBC2"],
    "CD8+ T": ["CD8A", "CD8B", "GZMK", "GZMA", "CCL5", "GZMB", "GZMH", "GZMA"],
    "T naive": ["LEF1", "CCR7", "TCF7"],
    "pDC": ["GZMB", "IL3RA", "COBLL1", "TCF4"],
}

sc.pl.dotplot(adata, marker_genes, groupby="leiden_res_0.02", standard_scale="var")

_save_figures("annotation/dotplot_marker_genes_leiden_res_0.02.png")

adata.obs["cell_type_lvl1"] = adata.obs["leiden_res_0.02"].map({
    "0": "Lymphocytes",
    "1": "Monocytes",
    "2": "B Cells",
    "3": "Erythroid",
    "4": "Erythroid",
})

sc.pl.dotplot(adata, marker_genes, groupby="leiden_res_0.50", standard_scale="var")

_save_figures("annotation/dotplot_marker_genes_leiden_res_0.50.png")
_save_csv(
    adata.obs[
        [
            "leiden",
            "leiden_res_0.02",
            "leiden_res_0.50",
            "leiden_res_2.00",
            "cell_type_lvl1",
        ]
    ],
    "clustering/obs_leiden_clusters.csv",
    index_label="obs_id",
)

# Obtain cluster-specific differentially expressed genes
sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")

_deg_frames = []
for _grp in adata.obs["leiden_res_0.50"].cat.categories:
    _df = sc.get.rank_genes_groups_df(adata, group=_grp)
    _df.insert(0, "group", _grp)
    _deg_frames.append(_df)
_save_csv(
    _pd.concat(_deg_frames, ignore_index=True),
    "deg/rank_genes_groups_leiden_res_0.50_wilcoxon.csv",
)

sc.pl.rank_genes_groups_dotplot(
    adata, groupby="leiden_res_0.50", standard_scale="var", n_genes=5
)

_save_figures("deg/rank_genes_groups_dotplot_top5.png")

sc.get.rank_genes_groups_df(adata, group="7").head(5)

dc_cluster_genes = sc.get.rank_genes_groups_df(adata, group="7").head(5)["names"]
sc.pl.umap(
    adata,
    color=[*dc_cluster_genes, "leiden_res_0.50"],
    legend_loc="on data",
    frameon=False,
    ncols=3,
)

_save_figures("deg/umap_cluster7_top_genes.png")
_cluster7_top5 = sc.get.rank_genes_groups_df(adata, group="7").head(5)
_save_csv(_cluster7_top5, "deg/cluster7_top5_de_genes.csv")
_save_json(
    [str(_g) for _g in _cluster7_top5["names"].tolist()],
    "deg/cluster7_top5_gene_names.json",
)
_save_csv(adata.obs, "final/obs_final_annotations.csv", index_label="obs_id")
(EXPORT_DIR / "final").mkdir(parents=True, exist_ok=True)
adata.write_h5ad(EXPORT_DIR / "final/adata_final.h5ad", compression="gzip")
