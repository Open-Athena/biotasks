# Preparation worker output

Rendered from [plan.json](plan.json). Generated commands and source edits have not been executed. Only structural checks have run; scientific fidelity is unreviewed.

## Decision

prepare

The notebook is one sequential scanpy workflow over two figshare-hosted 10X h5 matrices for which the provenance supplies URLs, sizes and provider MD5s, so a faithful offline reference is possible: setup stages the two files into /inputs, and the endpoints are preserved by serializing existing result objects. Consequential script changes: (1) the DOI-based pooch registry (`pooch.create(path=pooch.os_cache('scverse_tutorials'), ...)` + `EXAMPLE_DATA.load_registry_from_doi()`, both network operations) is replaced by a pooch registry over the two staged /inputs files using the provider MD5s, so `EXAMPLE_DATA.fetch(filename)` and the whole loading loop are unchanged while the data load is now offline and hash-checked; (2) the standalone result `sc.get.rank_genes_groups_df(adata, group='7').head(5)` is assigned to a fresh variable `rank_genes_groups_7_head` (call and arguments untouched) so it can be exported; (3) an export block is appended after the last analysis statement, writing the complete final annotated AnnData to /work/outputs/adata_annotated.h5ad and the cluster-7 top-5 DE table to CSV, adding only a `pathlib` import. No parameters, thresholds, filtering, plotting calls, ordering or randomness settings were changed, and no reductions added.

## Environment rationale

Directly imported third-party modules are scanpy, anndata and pooch; umap-learn and igraph are declared because scanpy treats them as optional but the script requires them. scanpy is floored at >=1.10 (native `pp.scrublet(..., batch_key=...)` and `tl.leiden(..., flavor='igraph', n_iterations=...)`) and capped <2 against future breaking majors. umap-learn is required by `pp.neighbors` (default method 'umap' via pynndescent) and `tl.umap`. igraph is required by all four `tl.leiden` calls; leidenalg is declared as a companion since scanpy's leiden module may import it on some code paths, although every call uses the igraph flavor. pooch remains in use, purely offline: the explicit MD5 registry lets `fetch` verify the staged files and return local paths. h5py, pandas, numpy, scipy, scikit-learn, seaborn, numba and pynndescent arrive transitively via scanpy/anndata/umap-learn and are not re-declared. No Debian packages are needed: igraph's Python wheels bundle the C core and all other compiled dependencies ship manylinux wheels, so system_packages is empty. Compatibility questions only execution can settle: whether the stack resolves on the base image's CPython 3.13.13 (notably numba/llvmlite via umap-learn, igraph and h5py cp313 wheels), and whether the resolved versions reproduce the tutorial's expected cluster labels — the source notebook itself declares no versions and was never executed (execution_mode off).

## Python dependencies

```toml
[project]
name = "scanpy-basics-clustering-reference"
version = "0.1.0"
description = "Reference environment for the scverse/scanpy 'Preprocessing and clustering' tutorial (basics/clustering.ipynb @ 8c1463d5d97272d5811ad3f4efb57483e23b4c7e)."
requires-python = ">=3.11"
dependencies = [
    "scanpy>=1.10,<2",
    "anndata>=0.10",
    "pooch>=1.7",
    "umap-learn>=0.5.5",
    "igraph>=0.11",
    "leidenalg>=0.10",
]

```

## System packages

```json
[]
```

## Input staging script

