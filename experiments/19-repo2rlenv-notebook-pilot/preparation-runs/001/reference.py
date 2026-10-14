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

# # Preprocessing and clustering

# Core scverse libraries
from __future__ import annotations

import anndata as ad

# Data retrieval
import pooch

import scanpy as sc

sc.settings.set_figure_params(dpi=50, facecolor="white")

# The data used in this basic preprocessing and clustering tutorial was collected from bone marrow mononuclear cells of healthy human donors and was part of [openproblem's NeurIPS 2021 benchmarking dataset](https://openproblems.bio/competitions/neurips_2021/) {cite}`Luecken2021`. The samples used in this tutorial were measured using the 10X Multiome Gene Expression and Chromatin Accessability kit. 
#
#
# We are reading in the count matrix into an {class}`~anndata.AnnData` object, which holds many slots for annotations and different representations of the data.
# See {doc}`anndata:tutorials/notebooks/getting-started` for a tutorial. 

# Input staging (offline reference run): the original notebook resolved the
# two input files by DOI via pooch (pooch.create + load_registry_from_doi,
# which query the figshare API over the network). The identical original
# input files are pre-staged under /inputs by the setup step, where the
# provider MD5 checksums and byte sizes were verified and SHA-256 digests
# recorded in /work/setup-inputs.json. The files, their order, the parser
# and all downstream reads are unchanged.
samples = {
    "s1d1": "/inputs/s1d1_filtered_feature_bc_matrix.h5",
    "s1d3": "/inputs/s1d3_filtered_feature_bc_matrix.h5",
}
adatas = {}

for sample_id, filename in samples.items():
    path = filename
    sample_adata = sc.read_10x_h5(path)
    sample_adata.var_names_make_unique()
    adatas[sample_id] = sample_adata

adata = ad.concat(adatas, label="sample")
adata.obs_names_make_unique()
print(adata.obs["sample"].value_counts())
adata

# Export: shared helper imports for all subsequent export snippets, the
# export directory, and the exact per-sample cell counts printed above.
import json as _json
import os as _os

import numpy as _np
import pandas as _pd

_OUTPUTS = "/work/outputs"
_os.makedirs(_OUTPUTS, exist_ok=True)
adata.obs["sample"].value_counts().rename_axis("sample").to_csv(
    _os.path.join(_OUTPUTS, "sample_cell_counts.csv")
)

# The data contains ~8,000 cells per sample and 36,601 measured genes. We'll now investigate these with a basic preprocessing and clustering workflow.

# ## Quality Control

# The scanpy function {func}`~scanpy.pp.calculate_qc_metrics` calculates common quality control (QC) metrics, which are largely based on `calculateQCMetrics` from scater {cite}`McCarthy2017`. One can pass specific gene population to {func}`~scanpy.pp.calculate_qc_metrics` in order to calculate proportions of counts for these populations. Mitochondrial, ribosomal and hemoglobin genes are defined by distinct prefixes as listed below. 

# mitochondrial genes, "MT-" for human, "mt-" for mouse
adata.var["mt"] = adata.var_names.str.startswith("MT-")
# ribosomal genes
adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL"))
# hemoglobin genes
adata.var["hb"] = adata.var_names.str.contains("^HB[^(P)]")

sc.pp.calculate_qc_metrics(
    adata, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True
)

# One can now inspect violin plots of some of the computed QC metrics:
#
# * the number of genes expressed in the count matrix
# * the total counts per cell
# * the percentage of counts in mitochondrial genes

sc.pl.violin(
    adata,
    ["n_genes_by_counts", "total_counts", "pct_counts_mt"],
    jitter=0.4,
    multi_panel=True,
)

# Additionally, it is useful to consider QC metrics jointly by inspecting a scatter plot colored by `pct_counts_mt`. 

sc.pl.scatter(adata, "total_counts", "n_genes_by_counts", color="pct_counts_mt")

# Export: per-cell QC metrics and per-gene QC annotations of the unfiltered
# dataset (underlying values of the QC violin plots and of this scatter plot).
_prefilter_n_obs, _prefilter_n_vars = adata.n_obs, adata.n_vars
adata.obs.to_csv(_os.path.join(_OUTPUTS, "qc_metrics_obs_prefilter.csv"))
adata.var.to_csv(_os.path.join(_OUTPUTS, "qc_metrics_var_prefilter.csv"))

