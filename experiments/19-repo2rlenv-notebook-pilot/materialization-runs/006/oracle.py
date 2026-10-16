#!/usr/bin/env python3
"""Marker genes for a fixed clustering of pooled bone-marrow single-cell data.

Implements the public task definition directly from the four declared inputs
(each declared path is relative directly to --input-dir):

1. build the pooled count matrix over the intersection gene universe, with
   rows aligned to ``cell_groups.csv``;
2. verify the defined analysis population: every supplied cell must detect at
   least 100 genes with a strictly positive count (fail loudly otherwise);
3. keep genes detected in at least 3 cells (the tested gene universe,
   identical for every cluster);
4. normalize with one pooled median-of-totals factor and natural log1p;
5. for every supplied cluster (in-group vs. all other analysis cells): a
   two-sided Wilcoxon rank-sum z-score with average ranks, no tie-variance
   correction and no continuity correction; the two-sided standard-normal
   tail via the complementary error function; Benjamini-Hochberg adjustment
   across all tested genes within the cluster; log2 fold change from
   back-transformed means with the 1e-9 stabilizers;
6. write ``cluster_marker_genes.csv`` directly under --output-dir: one row
   per (cluster, gene), ranked by descending score within each cluster, rows
   ordered by ascending numeric cluster label then rank.

Deterministic (no randomized component; sequential sparse reductions),
offline, reading only the declared inputs.  Ranks are computed once per gene
over the pooled cell axis and reduced per cluster with a sparse indicator
product; counts are handled as integers (exactly) and the normalized values
in float64, following the literal definitions.

Storage note: the 10x filtered-matrix layout stores ``matrix/shape`` as
[n_features, n_cells] with the compressed-sparse axis being the *cell*
(barcode) axis (``indptr`` spans cells, ``indices`` hold feature rows).  All
dimensions are inferred from the file and layout deviations are reported as
warnings with defensive reconciliation rather than fatal errors.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.special import erfc
from scipy.stats import rankdata

SQRT2 = float(np.sqrt(2.0))
MIN_DETECTED_GENES = 100
MIN_CELLS_PER_GENE = 3
RANK_CHUNK_ENTRIES = 8_000_000  # n_cells x chunk_genes is bounded by this
NORMALIZATION_BLOCK = 5_000_000  # entries per normalization block

START = time.time()


def log(message: str) -> None:
    print(f"[{time.time() - START:7.1f}s] {message}", flush=True)


def warn(message: str) -> None:
    print(f"WARNING: {message}", flush=True)


def decode_list(items) -> list[str]:
    return [item.decode() if isinstance(item, bytes) else str(item) for item in items]


def resolve_input(input_dir: Path, declared: str) -> Path:
    """Locate a declared input under ``--input-dir``.

    Paths are declared relative directly to the input directory (no extra
    directory level); the remaining candidates tolerate a staging layout that
    keeps the same file names one level deeper.
    """
    name = Path(declared).name
    for candidate in (input_dir / declared, input_dir / name, input_dir / "inputs" / name):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"declared input {declared!r} not found under {input_dir}")


def read_10x_matrix(path: Path):
    """Return (features x cells raw-count csc matrix, stored barcodes).

    The compressed-sparse axis is identified from the storage itself: the
    barcode list defines the cell axis, and ``indptr`` must span either the
    cell axis (standard 10x layout) or the feature axis (accepted fallback).
    Every remaining layout expectation is reported as a warning and
    reconciled instead of aborting the analysis.
    """
    with h5py.File(path, "r") as handle:
        group = handle["matrix"]
        data = np.asarray(group["data"][:]).ravel()
        indices = np.asarray(group["indices"][:]).ravel()
        indptr = np.asarray(group["indptr"][:]).ravel()
        barcodes = decode_list(group["barcodes"][:])
        shape = None
        if "shape" in group:
            arr = np.asarray(group["shape"][:]).ravel()
            if arr.size == 2:
                shape = (int(arr[0]), int(arr[1]))
        elif "shape" in group.attrs:
            try:
                arr = np.asarray(group.attrs["shape"]).ravel()
                if arr.size == 2:
                    shape = (int(arr[0]), int(arr[1]))
            except (TypeError, ValueError):
                shape = None

    if indptr.size == 0:
        raise SystemExit(f"{path}: indptr dataset is empty")
    if not np.issubdtype(data.dtype, np.integer):
        warn(f"{path}: stored counts are not integers; rounding to integers")
        data = np.rint(data.astype(np.float64)).astype(np.int64)
    if data.size and int(data.min()) < 0:
        warn(f"{path}: negative stored values present; strictly-positive filters ignore them")

    # Reconcile the entry arrays with the final pointer position defensively
    # (these hold exactly for well-formed 10x files).
    nnz = int(indptr[-1])
    n_idx, n_dat = int(indices.size), int(data.size)
    if n_idx != n_dat or n_idx != nnz or n_dat != nnz:
        warn(
            f"{path}: stored entry arrays ({n_idx} indices, {n_dat} values) disagree with "
            f"indptr[-1]={nnz}; reconciling"
        )
        keep = min(n_idx, n_dat)
        indices = np.array(indices[:keep], copy=True)
        data = np.array(data[:keep], copy=True)
        if keep < nnz:
            pad = nnz - keep
            indices = np.concatenate([indices, np.zeros(pad, dtype=indices.dtype)])
            data = np.concatenate([data, np.zeros(pad, dtype=data.dtype)])
        else:
            indices = indices[:nnz]
            data = data[:nnz]

    n_ptr = int(indptr.size) - 1  # the dimension the pointer spans
    n_cell = len(barcodes)
    if shape is not None:
        a, b = shape
        if b == n_cell:
            n_feat, n_cell_dim = a, b
        elif a == n_cell:
            warn(f"{path}: stored shape labels the barcode axis first; exchanging dimensions")
            n_feat, n_cell_dim = b, a
        else:
            warn(
                f"{path}: stored shape {shape} is inconsistent with the barcode count; "
                "inferring dimensions from the storage"
            )
            if n_ptr == n_cell:
                n_feat = (int(indices.max()) + 1) if indices.size else 0
            else:
                n_feat = n_ptr
            n_cell_dim = n_cell
    else:
        warn(f"{path}: no stored shape dataset; inferring dimensions from the storage")
        if n_ptr == n_cell:
            n_feat = (int(indices.max()) + 1) if indices.size else 0
        else:
            n_feat = n_ptr
        n_cell_dim = n_cell

    if n_ptr == n_cell_dim:
        # standard 10x layout: features x cells, compressed over cells
        matrix = sp.csc_matrix((data, indices, indptr), shape=(n_feat, n_cell_dim))
    elif n_ptr == n_feat:
        warn(f"{path}: indptr spans the feature axis; interpreting storage as feature-major")
        matrix = sp.csr_matrix((data, indices, indptr), shape=(n_feat, n_cell_dim)).tocsc()
    else:
        raise SystemExit(
            f"{path}: indptr spans {n_ptr} entries, matching neither stored dimension "
            f"({n_feat}, {n_cell_dim})"
        )
    if matrix.shape[1] != len(barcodes):
        warn(f"{path}: cell axis holds {matrix.shape[1]} columns for {len(barcodes)} barcodes")
    return matrix, barcodes


def prune_non_positive(block: sp.csr_matrix) -> sp.csr_matrix:
    """Drop stored entries that are not strictly positive, so a stored zero
    can never count as a detected gene or as expression."""
    if block.nnz == 0:
        return block
    positive = block.data > 0
    if bool(positive.all()):
        return block
    row_of_entry = np.repeat(np.arange(block.shape[0]), np.diff(block.indptr))
    kept_per_row = np.bincount(row_of_entry[positive], minlength=block.shape[0])
    indptr = np.concatenate(([0], np.cumsum(kept_per_row))).astype(np.int64)
    return sp.csr_matrix(
        (block.data[positive], block.indices[positive], indptr), shape=block.shape
    )


def build_sample_block(path: Path, h5_rows: np.ndarray, wanted_barcodes) -> sp.csr_matrix:
    """The sample's analysis cells (rows) x the shared gene universe (columns)."""
    matrix, barcodes = read_10x_matrix(path)
    n_feat = matrix.shape[0]
    if h5_rows.size == 0 or int(h5_rows.min()) < 0 or int(h5_rows.max()) >= n_feat:
        raise SystemExit(f"{path}: gene map references feature rows outside the stored matrix")
    index = pd.Index(barcodes)
    if index.has_duplicates:
        raise SystemExit(f"{path}: stored barcodes are not unique")
    positions = index.get_indexer(pd.Index(list(wanted_barcodes)))
    if (positions < 0).any():
        raise SystemExit(
            f"{path}: {int((positions < 0).sum())} barcodes of cell_groups.csv "
            "are not stored in this sample"
        )
    if h5_rows.size == n_feat and np.array_equal(h5_rows, np.arange(n_feat)):
        selected = matrix  # identity feature selection
    else:
        selected = matrix[h5_rows, :]
    block = selected[:, positions].T.tocsr()  # (cells x shared genes), raw counts
    return prune_non_positive(block)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    # ------------------------------------------------------------------ inputs
    cell_groups_path = resolve_input(input_dir, "cell_groups.csv")
    gene_map_path = resolve_input(input_dir, "gene_identities.csv")

    groups = pd.read_csv(cell_groups_path, dtype=str, keep_default_na=False)
    if list(groups.columns) != ["sample", "barcode", "cluster"]:
        raise SystemExit(f"unexpected cell_groups.csv columns: {list(groups.columns)}")
    for column in ("sample", "barcode", "cluster"):
        if (groups[column].str.len() == 0).any():
            raise SystemExit(f"blank values in cell_groups.csv column {column!r}")
    if groups.duplicated(["sample", "barcode"]).any():
        raise SystemExit("(sample, barcode) is not unique in cell_groups.csv")
    N = len(groups)
    if N < 2:
        raise SystemExit("the analysis population has fewer than two cells")

    gene_map = pd.read_csv(gene_map_path, dtype=str, keep_default_na=False)
    if list(gene_map.columns) != [
        "sample",
        "h5_row",
        "gene_id",
        "gene_symbol",
        "ensembl_id",
    ]:
        raise SystemExit(f"unexpected gene_identities.csv columns: {list(gene_map.columns)}")
    try:
        gene_map["h5_row"] = gene_map["h5_row"].astype("int64")
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"non-integer h5_row values in gene_identities.csv: {exc}")
    if gene_map.duplicated(["sample", "gene_id"]).any():
        raise SystemExit("gene_id is not unique within a sample in gene_identities.csv")
    if gene_map.duplicated(["sample", "h5_row"]).any():
        raise SystemExit("h5_row is not unique within a sample in gene_identities.csv")
    if (gene_map["gene_id"].str.len() == 0).any():
        raise SystemExit("blank gene identifiers in gene_identities.csv")

    samples = sorted(set(groups["sample"]))
    if not samples:
        raise SystemExit("no cells supplied")
    unknown_samples = [s for s in samples if s not in set(gene_map["sample"])]
    if unknown_samples:
        raise SystemExit(f"gene_identities.csv has no map for samples {unknown_samples}")
    identity_sets = [set(gene_map.loc[gene_map["sample"] == s, "gene_id"]) for s in samples]
    universe = sorted(set.intersection(*identity_sets))
    if not universe:
        raise SystemExit("the samples share no analysis genes")
    G0 = len(universe)
    log(f"population: {N} cells from {samples}; intersection gene universe {G0}")

    sample_paths = {
        s: resolve_input(input_dir, f"{s}_filtered_feature_bc_matrix.h5") for s in samples
    }

    # ------------------------------------------------- pooled matrix assembly
    sample_labels = groups["sample"].to_numpy()
    barcode_column = groups["barcode"].to_numpy()
    blocks = []
    row_slots = []
    for sample in samples:
        table = gene_map[gene_map["sample"] == sample].set_index("gene_id")
        h5_rows = table.loc[universe, "h5_row"].to_numpy().astype(np.int64)
        selected = np.flatnonzero(sample_labels == sample)
        blocks.append(build_sample_block(sample_paths[sample], h5_rows, barcode_column[selected]))
        row_slots.append(selected)
    if sum(len(sel) for sel in row_slots) != N:
        raise SystemExit("sample selections do not cover the analysis population")
    log("sample blocks built")

    # Assemble, in the row order of cell_groups.csv, one pooled CSR matrix of
    # raw integer counts (cells x the shared gene universe).
    row_nnz = np.zeros(N, dtype=np.int64)
    for block, selected in zip(blocks, row_slots):
        row_nnz[selected] = np.diff(block.indptr)
    indptr = np.zeros(N + 1, dtype=np.int64)
    np.cumsum(row_nnz, out=indptr[1:])
    data = np.empty(int(indptr[-1]), dtype=np.int64)
    indices = np.empty(int(indptr[-1]), dtype=np.int32)
    for block, selected in zip(blocks, row_slots):
        for k, global_row in enumerate(selected):
            source_lo = int(block.indptr[k])
            source_hi = int(block.indptr[k + 1])
            target_lo = int(indptr[int(global_row)])
            target_hi = int(indptr[int(global_row) + 1])
            if target_hi - target_lo != source_hi - source_lo:
                raise SystemExit("internal error assembling the pooled matrix")
            data[target_lo:target_hi] = block.data[source_lo:source_hi]
            indices[target_lo:target_hi] = block.indices[source_lo:source_hi]
    del blocks
    log(f"pooled matrix assembled over the universe ({len(data)} stored entries)")

    # ----------------------------------------------------------- cell filter
    below = int((row_nnz < MIN_DETECTED_GENES).sum())
    if below:
        raise SystemExit(
            f"the defined cell filter (>= {MIN_DETECTED_GENES} detected genes over the "
            f"pooled intersection universe) would drop {below} of the supplied cells: "
            "the supplied population is not reproducible, so the deliverable is invalid"
        )

    # ----------------------------------------------------------- gene filter
    column_counts = np.bincount(indices, minlength=G0)
    keep_genes = column_counts >= MIN_CELLS_PER_GENE
    tested_genes = [gene for gene, keep in zip(universe, keep_genes) if keep]
    G1 = len(tested_genes)
    if G1 == 0:
        raise SystemExit("no genes survive the min-cells filter")
    log(f"tested gene universe (>= {MIN_CELLS_PER_GENE} cells): {G1}")

    new_column = (np.cumsum(keep_genes) - 1).astype(np.int32)
    entry_keep = keep_genes[indices]
    kept_indices = new_column[indices[entry_keep]]
    kept_data = data[entry_keep]
    row_of_entry = np.repeat(np.arange(N, dtype=np.int32), row_nnz.astype(np.int32))
    kept_row_of_entry = row_of_entry[entry_keep]
    kept_per_row = np.bincount(kept_row_of_entry, minlength=N)
    kept_indptr = np.zeros(N + 1, dtype=np.int64)
    np.cumsum(kept_per_row, out=kept_indptr[1:])
    if int(kept_indptr[-1]) != len(kept_data):
        raise SystemExit("internal error building the gene-filtered matrix")
    del entry_keep, row_of_entry, indices, indptr, row_nnz

    # ----------------------------------------------------- totals and median
    totals = np.zeros(N, dtype=np.int64)
    nonzero_rows = kept_per_row > 0
    starts = kept_indptr[:-1][nonzero_rows]
    if starts.size:
        totals[nonzero_rows] = np.add.reduceat(kept_data, starts)
    if int((totals <= 0).sum()):
        raise SystemExit("a supplied cell has zero counts over the tested gene universe")
    target = float(np.median(totals.astype(np.float64)))
    log(f"pooled median count depth over tested genes: {target}")

    # ------------------------------------------------------- normalization
    # x_ij = ln(1 + count_ij * T / total_i); count * T is exact in float64, so
    # this is the literal definition evaluated to ~1 ulp.
    normalized = np.empty(len(kept_data), dtype=np.float64)
    for block_start in range(0, len(kept_data), NORMALIZATION_BLOCK):
        block_stop = min(block_start + NORMALIZATION_BLOCK, len(kept_data))
        values = kept_data[block_start:block_stop].astype(np.float64)
        values *= target
        values /= totals[kept_row_of_entry[block_start:block_stop]]
        np.log1p(values, out=values)
        normalized[block_start:block_stop] = values
    del kept_data, kept_row_of_entry, kept_per_row, nonzero_rows, starts
    log("normalized values computed")

    norm = sp.csr_matrix((normalized, kept_indices, kept_indptr), shape=(N, G1))
    del normalized, kept_indices, kept_indptr
    norm_csc = norm.tocsc()
    del norm

    # ---------------------------------------------------- cluster bookkeeping
    try:
        cluster_labels = sorted(set(groups["cluster"]), key=int)
    except ValueError as exc:
        raise SystemExit(f"cluster labels are not integer-like strings: {exc}")
    label_index = {label: i for i, label in enumerate(cluster_labels)}
    group_of_row = np.array(
        [label_index[label] for label in groups["cluster"].to_numpy()], dtype=np.int64
    )
    n_clusters = len(cluster_labels)
    sizes = np.bincount(group_of_row, minlength=n_clusters)
    if int(sizes.sum()) != N or int((sizes <= 0).sum()):
        raise SystemExit("cluster labels do not partition the analysis population")
    log("cluster sizes: " + ", ".join(f"{lab}:{int(n)}" for lab, n in zip(cluster_labels, sizes)))

    # indicator matrix: entry (cluster, cell) = 1 iff the cell is in-cluster
    onehot = sp.csr_matrix(
        (np.ones(N, dtype=np.float64), (group_of_row, np.arange(N, dtype=np.int64))),
        shape=(n_clusters, N),
    )

    # -------------------------- per-cluster sums of the normalized values
    # (numerators of the group means; arithmetic means are the point of
    # departure for the fold-change definition)
    product = onehot.dot(norm_csc)
    if sp.issparse(product):
        sums = product.toarray().astype(np.float64, copy=False)
    else:
        sums = np.asarray(product, dtype=np.float64)
    del product
    if sums.shape != (n_clusters, G1):
        raise SystemExit("internal error reducing the per-cluster sums")

    # -------------------------------- ranks and W statistics, gene chunked
    # For every gene: average ranks over all N cells (ties share the mean of
    # the ranks they span), then W_c = sum of the in-group ranks, by a sparse
    # indicator reduction.  The chunks bound resident dense memory.
    chunk_genes = max(1, RANK_CHUNK_ENTRIES // max(N, 1))
    W = np.empty((n_clusters, G1), dtype=np.float64)
    for left in range(0, G1, chunk_genes):
        right = min(left + chunk_genes, G1)
        dense = norm_csc[:, left:right].toarray()  # cells x chunk genes
        ranks = rankdata(dense, axis=0, method="average")
        W[:, left:right] = np.asarray(onehot.dot(ranks), dtype=np.float64)
        del dense, ranks
    del norm_csc, onehot
    log("rank statistics computed for all clusters")

    # -------------------------------------------------- per-cluster markers
    total_sums = sums.sum(axis=0)
    frames = []
    for ci, label in enumerate(cluster_labels):
        n = int(sizes[ci])
        n_rest = N - n
        if n <= 0 or n_rest <= 0:
            raise SystemExit(f"cluster {label!r} is empty or covers the whole population")
        variance = n * n_rest * (N + 1) / 12.0
        if variance <= 0:
            z = np.zeros(G1, dtype=np.float64)
        else:
            z = (W[ci] - n * (N + 1) / 2.0) / np.sqrt(variance)

        pval = erfc(np.abs(z) / SQRT2)

        # Benjamini-Hochberg across all tested genes within this cluster.
        order = np.argsort(pval, kind="stable")
        ranked = pval[order]
        ecdffactor = np.arange(1, G1 + 1, dtype=np.float64) / float(G1)
        adjusted_sorted = np.minimum.accumulate((ranked / ecdffactor)[::-1])[::-1]
        np.minimum(adjusted_sorted, 1.0, out=adjusted_sorted)
        padj = np.empty(G1, dtype=np.float64)
        padj[order] = adjusted_sorted

        mu_cluster = sums[ci] / float(n)
        mu_rest = (total_sums - sums[ci]) / float(n_rest)
        log2fc = np.log2((np.expm1(mu_cluster) + 1e-9) / (np.expm1(mu_rest) + 1e-9))

        for name, values in (
            ("score", z),
            ("pval", pval),
            ("pval_adj", padj),
            ("log2fc", log2fc),
        ):
            if not np.isfinite(values).all():
                raise SystemExit(f"non-finite {name} values for cluster {label!r}")

        ranked_order = np.argsort(-z, kind="stable")  # descending score, deterministic ties
        frames.append(
            pd.DataFrame(
                {
                    "cluster": label,
                    "rank": np.arange(1, G1 + 1, dtype=np.int64),
                    "gene": [tested_genes[i] for i in ranked_order],
                    "score": z[ranked_order],
                    "pval": pval[ranked_order],
                    "pval_adj": padj[ranked_order],
                    "log2fc": log2fc[ranked_order],
                }
            )
        )
        log(f"cluster {label} ({n} cells): done")

    del W, sums, total_sums
    result = pd.concat(frames, ignore_index=True)
    result = result[["cluster", "rank", "gene", "score", "pval", "pval_adj", "log2fc"]]
    if result.duplicated(["cluster", "gene"]).any():
        raise SystemExit("internal error: duplicated (cluster, gene) pairs")
    if len(result) != n_clusters * G1:
        raise SystemExit("internal error: incomplete cluster x gene cross product")

    # ------------------------------------------------------------------ output
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "cluster_marker_genes.csv"
    result.to_csv(out_path, index=False)
    log(f"wrote {len(result)} rows ({n_clusters} clusters x {G1} genes) to {out_path}")


if __name__ == "__main__":
    main()