```sh
# Stage the original input data for the Scanpy preprocessing & clustering
# reference run. Runs after dependency installation, with the virtual
# environment's python on PATH; network is available only here. Downloads the
# two 10X filtered feature matrices from figshare
# (doi:10.6084/m9.figshare.22716739.v1, NeurIPS 2021 benchmark dataset,
# CC BY 4.0), verifies them against the provider-supplied MD5 checksums and
# sizes, and writes a SHA-256 receipt to /work/setup-inputs.json.

set -eu

python - <<'PY'
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

DEST_DIR = Path("/inputs")
DEST_DIR.mkdir(parents=True, exist_ok=True)

FILES = [
    {
        "url": "https://ndownloader.figshare.com/files/40347877",
        "name": "s1d1_filtered_feature_bc_matrix.h5",
        "md5": "a99285913ea3f3d22600d3d2f8a88e34",
        "bytes": 22848647,
    },
    {
        "url": "https://ndownloader.figshare.com/files/40347880",
        "name": "s1d3_filtered_feature_bc_matrix.h5",
        "md5": "825f7f7578e3dc0b8955f5a97a402338",
        "bytes": 20432298,
    },
]


def checksums(path):
    data = path.read_bytes()
    return data, hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()


def verify_or_download(rec):
    dest = DEST_DIR / rec["name"]
    if dest.is_file():
        data, md5, _ = checksums(dest)
        if len(data) == rec["bytes"] and md5 == rec["md5"]:
            return dest
    tmp = dest.with_name(dest.name + ".part")
    print(f"Downloading {rec['name']} from {rec['url']} ...")
    request = urllib.request.Request(
        rec["url"], headers={"User-Agent": "reference-setup"}
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response, open(
            tmp, "wb"
        ) as fh:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
        data, md5, _ = checksums(tmp)
        if len(data) != rec["bytes"]:
            sys.exit(
                f"{rec['name']}: size mismatch (expected {rec['bytes']}, got {len(data)})"
            )
        if md5 != rec["md5"]:
            sys.exit(
                f"{rec['name']}: MD5 mismatch (expected {rec['md5']}, got {md5})"
            )
        tmp.replace(dest)
    finally:
        if tmp.is_file():
            tmp.unlink()
    return dest


receipt = {"files": []}
for rec in FILES:
    dest = verify_or_download(rec)
    _, _, sha256 = checksums(dest)
    receipt["files"].append(
        {"local_path": str(dest), "source": rec["url"], "sha256": sha256}
    )

Path("/work/setup-inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(
    f"Staged {len(receipt['files'])} input files in /inputs; "
    "receipt written to /work/setup-inputs.json"
)
PY

```

## Controller setup script

```sh
#!/bin/sh
set -eu
cd /work
export DEBIAN_FRONTEND=noninteractive
python -m pip install --disable-pip-version-check uv==0.12.21
export UV_PROJECT_ENVIRONMENT=/work/venv
export UV_PYTHON_DOWNLOADS=never
uv lock --project /work/environment --python "$(command -v python)"
uv sync --project /work/environment --locked --no-dev --no-install-project --python "$(command -v python)"
uv pip freeze --python /work/venv/bin/python > /work/environment/environment.txt
export PATH=/work/venv/bin:$PATH
rm -f /work/setup-inputs.json
sh -eu /work/stage-inputs.sh
python /work/remote.py verify-staging /work/setup-inputs.json

```

## Artifact: adata_annotated.h5ad

Full final annotated single-cell object (the notebook's working `adata` after every step), written under /work/outputs. Covers all scientific branches in one artifact: dataset composition (obs['sample'], barcode and gene identifiers); per-cell QC metrics (n_genes_by_counts, total_counts, pct_counts_{mt,ribo,hb} and log1p variants, n_cells_by_counts on var); cell/gene filtering outcome (final shape); Scrublet doublet scores and predicted-doublet calls per cell; raw counts (layers['counts']) and median-normalized log1PF data (X); highly-variable-gene flags/dispersions/means (n_top_genes=2000, batch_key='sample'); PCA coordinates, loadings and variance ratios; kNN graph (obsp/uns); UMAP coordinates; Leiden clusterings at default resolution plus 0.02/0.50/2.00; level-1 cell-type annotation (obs['cell_type_lvl1']); and the complete Wilcoxon rank_genes_groups results for all leiden_res_0.50 clusters (uns['rank_genes_groups']), which underlie the marker-gene dotplots and the DE branch.

Source evidence: Single adata object built across the whole script: sc.pp.calculate_qc_metrics(adata, qc_vars=['mt','ribo','hb'], log1p=True); sc.pp.filter_cells(adata, min_genes=100); sc.pp.filter_genes(adata, min_cells=3); sc.pp.scrublet(adata, batch_key='sample'); adata.layers['counts'] = adata.X.copy(); sc.pp.normalize_total/sc.pp.log1p; sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key='sample'); sc.tl.pca(adata); sc.pp.neighbors(adata); sc.tl.umap(adata); sc.tl.leiden(adata, flavor='igraph', n_iterations=2); the `for res in [0.02, 0.5, 2.0]` resolution loop; the cell_type_lvl1 mapping; sc.tl.rank_genes_groups(adata, groupby='leiden_res_0.50', method='wilcoxon').

## Artifact: rank_genes_groups_cluster7_head5.csv

The notebook's explicit differentially-expressed-gene table for cluster 7 of leiden_res_0.50: top-5 genes with names, scores, logfoldchanges and p-values (plus companion columns). Covers the notebook's observation that cluster 7 expresses NKG7/GNLY (NK cells) and provides exactly `dc_cluster_genes`, the gene list used to color the final UMAP panels.