# Based on the QC metric plots, one could now remove cells that have too many mitochondrial genes expressed or too many total counts by setting manual or automatic thresholds. However, sometimes what appears to be poor QC metrics can be driven by real biology so we suggest starting with a very permissive filtering strategy and revisiting it at a later point. We therefore now only filter cells with less than 100 genes expressed and genes that are detected in less than 3 cells. 
#
# Additionally, it is important to note that for datasets with multiple batches, quality control should be performed for each sample individually as quality control thresholds can vary substantially between batches. 

sc.pp.filter_cells(adata, min_genes=100)
sc.pp.filter_genes(adata, min_cells=3)

# Export: dataset dimensions across the source's own filtering step.
_postfilter_n_obs, _postfilter_n_vars = adata.n_obs, adata.n_vars
with open(_os.path.join(_OUTPUTS, "dataset_dimensions.json"), "w") as _fh:
    _json.dump(
        {
            "n_obs_prefilter": int(_prefilter_n_obs),
            "n_vars_prefilter": int(_prefilter_n_vars),
            "n_obs_postfilter": int(_postfilter_n_obs),
            "n_vars_postfilter": int(_postfilter_n_vars),
        },
        _fh,
        indent=2,
    )

# ### Doublet detection
#
# As a next step, we run a doublet detection algorithm. Identifying doublets is crucial as they can lead to misclassifications or distortions in downstream analysis steps. Scanpy contains the doublet detection method Scrublet {cite}`Wolock2019`. Scrublet predicts cell doublets using a nearest-neighbor classifier of observed transcriptomes and simulated doublets. {func}`scanpy.pp.scrublet` adds `doublet_score` and `predicted_doublet` to `.obs`. One can now either filter directly on `predicted_doublet` or use the `doublet_score` later during clustering to filter clusters with high doublet scores. 

sc.pp.scrublet(adata, batch_key="sample")

# Export: per-cell Scrublet results (doublet score and predicted doublet)
# together with the sample annotation.
adata.obs[["sample", "doublet_score", "predicted_doublet"]].to_csv(
    _os.path.join(_OUTPUTS, "scrublet_per_cell.csv")
)

# We can remove doublets by either filtering out the cells called as doublets, or waiting until we've done a clustering pass and filtering out any clusters with high doublet scores.

# :::{seealso}
# Alternative methods for doublet detection within the scverse ecosystem are [DoubletDetection](https://github.com/JonathanShor/DoubletDetection) and [SOLO](https://docs.scvi-tools.org/en/stable/user_guide/models/solo.html). You can read more about these in the [Doublet Detection chapter](https://www.sc-best-practices.org/preprocessing_visualization/quality_control.html#doublet-detection) of Single Cell Best Practices.
# :::

# ## Normalization
#
# The next preprocessing step is normalization. A common approach is count depth scaling with subsequent log plus one (log1p) transformation. Count depth scaling normalizes the data to a “size factor” such as the median count depth in the dataset, ten thousand (CP10k) or one million (CPM, counts per million). The size factor for count depth scaling can be controlled via `target_sum` in `pp.normalize_total`. We are applying median count depth normalization with log1p transformation (AKA log1PF).

# Saving count data
adata.layers["counts"] = adata.X.copy()

# Normalizing to median total counts
sc.pp.normalize_total(adata)
# Logarithmize the data
sc.pp.log1p(adata)

# Export: median total counts per cell - the effective count-depth scaling
# factor (target_sum) used by sc.pp.normalize_total - read from the preserved
# raw counts layer.
_cell_totals = _np.asarray(adata.layers["counts"].sum(axis=1)).ravel()
with open(_os.path.join(_OUTPUTS, "normalization_target_sum.json"), "w") as _fh:
    _json.dump(
        {
            "n_cells": int(_cell_totals.size),
            "median_total_counts_per_cell": float(_np.median(_cell_totals)),
        },
        _fh,
        indent=2,
    )

