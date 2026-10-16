#!/usr/bin/env python3
"""Reference solution: marker genes for a fixed clustering of pooled marrow data.

Reads only <input-dir>/inputs and writes <output-dir>/cluster_marker_genes.csv.

The statistics follow the scanpy `rank_genes_groups(method="wilcoxon")`
convention precisely, but are computed directly so that every step of the public
definition is explicit:
  * pooled matrix over the intersection gene universe;
  * permissive cell filter (>= 100 detected genes) and gene filter (>= 3 cells);
  * one pooled median-of-totals size factor, log1p (float32, as scanpy stores it);
  * per-cluster two-sided Wilcoxon rank-sum z with average ranks, no tie
    correction, no continuity correction;
  * two-sided normal tail via the stable complementary CDF (erfc);
  * Benjamini-Hochberg across all tested genes within each cluster;
  * log2 fold change from back-transformed means with the 1e-9 stabilizer.
"""
from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.special import erfc

CHUNK_CELLS_PER_GENE = 10_000_000  # scanpy's chunking constant

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)


def read_sample_matrix(path: Path):
    """Return (CSR cells x genes, barcodes, feature_type) from a 10x h5 file."""
    with h5py.File(path, "r") as f:
        m = f["matrix"]
        n_feat, n_cell = (int(v) for v in m["shape"][:])
        data = m["data"][:]
        indices = m["indices"][:]
        indptr = m["indptr"][:]
        barcodes = [b.decode() for b in m["barcodes"][:]]
        ftype = [b.decode() for b in m["features/feature_type"][:]]
        feature_rows = np.arange(n_feat)
    matrix = sp.csc_matrix((data, indices, indptr), shape=(n_feat, n_cell))
    return matrix, barcodes, ftype, feature_rows


def rankdata_average(chunk: np.ndarray) -> np.ndarray:
    """Average ranks per column (ties get the mean of the ranks they span)."""
    n = chunk.shape[0]
    out = np.empty_like(chunk, dtype=np.float64)
    order = np.argsort(chunk, axis=0, kind="stable")
    ranks = np.arange(1, n + 1, dtype=np.float64)
    for j in range(chunk.shape[1]):
        col = chunk[:, j]
        srt = col[order[:, j]]
        obs = np.empty(n, dtype=bool)
        obs[0] = True
        obs[1:] = srt[1:] != srt[:-1]
        # rank positions 1..n assigned in sorted order; ties share the mean
        sorted_ranks = np.empty(n)
        i = 0
        while i < n:
            k = i
            while k + 1 < n and not obs[k + 1]:
                k += 1
            mean_rank = 0.5 * (ranks[i] + ranks[k])
            sorted_ranks[i : k + 1] = mean_rank
            i = k + 1
        col_ranks = np.empty(n)
        col_ranks[order[:, j]] = sorted_ranks
        out[:, j] = col_ranks
    return out


def rankdata_average(chunk: np.ndarray) -> np.ndarray:
    """Average ranks per column (ties get the mean of the ranks they span)."""
    n, m = chunk.shape
    out = np.empty((n, m), dtype=np.float64)
    order = np.argsort(chunk, axis=0, kind="stable")
    srt = np.take_along_axis(chunk, order, axis=0)
    starts = np.zeros((n, m), dtype=bool)
    starts[0, :] = True
    starts[1:, :] = srt[1:, :] != srt[:-1, :]
    for j in range(m):
        idx = np.flatnonzero(starts[:, j])          # first row of each tie run
        boundaries = np.concatenate([idx, [n]])
        first = boundaries[:-1] + 1                 # 1-based rank of run start
        last = boundaries[1:]                       # 1-based rank of run end
        mean_rank = 0.5 * (first + last)
        run_of_row = np.cumsum(starts[:, j]) - 1    # run index per sorted row
        col_ranks = np.empty(n, dtype=np.float64)
        col_ranks[order[:, j]] = mean_rank[run_of_row]
        out[:, j] = col_ranks
    return out