Source evidence: Standalone cell `sc.get.rank_genes_groups_df(adata, group='7').head(5)` (assigned to `rank_genes_groups_7_head` in the reference script, call and arguments unchanged) together with `dc_cluster_genes = sc.get.rank_genes_groups_df(adata, group='7').head(5)['names']`; values originate from sc.tl.rank_genes_groups(adata, groupby='leiden_res_0.50', method='wilcoxon').

## Complete edited script

`````python
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

# Reference-script change: the original cell resolved the download registry from
# the figshare DOI at run time (network access). For the offline reference run
# the two .h5 files are staged by the setup step in /inputs, so the unchanged
# EXAMPLE_DATA.fetch() call below MD5-verifies each staged file locally and
# returns its path without any network retrieval.
EXAMPLE_DATA = pooch.create(
    path="/inputs",
    base_url="doi:10.6084/m9.figshare.22716739.v1/",
    registry={
        "s1d1_filtered_feature_bc_matrix.h5": "md5:a99285913ea3f3d22600d3d2f8a88e34",
        "s1d3_filtered_feature_bc_matrix.h5": "md5:825f7f7578e3dc0b8955f5a97a402338",
    },
)

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

# Based on the QC metric plots, one could now remove cells that have too many mitochondrial genes expressed or too many total counts by setting manual or automatic thresholds. However, sometimes what appears to be poor QC metrics can be driven by real biology so we suggest starting with a very permissive filtering strategy and revisiting it at a later point. We therefore now only filter cells with less than 100 genes expressed and genes that are detected in less than 3 cells. 
#
# Additionally, it is important to note that for datasets with multiple batches, quality control should be performed for each sample individually as quality control thresholds can vary substantially between batches. 

sc.pp.filter_cells(adata, min_genes=100)
sc.pp.filter_genes(adata, min_cells=3)

# ### Doublet detection
#
# As a next step, we run a doublet detection algorithm. Identifying doublets is crucial as they can lead to misclassifications or distortions in downstream analysis steps. Scanpy contains the doublet detection method Scrublet {cite}`Wolock2019`. Scrublet predicts cell doublets using a nearest-neighbor classifier of observed transcriptomes and simulated doublets. {func}`scanpy.pp.scrublet` adds `doublet_score` and `predicted_doublet` to `.obs`. One can now either filter directly on `predicted_doublet` or use the `doublet_score` later during clustering to filter clusters with high doublet scores. 

sc.pp.scrublet(adata, batch_key="sample")

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

# ## Feature selection
#
# As a next step, we want to reduce the dimensionality of the dataset and only include the most informative genes. This step is commonly known as feature selection. The scanpy function `pp.highly_variable_genes` annotates highly variable genes by reproducing the implementations of Seurat {cite}`Satija2015`, Cell Ranger {cite}`Zheng2017`, and Seurat v3 {cite}`Stuart2019` depending on the chosen `flavor`. 

sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")

sc.pl.highly_variable_genes(adata)

# ## Dimensionality Reduction
# Reduce the dimensionality of the data by running principal component analysis (PCA), which reveals the main axes of variation and denoises the data.

sc.tl.pca(adata)

# Let us inspect the contribution of single PCs to the total variance in the data. This gives us information about how many PCs we should consider in order to compute the neighborhood relations of cells, e.g. used in the clustering function {func}`~scanpy.tl.leiden` or {func}`~scanpy.tl.tsne`. In our experience, there does not seem to be signifigant downside to overestimating the numer of principal components.

sc.pl.pca_variance_ratio(adata, n_pcs=50, log=True)

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

# This graph can then be embedded in two dimensions for visualiztion with UMAP {cite:p}`McInnes2018`:

sc.tl.umap(adata)

# We can now visualize the UMAP according to the `sample`. 

sc.pl.umap(
    adata,
    color="sample",
    # Setting a smaller point size to get prevent overlap
    size=2,
)

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

# We have now reached a point where we have obtained a set of cells with decent quality, and we can proceed to their annotation to known cell types. Typically, this is done using genes that are exclusively expressed by a given cell type, or in other words these genes are the marker genes of the cell types, and are thus used to distinguish the heterogeneous groups of cells in our data. Previous efforts have collected and curated various marker genes into available resources, such as [CellMarker](http://bio-bigdata.hrbmu.edu.cn/CellMarker/), [TF-Marker](http://bio.liclab.net/TF-Marker/), and [PanglaoDB](https://panglaodb.se/). The [cellxgene gene expression tool](https://cellxgene.cziscience.com/gene-expression) can also be quite useful to see what cell types a gene has been expressed in across many existing datasets.

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

# There are fairly clear patterns of expression for our markers show here, which we can use to label our coarsest clustering with broad lineages.

adata.obs["cell_type_lvl1"] = adata.obs["leiden_res_0.02"].map({
    "0": "Lymphocytes",
    "1": "Monocytes",
    "2": "B Cells",
    "3": "Erythroid",
    "4": "Erythroid",
})

sc.pl.dotplot(adata, marker_genes, groupby="leiden_res_0.50", standard_scale="var")

# This seems like a resolution that suitable to distinguish most of the different cell types in our data. As such, let's try to annotate those by manually using the dotplot above, together with the UMAP of our clusters. Ideally, one would also look specifically into each cluster, and attempt to subcluster those if required.

# ### Differentially-expressed Genes as Markers

# Furthermore, one can also calculate marker genes per cluster and then look up whether we can link those marker genes to any known biology, such as cell types and/or states. This is typically done using simple statistical tests, such as Wilcoxon and t-test, for each cluster vs the rest.

# Obtain cluster-specific differentially expressed genes
sc.tl.rank_genes_groups(adata, groupby="leiden_res_0.50", method="wilcoxon")

# We can then visualize the top 5 differentially-expressed genes on a dotplot.

sc.pl.rank_genes_groups_dotplot(
    adata, groupby="leiden_res_0.50", standard_scale="var", n_genes=5
)

# We can then use these genes to figure out what cell types we're looking at. For example, Cluster 7 is expressing [*NKG7*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=NKG7&keywords=nkg7) and [*GNLY*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=GNLY&keywords=gnly), suggesting these are [NK cells](https://en.wikipedia.org/wiki/Natural_killer_cell).

# To create your own plots, or use a more automated approach, the differentially expressed genes can be extracted in a convenient format with {func}`scanpy.get.rank_genes_groups_df`

rank_genes_groups_7_head = sc.get.rank_genes_groups_df(adata, group="7").head(5)

dc_cluster_genes = sc.get.rank_genes_groups_df(adata, group="7").head(5)["names"]
sc.pl.umap(
    adata,
    color=[*dc_cluster_genes, "leiden_res_0.50"],
    legend_loc="on data",
    frameon=False,
    ncols=3,
)

# You may have noticed that the p-values found here are extremely low. This is due to the statistical test being performed considering each cell as an independent sample. For a more conservative approach you may want to consider "pseudo-bulking" your data by sample (*e.g.* `sc.get.aggregate(adata, by=["sample", "cell_type"], func="sum", layer="counts")`) and using a more powerful differential expression tool, like {doc}`pydeseq2 <pydeseq2:index>`.

# --- Reference-only export of scientific endpoints ---------------------------
# Added for the offline reference run; it does not add, change or remove any
# computed result. `adata_annotated.h5ad` stores the full final analysis object
# (QC metrics and filtering outcome, Scrublet doublet scores/calls, the counts
# layer, log1PF-normalized data, HVG annotations, PCA coordinates/loadings/
# variance ratios, neighborhood graph, UMAP coordinates, Leiden clusterings at
# every run resolution, level-1 cell-type labels and the complete Wilcoxon
# rank_genes_groups results). `rank_genes_groups_cluster7_head5.csv` stores the
# notebook's own top-5 DE-gene table for cluster 7, whose "names" column is
# exactly `dc_cluster_genes`.

from pathlib import Path

OUTPUT_DIR = Path("/work/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

adata.write_h5ad(OUTPUT_DIR / "adata_annotated.h5ad", compression="lzf")

rank_genes_groups_7_head.to_csv(
    OUTPUT_DIR / "rank_genes_groups_cluster7_head5.csv", index=False
)

`````