# ## Feature selection
#
# As a next step, we want to reduce the dimensionality of the dataset and only include the most informative genes. This step is commonly known as feature selection. The scanpy function `pp.highly_variable_genes` annotates highly variable genes by reproducing the implementations of Seurat {cite}`Satija2015`, Cell Ranger {cite}`Zheng2017`, and Seurat v3 {cite}`Stuart2019` depending on the chosen `flavor`. 

sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")

sc.pl.highly_variable_genes(adata)

# Export: gene-level annotations after filtering (gene ids, QC flags,
# n_cells and the highly-variable-gene statistics plotted above).
_n_highly_variable = int(adata.var["highly_variable"].sum())
adata.var.to_csv(_os.path.join(_OUTPUTS, "var_annotations_postfilter.csv"))

# ## Dimensionality Reduction
# Reduce the dimensionality of the data by running principal component analysis (PCA), which reveals the main axes of variation and denoises the data.

sc.tl.pca(adata)

# Let us inspect the contribution of single PCs to the total variance in the data. This gives us information about how many PCs we should consider in order to compute the neighborhood relations of cells, e.g. used in the clustering function {func}`~scanpy.tl.leiden` or {func}`~scanpy.tl.tsne`. In our experience, there does not seem to be signifigant downside to overestimating the numer of principal components.

sc.pl.pca_variance_ratio(adata, n_pcs=50, log=True)

# Export: per-component PCA variance and variance ratio (underlying data of
# the variance-ratio plot above).
_pca_summary = _pd.DataFrame(
    {
        "pc": _np.arange(1, len(adata.uns["pca"]["variance_ratio"]) + 1),
        "variance_ratio": adata.uns["pca"]["variance_ratio"],
        "variance": adata.uns["pca"]["variance"],
    }
)
_pca_summary.to_csv(_os.path.join(_OUTPUTS, "pca_variance_ratio.csv"), index=False)

# You can also plot the principal components to see if there are any potentially undesired features (e.g. batch, QC metrics) driving signifigant variation in this dataset. In this case, there isn't anything too alarming, but it's a good idea to explore this.

sc.pl.pca(
    adata,
    color=["sample", "sample", "pct_counts_mt", "pct_counts_mt"],
    dimensions=[(0, 1), (2, 3), (0, 1), (2, 3)],
    ncols=2,
    size=2,
)

# ## Nearest neighbor graph construction and visualization
#
# Let us compute the neighborhood graph of cells using the PCA representation of the data matrix.

sc.pp.neighbors(adata)

# Export: parameter record of the neighborhood graph construction.
with open(_os.path.join(_OUTPUTS, "neighbors_params.json"), "w") as _fh:
    _json.dump(
        {
            "params": {
                str(_k): str(_v)
                for _k, _v in adata.uns["neighbors"]["params"].items()
            }
        },
        _fh,
        indent=2,
    )

# This graph can then be embedded in two dimensions for visualiztion with UMAP {cite:p}`McInnes2018`:

sc.tl.umap(adata)

# We can now visualize the UMAP according to the `sample`. 

sc.pl.umap(
    adata,
    color="sample",
    # Setting a smaller point size to get prevent overlap
    size=2,
)

# Export: UMAP coordinates per cell (shared geometry of all later UMAP
# panels in the notebook).
_umap_df = _pd.DataFrame(
    adata.obsm["X_umap"], index=adata.obs_names, columns=["umap_1", "umap_2"]
)
_umap_df.index.name = "obs_names"
_umap_df.to_csv(_os.path.join(_OUTPUTS, "umap_embedding.csv"))

# Even though the data considered in this tutorial includes two different samples, we only observe a minor batch effect and we can continue with clustering and annotation of our data. 
#
# If you inspect batch effects in your UMAP it can be beneficial to integrate across samples and perform batch correction/integration. We recommend checking out [`scanorama`](https://github.com/brianhie/scanorama) and [`scvi-tools`](https://scvi-tools.org) for batch integration.

# ## Clustering
#
# As with Seurat and many other frameworks, we recommend the Leiden graph-clustering method (community detection based on optimizing modularity) {cite}`Traag2019`. Note that Leiden clustering directly clusters the neighborhood graph of cells, which we already computed in the previous section.

