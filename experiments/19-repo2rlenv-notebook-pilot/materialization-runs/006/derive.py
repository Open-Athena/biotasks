#!/usr/bin/env python3
"""Materialize the task inputs and the reference projection.

Stage layout (declared paths are relative to each stage directory, with no
extra directory level):
  <destination>/inputs/    the four declared input files (flat names);
  <destination>/reference/ one file per declared output path (flat name):
                            cluster_marker_genes.csv.

Inputs:
  * the two original 10x count matrices, copied byte-for-byte after verifying
    the provider md5 checksums;
  * gene_identities.csv -- the features of each sample that the recorded
    analysis included, identified by the naming convention of that run,
    selected from the h5 files' own metadata;
  * cell_groups.csv -- the fixed per-cell cluster assignment of the recorded
    reference clustering, with (sample, stored barcode, cluster label).

Reference: the recorded reference marker table projected into the public
output schema (fields renamed; a per-cluster rank added from the recorded
ranking order; rows ordered by ascending numeric cluster label then rank).
Recorded numeric values pass through as their original strings; no value is
recomputed, re-filtered or re-ranked.

No differential-expression result or other analysis-derived value is written
under <destination>/inputs/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

SAMPLES = ("s1d1", "s1d3")
PROVIDER_MD5 = {
    "s1d1_filtered_feature_bc_matrix.h5": "a99285913ea3f3d22600d3d2f8a88e34",
    "s1d3_filtered_feature_bc_matrix.h5": "825f7f7578e3dc0b8955f5a97a402338",
}
REFERENCE_CELL_TABLE = "cell_clusters_umap.csv"
REFERENCE_MARKER_TABLE = "rank_genes_groups_leiden_res_0.50.csv"
SUFFIX_RE = re.compile(r"^(.*)-(\d+)$")


def warn(message: str) -> None:
    print(f"WARNING: {message}", flush=True)


def md5_sum(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_local_paths(node) -> list[Path]:
    found: list[Path] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "local_path" and isinstance(value, str):
                found.append(Path(value))
            else:
                found.extend(collect_local_paths(value))
    elif isinstance(node, (list, tuple)):
        for value in node:
            found.extend(collect_local_paths(value))
    return found


def original_inputs(manifest_file: Path) -> dict[str, Path]:
    """Locate the two original matrices in the manifest and verify identity."""
    manifest = json.loads(manifest_file.read_text())
    by_name: dict[str, Path] = {}
    for path in collect_local_paths(manifest):
        if path.name in PROVIDER_MD5 and path.name not in by_name:
            by_name[path.name] = path
    missing = sorted(set(PROVIDER_MD5) - set(by_name))
    if missing:
        raise SystemExit(f"original inputs missing from the manifest: {missing}")
    for name, path in by_name.items():
        if not path.is_file():
            raise SystemExit(f"manifest path for {name} does not exist: {path}")
        digest = md5_sum(path)
        if digest != PROVIDER_MD5[name]:
            raise SystemExit(
                f"{name}: md5 {digest} does not match the provider checksum "
                f"{PROVIDER_MD5[name]}"
            )
    return by_name


def decode_list(items) -> list[str]:
    return [item.decode() if isinstance(item, bytes) else str(item) for item in items]


def read_h5_metadata(path: Path):
    """Stored barcodes and feature metadata of a 10x filtered matrix."""
    with h5py.File(path, "r") as handle:
        group = handle["matrix"]
        barcodes = decode_list(group["barcodes"][:])
        names = decode_list(group["features/name"][:])
        ids = decode_list(group["features/id"][:])
        ftype = decode_list(group["features/feature_type"][:])
    return barcodes, names, ids, ftype


def analysis_gene_rows(names, feature_types):
    """(h5_row, gene_id, gene_symbol) for the included Gene Expression features.

    The gene identifier follows the recorded analysis's naming convention on
    ``sc.read_10x_h5`` + ``var_names_make_unique``: only ``Gene Expression``
    features in stored order, a first occurrence keeping its symbol and each
    later duplicate gaining '-1', '-2', ... Duplicated symbols stay distinct
    features under distinct identifiers; none are merged or summed.  This is
    mechanical selection of recorded metadata, not a computation.
    """
    rows = []
    seen: Counter = Counter()
    for row, symbol in enumerate(names):
        if feature_types[row] != "Gene Expression":
            continue
        occurrence = seen[symbol]
        seen[symbol] += 1
        gene_id = symbol if occurrence == 0 else f"{symbol}-{occurrence}"
        rows.append((row, gene_id, symbol))
    return rows


def suffix_variants(text: str):
    """A recorded pooled cell identifier, then progressively dropping any
    disambiguation suffix.  A stored 10x barcode ends in '-1'; the source's
    pooled-unique renaming appended a further '-<n>' exactly where a barcode
    string occurs in both samples, so a colliding identifier ends '-1-1'."""
    yield text
    base = text
    for _ in range(3):
        match = SUFFIX_RE.match(base)
        if match is None:
            return
        base = match.group(1)
        yield base


def resolve_barcodes(recorded_ids, stored_barcodes) -> list[str]:
    index = pd.Index(stored_barcodes)
    if index.has_duplicates:
        raise SystemExit("stored barcodes are not unique within a sample")
    out: list[str] = []
    unresolved: list[str] = []
    for value in recorded_ids:
        text = str(value)
        found = None
        for candidate in suffix_variants(text):
            if candidate in index:
                found = candidate
                break
        if found is None:
            unresolved.append(text)
        else:
            out.append(found)
    if unresolved:
        raise SystemExit(
            f"{len(unresolved)} recorded cells are absent from the stored barcodes, "
            f"e.g. {unresolved[:5]}"
        )
    return out


def recorded_cell_table(ref_dir: Path) -> pd.DataFrame:
    table = pd.read_csv(ref_dir / REFERENCE_CELL_TABLE, dtype=str)
    needed = ["cell_id", "sample", "leiden_res_0.50"]
    for column in needed:
        if column not in table.columns:
            raise SystemExit(f"recorded cell table lacks column {column!r}")
    table = table[needed]
    if table.isna().any().any():
        raise SystemExit("missing values in the recorded per-cell table")
    if set(table["sample"]) != set(SAMPLES):
        raise SystemExit("unexpected samples in the recorded per-cell table")
    if table.duplicated(["sample", "cell_id"]).any():
        raise SystemExit("duplicate (sample, cell_id) in the recorded per-cell table")
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-inputs", required=True)
    ap.add_argument("--reference-dir", required=True)
    ap.add_argument("--destination", required=True)
    args = ap.parse_args()

    src = original_inputs(Path(args.source_inputs))
    ref_dir = Path(args.reference_dir)
    dest = Path(args.destination)
    inputs_dir = dest / "inputs"
    reference_dir = dest / "reference"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ 1. raw matrices
    file_of = {s: f"{s}_filtered_feature_bc_matrix.h5" for s in SAMPLES}
    for sample in SAMPLES:
        shutil.copyfile(src[file_of[sample]], inputs_dir / file_of[sample])

    meta = {}
    for sample in SAMPLES:
        barcodes, names, ids, ftype = read_h5_metadata(src[file_of[sample]])
        meta[sample] = (barcodes, analysis_gene_rows(names, ftype), ids)

    # ------------------------------------------------------- 2. gene identities
    records = []
    for sample in SAMPLES:
        _, gene_rows, ensembl_ids = meta[sample]
        for h5_row, gene_id, symbol in gene_rows:
            records.append(
                {
                    "sample": sample,
                    "h5_row": h5_row,
                    "gene_id": gene_id,
                    "gene_symbol": symbol,
                    "ensembl_id": ensembl_ids[h5_row],
                }
            )
    gene_identities = pd.DataFrame(
        records, columns=["sample", "h5_row", "gene_id", "gene_symbol", "ensembl_id"]
    )
    if gene_identities.empty:
        raise SystemExit("no Gene Expression features found in the inputs")
    if gene_identities.duplicated(["sample", "gene_id"]).any():
        raise SystemExit("identifier-naming convention produced duplicate gene_id values")
    if gene_identities.duplicated(["sample", "h5_row"]).any():
        raise SystemExit("h5_row is not unique within a sample")
    gene_identities["h5_row"] = gene_identities["h5_row"].astype(int)
    gene_identities.to_csv(inputs_dir / "gene_identities.csv", index=False)

    # ---------------------------------------------------------- 3. cell groups
    cells = recorded_cell_table(ref_dir)
    frames = []
    for sample in SAMPLES:
        barcodes, _, _ = meta[sample]
        part = cells[cells["sample"] == sample]
        frames.append(
            pd.DataFrame(
                {
                    "sample": sample,
                    "barcode": resolve_barcodes(part["cell_id"].to_numpy(), barcodes),
                    "cluster": part["leiden_res_0.50"].to_numpy(),
                }
            )
        )
    cell_groups = pd.concat(frames, ignore_index=True)
    if cell_groups.duplicated(["sample", "barcode"]).any():
        raise SystemExit("(sample, barcode) is not unique in the derived cell groups")
    # row order keeps the recorded export's (the s1d1 block, then the s1d3 block)
    cell_groups.to_csv(inputs_dir / "cell_groups.csv", index=False)

    # ------------------------------------------------- 4. reference projection
    de = pd.read_csv(ref_dir / REFERENCE_MARKER_TABLE, dtype=str, keep_default_na=False)
    needed = ["group", "names", "scores", "pvals_adj", "pvals", "logfoldchanges"]
    for column in needed:
        if column not in de.columns:
            raise SystemExit(f"reference marker table lacks column {column!r}")
    de = de[needed]
    if any(
        (de[column].str.len() == 0).any()
        for column in ("scores", "pvals", "pvals_adj", "logfoldchanges")
    ):
        warn("reference marker table contains blank numeric values")

    de = de.rename(
        columns={
            "group": "cluster",
            "names": "gene",
            "scores": "score",
            "pvals": "pval",
            "pvals_adj": "pval_adj",
            "logfoldchanges": "log2fc",
        }
    )
    cluster_arr = de["cluster"].to_numpy()
    gene_arr = de["gene"].to_numpy()
    n_rows = len(de)
    labels = list(dict.fromkeys(cluster_arr))  # order of first appearance

    # The recorded ranking order is the reference rank: the position of the
    # row within its cluster block (order of appearance, robust even to
    # non-contiguous cluster layouts).  No score is recomputed.
    de["rank"] = de.groupby("cluster", sort=False).cumcount() + 1

    # Order rows by ascending numeric cluster label, then rank.
    try:
        cluster_key = np.array([int(label) for label in cluster_arr], dtype=np.int64)
        label_order = sorted(labels, key=int)
    except ValueError:
        cluster_key = np.array([labels.index(label) for label in cluster_arr], dtype=np.int64)
        label_order = list(labels)
        warn("reference cluster labels are not integer-like; using appearance order")
    order = np.lexsort((de["rank"].to_numpy(), cluster_key))

    # Structural checks on the recorded result, reported as warnings only:
    # they describe invariants of the recorded export, and a failed check must
    # not prevent the declared file inventory from being produced.
    per_cluster_counts = de.groupby("cluster", sort=False).size()
    per_cluster_genes = de.groupby("cluster", sort=False)["gene"].nunique()
    if int(per_cluster_counts.sum()) != n_rows:
        warn("reference cluster tabulation lost rows")
    if int(per_cluster_genes.nunique()) != 1:
        warn(f"reference clusters cover different gene counts: {per_cluster_genes.to_dict()}")
    n_genes = int(per_cluster_genes.iloc[0])
    if n_rows != len(labels) * n_genes:
        warn("reference marker table is not a complete cluster x gene cross product")
    if de.duplicated(["cluster", "gene"]).any():
        warn("duplicate (cluster, gene) pairs in the reference marker table")
    gene_lists = [set(de.loc[de["cluster"] == label, "gene"]) for label in labels]
    if any(gene_list != gene_lists[0] for gene_list in gene_lists[1:]):
        warn("reference clusters test different gene sets")

    scores = pd.to_numeric(de["score"], errors="coerce").to_numpy(dtype=np.float64)
    if int(np.isnan(scores).sum()):
        warn("non-numeric score values in the reference marker table")
    ordered_scores = scores[order]
    ordered_clusters = cluster_arr[order]
    same_cluster = np.concatenate([[False], ordered_clusters[1:] == ordered_clusters[:-1]])
    if same_cluster.any():
        ascending = np.diff(ordered_scores) > 0
        if int((ascending & same_cluster[1:]).sum()):
            warn("the recorded ranking is not by descending score within some cluster")

    try:
        cell_labels = sorted(set(cell_groups["cluster"]), key=int)
    except ValueError:
        cell_labels = sorted(set(cell_groups["cluster"]))
        warn("cell-group cluster labels are not integer-like")
    if label_order != cell_labels:
        warn("reference cluster labels differ from the labels present in cell_groups.csv")

    identity_intersection = set.intersection(
        *[set(gene_identities.loc[gene_identities["sample"] == s, "gene_id"]) for s in SAMPLES]
    )
    outside = sorted(set(gene_arr) - identity_intersection)
    if outside:
        warn(
            f"{len(outside)} reference gene identifiers are outside the mapped identity "
            f"intersection, e.g. {outside[:8]}"
        )

    projection = de.iloc[order][
        ["cluster", "rank", "gene", "score", "pval", "pval_adj", "log2fc"]
    ]
    projection.to_csv(reference_dir / "cluster_marker_genes.csv", index=False)

    summary = {
        "cells": int(len(cell_groups)),
        "cluster_labels": cell_labels,
        "genes_mapped_per_sample": {
            s: int((gene_identities["sample"] == s).sum()) for s in SAMPLES
        },
        "pooled_identity_intersection": len(identity_intersection),
        "reference_rows": int(len(projection)),
        "reference_clusters": len(labels),
        "reference_genes_per_cluster": n_genes,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