## Controller-computed diff

```diff
--- baseline.py
+++ reference.py
@@ -32,11 +32,19 @@
 # We are reading in the count matrix into an {class}`~anndata.AnnData` object, which holds many slots for annotations and different representations of the data.
 # See {doc}`anndata:tutorials/notebooks/getting-started` for a tutorial. 
 
+# Reference-script change: the original cell resolved the download registry from
+# the figshare DOI at run time (network access). For the offline reference run
+# the two .h5 files are staged by the setup step in /inputs, so the unchanged
+# EXAMPLE_DATA.fetch() call below MD5-verifies each staged file locally and
+# returns its path without any network retrieval.
 EXAMPLE_DATA = pooch.create(
-    path=pooch.os_cache("scverse_tutorials"),
+    path="/inputs",
     base_url="doi:10.6084/m9.figshare.22716739.v1/",
-)
-EXAMPLE_DATA.load_registry_from_doi()
+    registry={
+        "s1d1_filtered_feature_bc_matrix.h5": "md5:a99285913ea3f3d22600d3d2f8a88e34",
+        "s1d3_filtered_feature_bc_matrix.h5": "md5:825f7f7578e3dc0b8955f5a97a402338",
+    },
+)
 
 samples = {
     "s1d1": "s1d1_filtered_feature_bc_matrix.h5",
@@ -214,7 +222,7 @@
 
 # Cell type annotation is laborous and repetitive task, one which typically requires multiple rounds of subclustering and re-annotation. It's difficult to show the entirety of the process in this tutorial, but we aim to show how the tools scanpy provides assist in this process.
 
-# We have now reached a point where we have obtained a set of cells with decent quality, and we can proceed to their annotation to known cell types. Typically, this is done using genes that are exclusively expressed by a given cell type, or in other words these genes are the marker genes of the cell types, and are thus used to distinguish the heterogeneous groups of cells in our data. Previous efforts have collected and curated various marker genes into available resources, such as [CellMarker](http://bio-bigdata.hrbmu.edu.cn/CellMarker/), [TF-Marker](http://bio.liclab.net/TF-Marker/), and [PanglaoDB](https://panglaodb.se/). The [cellxgene gene expression tool](https://cellxgene.cziscience.com/gene-expression) can also be quite useful to see which cell types a gene has been expressed in across many existing datasets.
+# We have now reached a point where we have obtained a set of cells with decent quality, and we can proceed to their annotation to known cell types. Typically, this is done using genes that are exclusively expressed by a given cell type, or in other words these genes are the marker genes of the cell types, and are thus used to distinguish the heterogeneous groups of cells in our data. Previous efforts have collected and curated various marker genes into available resources, such as [CellMarker](http://bio-bigdata.hrbmu.edu.cn/CellMarker/), [TF-Marker](http://bio.liclab.net/TF-Marker/), and [PanglaoDB](https://panglaodb.se/). The [cellxgene gene expression tool](https://cellxgene.cziscience.com/gene-expression) can also be quite useful to see what cell types a gene has been expressed in across many existing datasets.
 
 # Commonly and classically, cell type annotation uses those marker genes subsequent to the grouping of the cells into clusters. So, let's generate a set of clustering solutions which we can then use to annotate our cell types. Here, we will use the Leiden clustering algorithm which will extract cell communities from our nearest neighbours graph.
 
@@ -305,11 +313,11 @@
     adata, groupby="leiden_res_0.50", standard_scale="var", n_genes=5
 )
 
-# We can then use these genes to figure out what cell types we're looking at. For example, Cluster 7 is expressing [*NKG7*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=NKG7&keywords=nkg7) and [*GNLY*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=GNLY&keywords=GNLY), suggesting these are [NK cells](https://en.wikipedia.org/wiki/Natural_killer_cell).
+# We can then use these genes to figure out what cell types we're looking at. For example, Cluster 7 is expressing [*NKG7*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=NKG7&keywords=nkg7) and [*GNLY*](https://www.genecards.org/cgi-bin/carddisp.pl?gene=GNLY&keywords=gnly), suggesting these are [NK cells](https://en.wikipedia.org/wiki/Natural_killer_cell).
 
 # To create your own plots, or use a more automated approach, the differentially expressed genes can be extracted in a convenient format with {func}`scanpy.get.rank_genes_groups_df`
 
-sc.get.rank_genes_groups_df(adata, group="7").head(5)
+rank_genes_groups_7_head = sc.get.rank_genes_groups_df(adata, group="7").head(5)
 
 dc_cluster_genes = sc.get.rank_genes_groups_df(adata, group="7").head(5)["names"]
 sc.pl.umap(
@@ -321,3 +329,25 @@
 )
 
 # You may have noticed that the p-values found here are extremely low. This is due to the statistical test being performed considering each cell as an independent sample. For a more conservative approach you may want to consider "pseudo-bulking" your data by sample (*e.g.* `sc.get.aggregate(adata, by=["sample", "cell_type"], func="sum", layer="counts")`) and using a more powerful differential expression tool, like {doc}`pydeseq2 <pydeseq2:index>`.
+
+# --- Reference-only export of scientific endpoints ---------------------------
+# Added for the offline reference run; it does not add, change or remove any
+# computed result. `adata_annotated.h5ad` stores the full final analysis object
+# (QC metrics and filtering outcome, Scrublet doublet scores/calls, the counts
+# layer, log1PF-normalized data, HVG annotations, PCA coordinates/loadings/
+# variance ratios, neighborhood graph, UMAP coordinates, Leiden clusterings at
+# every run resolution, level-1 cell-type labels and the complete Wilcoxon
+# rank_genes_groups results). `rank_genes_groups_cluster7_head5.csv` stores the
+# notebook's own top-5 DE-gene table for cluster 7, whose "names" column is
+# exactly `dc_cluster_genes`.
+
+from pathlib import Path
+
+OUTPUT_DIR = Path("/work/outputs")
+OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
+
+adata.write_h5ad(OUTPUT_DIR / "adata_annotated.h5ad", compression="lzf")
+
+rank_genes_groups_7_head.to_csv(
+    OUTPUT_DIR / "rank_genes_groups_cluster7_head5.csv", index=False
+)

```