def csr_group_means(X, group_of_row, n_groups):
    """Per-group column means, accumulating the stored values in float64.

    Nonzeros are accumulated in CSR order (row by row), which is exactly the
    accumulation order the reference analysis's grouped mean used, so the
    floating-point results match that convention bit for bit.
    """
    cols = X.indices
    data = X.data.astype(np.float64)
    groups = np.repeat(group_of_row, np.diff(X.indptr))
    sums = np.zeros((n_groups, X.shape[1]), dtype=np.float64)
    np.add.at(sums, (groups, cols), data)
    counts = np.bincount(group_of_row, minlength=n_groups).astype(np.float64)
    return sums / counts[:, None]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    input_dir = Path(args.input_dir) / "inputs"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    groups = pd.read_csv(input_dir / "cell_groups.csv", dtype=str)
    genes_meta = pd.read_csv(input_dir / "gene_identities.csv", dtype={"sample": str})
    genes_meta["h5_row"] = genes_meta["h5_row"].astype(int)

    samples = sorted(set(groups["sample"]))
    sample_paths = {s: input_dir / f"{s}_filtered_feature_bc_matrix.h5" for s in samples}
    for s, p in sample_paths.items():
        if not p.is_file():
            raise SystemExit(f"missing input file {p}")

    # ---------------------------------------------------------------- gene universe
    by_sample = {s: genes_meta[genes_meta["sample"] == s] for s in samples}
    universe = sorted(
        set.intersection(*[set(t["gene_id"]) for t in by_sample.values()])
    )
    log(f"gene universe (intersection over samples): {len(universe)}")

    # ---------------------------------------------------------------- pooled matrix
    labels = []
    n_cells = len(groups)
    pooled_blocks = []
    row_slots = []
    for s in samples:
        table = by_sample[s].set_index("gene_id")
        h5_rows = table.loc[universe, "h5_row"].to_numpy()
        matrix, barcodes, ftype, _ = read_sample_matrix(sample_paths[s])
        idx_map = pd.Index(barcodes)
        part_rows = np.flatnonzero(groups["sample"].to_numpy() == s)
        part = groups.iloc[part_rows]
        pos = idx_map.get_indexer(part["barcode"].to_numpy())
        if (pos < 0).any():
            raise SystemExit(f"{s}: barcodes in cell_groups.csv missing from the h5 file")
        # this sample's cells (rows) x the shared gene universe (columns)
        pooled_blocks.append(matrix[h5_rows, :][:, pos].T.tocsr())
        row_slots.append(part_rows)
        labels.append(part["cluster"].to_numpy())
        del matrix
    # assemble in the row order of cell_groups.csv
    ordered = np.empty(n_cells, dtype=int)
    offset = 0
    for slots in row_slots:
        ordered[slots] = offset + np.arange(len(slots))
        offset += len(slots)
    stacked = sp.vstack(pooled_blocks, format="csr")
    pooled = stacked[ordered, :].tocsr()
    cluster = np.concatenate(labels)
    del pooled_blocks, stacked
    log(f"pooled matrix {pooled.shape}")

    # ---------------------------------------------------------------- cell filter
    detected = np.diff(pooled.indptr)
    keep_cells = detected >= 100
    if not keep_cells.all():
        raise SystemExit(
            "cell filter does not reproduce the analysis population: "
            f"{int((~keep_cells).sum())} cells would be dropped"
        )

    # ---------------------------------------------------------------- gene filter
    cols = pooled.tocsc()
    cells_per_gene = np.diff(cols.indptr)
    keep_genes = cells_per_gene >= 3
    pooled = cols[:, keep_genes].tocsr()
    tested_genes = [g for g, k in zip(universe, keep_genes) if k]
    log(f"tested genes {len(tested_genes)}")

    # ---------------------------------------------------------------- normalization
    # Sizes factors follow the reference convention: the per-cell total is
    # accumulated in the stored float32 dtype (not in exact integer arithmetic),
    # the median of those totals is the target, each value is divided by the
    # per-cell count-depth ratio in float32, and log1p is applied in float32.
    n_rows = pooled.shape[0]
    counts_per_cell = np.empty(n_rows, dtype=np.float32)
    _indptr = pooled.indptr
    _data = pooled.data.astype(np.float32)
    for i in range(n_rows):
        acc = np.float32(0.0)
        for k in range(_indptr[i], _indptr[i + 1]):
            acc = np.float32(acc + _data[k])
        counts_per_cell[i] = acc
    nonzero_counts = counts_per_cell[counts_per_cell > 0]
    if nonzero_counts.size != counts_per_cell.size:
        raise SystemExit("a cell with zero counts over the tested genes is present")
    target = np.float32(np.median(nonzero_counts))
    log(f"median of per-cell totals: {float(target)}")
    size_factor = counts_per_cell / target
    scaled = pooled.data.astype(np.float32) / size_factor[
        np.repeat(np.arange(n_rows), np.diff(pooled.indptr))
    ]
    normed = sp.csr_matrix(
        (np.log1p(scaled).astype(np.float32), pooled.indices, pooled.indptr),
        shape=pooled.shape,
        dtype=np.float32,
    )
    log(f"normalized matrix nnz {normed.nnz}")
    normed_csr = normed.tocsr()                # row-major copy for the mean accumulations
    cluster_labels = sorted(set(cluster), key=lambda x: int(x))
    label_index = {lab: i for i, lab in enumerate(cluster_labels)}
    group_of_row = np.array([label_index[c] for c in cluster], dtype=np.int64)
    all_group_means = csr_group_means(normed_csr, group_of_row, len(cluster_labels))
    group_sizes = np.array([int((cluster == lab).sum()) for lab in cluster_labels], dtype=np.float64)

    # ---------------------------------------------------------------- marker test
    N = normed_csr.shape[0]
    results = []
    for lab in cluster_labels:
        mask = cluster == lab
        n = int(mask.sum())
        n_rest = N - n
        if n == 0 or n_rest == 0:
            raise SystemExit(f"cluster {lab} is empty or covers the whole population")
        W = np.zeros(normed_csr.shape[1], dtype=np.float64)
        step = max(CHUNK_CELLS_PER_GENE // N, 1)
        normed_csc = normed_csr.tocsc()
        for left in range(0, normed_csc.shape[1], step):
            right = min(left + step, normed_csc.shape[1])
            chunk = np.asarray(normed_csc[:, left:right].todense(), dtype=np.float64)
            ranks = rankdata_average(chunk)
            W[left:right] = ranks[mask, :].sum(axis=0)
        std = np.sqrt(n * n_rest * (N + 1) / 12.0)
        z = (W - n * (N + 1) / 2.0) / std
        z = np.where(np.isnan(z), 0.0, z)
        # two-sided normal tail, stable evaluation
        pval = erfc(np.abs(z) / np.sqrt(2.0))
        # means of normalized values
        # Group means accumulate the float32 stored values in float64, in CSR
        # row order (the same accumulation the reference analysis's grouped
        # mean uses), then each group's "rest" mean is the weighted difference
        # of the other groups from the population total.
        gi = label_index[lab]
        mu = all_group_means[gi]
        total = (group_sizes[:, None] * all_group_means).sum(axis=0)
        mu_rest = (total - mu * n) / n_rest
        log2fc = np.log2(
            (np.expm1(mu.astype(np.float64)) + 1e-9)
            / (np.expm1(mu_rest.astype(np.float64)) + 1e-9)
        )
        # Benjamini-Hochberg within the cluster over all tested genes: scale the
        # sorted p-values by m / k (k = 1..m), enforce monotonicity from the
        # largest p-value upward, and cap at 1.
        m = len(pval)
        order = np.argsort(pval, kind="stable")
        ranked = pval[order]
        ecdffactor = np.arange(1, m + 1) / float(m)
        padj_sorted = np.minimum.accumulate((ranked / ecdffactor)[::-1])[::-1]
        padj_sorted[padj_sorted > 1] = 1.0
        padj = np.empty(m, dtype=np.float64)
        padj[order] = padj_sorted
        results.append(
            pd.DataFrame(
                {
                    "cluster": lab,
                    "gene": tested_genes,
                    "score": z,
                    "pval": pval,
                    "pval_adj": padj,
                    "log2fc": log2fc,
                }
            )
        )
        log(f"cluster {lab}: n={n} done")

    table = pd.concat(results, ignore_index=True)
    table["cluster"] = table["cluster"].astype(str)

    # -------------------------------------------- rank by descending score per cluster
    out_frames = []
    for lab in cluster_labels:
        part = table[table["cluster"] == lab].copy()
        order = np.argsort(-part["score"].to_numpy(), kind="stable")
        part = part.iloc[order]
        part["rank"] = np.arange(1, len(part) + 1)
        out_frames.append(part)
    out = pd.concat(out_frames, ignore_index=True)
    out = out[["cluster", "rank", "gene", "score", "pval", "pval_adj", "log2fc"]]
    out.to_csv(output_dir / "cluster_marker_genes.csv", index=False)
    log(f"wrote {len(out)} rows")


if __name__ == "__main__":
    main()