# Using the igraph implementation and a fixed number of iterations can be significantly faster,
# especially for larger datasets
sc.tl.leiden(adata, flavor="igraph", n_iterations=2)

sc.pl.umap(adata, color=["leiden"])

# ```{dropdown} How do I save a plot?
# You can save a plot by directly accessing the returned Matplotlib figure:
# ````python
# sc.pl.umap(adata, color=["leiden"], show).figure.savefig("output_path.ext")
# ````
# ```

# ## Re-assess quality control and cell filtering 
#
# As indicated before, we will now re-assess our filtering strategy by visualizing different QC metrics using UMAP. 

sc.pl.umap(
    adata,
    color=["leiden", "predicted_doublet", "doublet_score"],
    # increase horizontal space between panels
    wspace=0.5,
    size=3,
)

sc.pl.umap(
    adata,
    color=["leiden", "log1p_total_counts", "pct_counts_mt", "log1p_n_genes_by_counts"],
    wspace=0.5,
    ncols=2,
)

# ## Manual cell-type annotation

# :::{note}
# This section of the tutorial is expanded upon using prior knowledge resources like automated assignment and gene enrichment in the scverse tutorial [here](https://scverse-tutorials.readthedocs.io/page/notebooks/basic-scrna-tutorial.html#cell-type-annotation)
# :::

# Cell type annotation is laborous and repetitive task, one which typically requires multiple rounds of subclustering and re-annotation. It's difficult to show the entirety of the process in this tutorial, but we aim to show how the tools scanpy provides assist in this process.

# We have now reached a point where we have obtained a set of cells with decent quality, and we can proceed to their annotation to known cell types. Typically, this is done using genes that are exclusively expressed by a given cell type, or in other words these genes are the marker genes of the cell types, and are thus used to distinguish the heterogeneous groups of cells in our data. Previous efforts have collected and curated various marker genes into available resources, such as [CellMarker](http://bio-bigdata.hrbmu.edu.cn/CellMarker/), [TF-Marker](http://bio.liclab.net/TF-Marker/), and [PanglaoDB](https://panglaodb.se/). The [cellxgene gene expression tool](https://cellxgene.cziscience.com/gene-expression) can also be quite useful to see which cell types a gene has been expressed in across many existing datasets.

# Commonly and classically, cell type annotation uses those marker genes subsequent to the grouping of the cells into clusters. So, let's generate a set of clustering solutions which we can then use to annotate our cell types. Here, we will use the Leiden clustering algorithm which will extract cell communities from our nearest neighbours graph.

for res in [0.02, 0.5, 2.0]:
    sc.tl.leiden(
        adata, key_added=f"leiden_res_{res:4.2f}", resolution=res, flavor="igraph"
    )

# Notably, the number of clusters that we define is largely arbitrary, and so is the `resolution` parameter that we use to control for it. As such, the number of clusters is ultimately bound to the stable and biologically-meaningful groups that we can ultimately distringuish, typically done by experts in the corresponding field or by using expert-curated prior knowledge in the form of markers.

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

# Though UMAPs should not be over-interpreted, here we can already see that in the highest resolution our data is over-clustered, while the lowest resolution is likely grouping cells which belong to distinct cell identities.

# ### Marker gene set

# Let's define a set of marker genes for the main cell types that we expect to see in this dataset. These were adapted from [Single Cell Best Practices annotation chapter](https://www.sc-best-practices.org/cellular_structure/annotation.html), for a more detailed overview and best practices in cell type annotation, we refer the user to it.

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

# Export: the source marker-gene dictionary and the underlying dotplot values
# for the coarsest clustering (per gene and cluster: mean log-normalized
# expression, fraction of expressing cells, and the per-gene [0,1]-scaled mean
# matching standard_scale="var"). Only genes present in the filtered data are
# included, mirroring the genes the dotplot can show.
with open(_os.path.join(_OUTPUTS, "marker_genes.json"), "w") as _fh:
    _json.dump(marker_genes, _fh, indent=2)