## Excluded outputs

- Rendered figures from every plotting call (QC violin and scatter, HVG plot, PCA variance-ratio and PCA panels, UMAP panels for sample/leiden/doublet/QC metrics/cluster resolutions/marker genes, marker dotplots at res 0.02/0.50, rank_genes_groups dotplot): per the output requirement only their underlying scientific values and identifiers are exported, via adata_annotated.h5ad (obs QC and color-key columns, X_umap, X_pca, var HVG fields, uns PCA variance ratios, normalized expression plus the marker gene lists preserved in the script) and rank_genes_groups_cluster7_head5.csv; the source's plotting calls themselves remain unchanged.

- print(adata.obs['sample'].value_counts()) — the per-sample cell counts stay printed to the log as in the source and are recomputable from obs['sample'] in the exported h5ad; no separate artifact was added.

- dc_cluster_genes (pandas Series of cluster-7 marker gene names): not written separately; its values, in identical order, are exactly the 'names' column of rank_genes_groups_cluster7_head5.csv.

- Rank-genes-groups results beyond cluster 7's top 5 (all other groups and all tested genes) remain available in adata.uns['rank_genes_groups'] inside the exported h5ad; the source itself only displays group 7's top-5 rows, so no additional per-group tables are exported.

## Unresolved assumptions