def _export_grouped_gene_values(_genes, _groupby, _path):
    import scipy.sparse as _sps

    _present_genes = [str(_gene) for _gene in _genes if str(_gene) in adata.var_names]
    _agg = sc.get.aggregate(
        adata[:, _present_genes].copy(), by=_groupby, func=("mean", "count_nonzero")
    )
    if _groupby in _agg.obs.columns:
        _groups = [str(_group) for _group in _agg.obs[_groupby].tolist()]
    else:
        _groups = [str(_group) for _group in _agg.obs_names]

    def _to_dense(_matrix):
        return _matrix.toarray() if _sps.issparse(_matrix) else _np.asarray(_matrix)

    _mean = _to_dense(_agg.layers["mean"]).astype(float)
    _nonzero = _to_dense(_agg.layers["count_nonzero"]).astype(float)
    _n_cells = (
        adata.obs[_groupby].value_counts().reindex(_groups).to_numpy(dtype=float)
    )
    _mins = _mean.min(axis=0)
    _spans = _mean.max(axis=0) - _mins
    _spans[_spans == 0] = 1.0
    _scaled = (_mean - _mins) / _spans
    _records = []
    for _i, _group in enumerate(_groups):
        for _j, _gene in enumerate(_present_genes):
            _records.append(
                {
                    "group": _group,
                    "gene": _gene,
                    "n_cells_in_group": float(_n_cells[_i]),
                    "mean_expression": float(_mean[_i, _j]),
                    "fraction_expressing": float(_nonzero[_i, _j] / _n_cells[_i]),
                    "mean_expression_scaled_var": float(_scaled[_i, _j]),
                }
            )
    _pd.DataFrame.from_records(_records).to_csv(_path, index=False)


_marker_gene_list = sorted(
    {_gene for _genes in marker_genes.values() for _gene in _genes}
)
_export_grouped_gene_values(
    _marker_gene_list,
    "leiden_res_0.02",
    _os.path.join(_OUTPUTS, "marker_dotplot_leiden_res_0.02.csv"),
)

# There are fairly clear patterns of expression for our markers show here, which we can use to label our coarsest clustering with broad lineages.

adata.obs["cell_type_lvl1"] = adata.obs["leiden_res_0.02"].map({
    "0": "Lymphocytes",
    "1": "Monocytes",
    "2": "B Cells",
    "3": "Erythroid",
    "4": "Erythroid",
})

sc.pl.dotplot(adata, marker_genes, groupby="leiden_res_0.50", standard_scale="var")

# Export: underlying dotplot values for the intermediate-resolution
# clustering used for cell-type annotation.
_export_grouped_gene_values(
    _marker_gene_list,
    "leiden_res_0.50",
    _os.path.join(_OUTPUTS, "marker_dotplot_leiden_res_0.50.csv"),
)

# This seems like a resolution that suitable to distinguish most of the different cell types in our data. As such, let's try to annotate those by manually using the dotplot above, together with the UMAP of our clusters. Ideally, one would also look specifically into each cluster, and attempt to subcluster those if required.

# ### Differentially-expressed Genes as Markers

# Furthermore, one can also calculate marker genes per cluster and then look up whether we can link those marker genes to any known biology, such as cell types and/or states. This is typically done using simple statistical tests, such as Wilcoxon and t-test, for each cluster vs the rest.

# Obtain cluster-specific differentially expressed genes
sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")

# Export: the complete Wilcoxon DEG ranking for every cluster of
# leiden_res_0.50 (each gene vs the rest of the cells), extracted with the
# documented per-group getter also used by the notebook.
_deg_groups = list(adata.uns["rank_genes_groups"]["names"].dtype.names)
_deg_frames = []
for _deg_group in _deg_groups:
    _deg_df = sc.get.rank_genes_groups_df(adata, group=_deg_group)
    _deg_df.insert(0, "group", str(_deg_group))
    _deg_frames.append(_deg_df)
_pd.concat(_deg_frames, ignore_index=True).to_csv(
    _os.path.join(_OUTPUTS, "deg_wilcoxon_leiden_res_0.50.csv"), index=False
)

# We can then visualize the top 5 differentially-expressed genes on a dotplot.

sc.pl.rank_genes_groups_dotplot(
    adata, groupby="leiden_res_0.50", standard_scale="var", n_genes=5
)