- Input staging: the two figshare URLs (files 40347877, 40347880) must deliver the exact .h5 files during setup, matching the provider-supplied MD5s and byte sizes (provenance notes these checksums were never verified against a download; the stage script aborts on any mismatch). The SHA-256 values in /work/setup-inputs.json are computed at setup time from the downloaded content — no upstream SHA-256 is published.

- Dependency resolution on the base image's CPython 3.13.13 (scanpy>=1.10 with umap-learn's numba/llvmlite, igraph and h5py wheels) must succeed at uv lock/uv sync; the source notebook declares no versions and was never executed, so the exact scanpy revision behavior is unconfirmed. A resolution failure is an environment issue, not a source defect.

- Offline loading relies on pooch's documented behavior that fetch() returns a locally present file whose hash matches the registry without contacting the network; a checksum mismatch would surface as an explicit error rather than a network attempt.

- Cluster-label structure: this unexecuted notebook assumes leiden_res_0.50 contains cluster '7' (NKG7/GNLY-high) and leiden_res_0.02 yields exactly clusters '0'–'4'. If the locked dependency versions produce a different clustering, sc.get.rank_genes_groups_df(adata, group='7') raises and/or obs['cell_type_lvl1'] contains NaN; only the reference run can establish the actual labels.

- Resource fit is unmeasured (no execution timings exist in the inputs): whether the complete pipeline plus exports — two-batch Scrublet, PCA, neighbors/UMAP, four igraph leiden runs, Wilcoxon DE over all genes, figure rendering under Agg, and the lzf-compressed h5ad write — fits the 600 s / 8 GiB limits on 4 CPUs must be established by execution; exceeding them would be a resource limit, not a source defect.

- Determinism: all randomized steps use scanpy defaults (random_state=0 for PCA/Scrublet/UMAP/Leiden); results are reproducible only for the locked dependency versions, and no stored notebook outputs exist for comparison.