# Export: the five top-ranked DEGs per cluster (the gene axis of the dotplot
# above) and the underlying per-(cluster, gene) values it displays.
_top5_by_group = {
    str(_deg_group): [
        str(_gene)
        for _gene in sc.get.rank_genes_groups_df(adata, group=_deg_group)["names"].head(5)
    ]
    for _deg_group in _deg_groups
}
with open(_os.path.join(_OUTPUTS, "deg_top5_per_group.json"), "w") as _fh:
    _json.dump(_top5_by_group, _fh, indent=2)
_export_grouped_gene_values(
    sorted({_gene for _genes in _top5_by_group.values() for _gene in _genes}),
    "leiden_res_0.50",
    _os.path.join(_OUTPUTS, "deg_top5_dotplot_values.csv"),
)

# We can then use these genes to figure out what cell types we're looking at. For example, Cluster 7 is expressing [*NKG7*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=NKG7&keywords=nkg7) and [*GNLY*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=GNLY&keywords=GNLY), suggesting these are [NK cells](https://en.wikipedia.org/wiki/Natural_killer_cell).

# To create your own plots, or use a more automated approach, the differentially expressed genes can be extracted in a convenient format with {func}`scanpy.get.rank_genes_groups_df`

sc.get.rank_genes_groups_df(adata, group="7").head(5)

dc_cluster_genes = sc.get.rank_genes_groups_df(adata, group="7").head(5)["names"]

# Export: the exact top-5 DEG table displayed for cluster "7" and the
# ordered gene list mapped onto the following UMAP panels.
_g7_top5 = sc.get.rank_genes_groups_df(adata, group="7").head(5).copy()
_g7_top5.insert(0, "group", "7")
_g7_top5.to_csv(_os.path.join(_OUTPUTS, "deg_group_7_top5.csv"), index=False)
with open(_os.path.join(_OUTPUTS, "dc_cluster_7_genes.json"), "w") as _fh:
    _json.dump([str(_gene) for _gene in dc_cluster_genes.tolist()], _fh, indent=2)
sc.pl.umap(
    adata,
    color=[*dc_cluster_genes, "leiden_res_0.50"],
    legend_loc="on data",
    frameon=False,
    ncols=3,
)

# Final exports: complete per-cell metadata (all obs columns), label counts
# for every categorical result, the finalized dataset dimension checkpoints,
# and the complete final AnnData object (executed last so every other artifact
# is already on disk).
_obs_out = adata.obs.copy()
_obs_out.index.name = "obs_names"
_obs_out.to_csv(_os.path.join(_OUTPUTS, "cells_metadata.csv"))

_label_counts = {}
for _label_col in [
    "sample",
    "predicted_doublet",
    "leiden",
    "leiden_res_0.02",
    "leiden_res_0.50",
    "leiden_res_2.00",
    "cell_type_lvl1",
]:
    _label_counts[_label_col] = {
        str(_label): int(_count)
        for _label, _count in adata.obs[_label_col].value_counts().items()
    }
with open(_os.path.join(_OUTPUTS, "clustering_label_counts.json"), "w") as _fh:
    _json.dump(_label_counts, _fh, indent=2)

with open(_os.path.join(_OUTPUTS, "dataset_dimensions.json"), "w") as _fh:
    _json.dump(
        {
            "n_obs_prefilter": int(_prefilter_n_obs),
            "n_vars_prefilter": int(_prefilter_n_vars),
            "n_obs_postfilter": int(_postfilter_n_obs),
            "n_vars_postfilter": int(_postfilter_n_vars),
            "n_highly_variable_genes": int(_n_highly_variable),
            "n_obs_final": int(adata.n_obs),
            "n_vars_final": int(adata.n_vars),
        },
        _fh,
        indent=2,
    )

adata.write_h5ad(_os.path.join(_OUTPUTS, "adata_final.h5ad"))

# You may have noticed that the p-values found here are extremely low. This is due to the statistical test being performed considering each cell as an independent sample. For a more conservative approach you may want to consider "pseudo-bulking" your data by sample (*e.g.* `sc.get.aggregate(adata, by=["sample", "cell_type"], func="sum", layer="counts")`) and using a more powerful differential expression tool, like {doc}`pydeseq2 <pydeseq2:index>`.
