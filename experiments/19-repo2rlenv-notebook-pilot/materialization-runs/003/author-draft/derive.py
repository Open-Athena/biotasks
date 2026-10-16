#!/usr/bin/env python3
"""Derive the supplied inputs for the marker-gene (DE) task.

Inputs created under <destination>/inputs/:
  * the two original 10x h5 count matrices, copied byte-for-byte;
  * cell_groups.csv  -- fixed per-cell cluster labels (from the recorded
    reference run; identity/grouping information only);
  * gene_identities.csv -- which stored features the analysis includes and the
    gene identifier for each (from the h5 files' own metadata).

<destination>/reference/ receives a projection of the recorded reference answer
fields for the controller's numerical-comparison stage.

No scientific computation and no answer values are produced here: the h5 files
are copied, and the two metadata tables are assembled by *selecting* existing
fields from the recorded reference export and from the h5 files' own metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import h5py
import pandas as pd

PROVIDER_MD5 = {
    "s1d1_filtered_feature_bc_matrix.h5": "a99285913ea3f3d22600d3d2f8a88e34",
    "s1d3_filtered_feature_bc_matrix.h5": "825f7f7578e3dc0b8955f5a97a402338",
}
SAMPLES = ("s1d1", "s1d3")


def md5(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_original(manifest: dict) -> dict[str, Path]:
    """Return the manifest's local paths keyed by file name, verifying identity."""
    paths: dict[str, Path] = {}
    for item in manifest["files"]:
        name = Path(item["local_path"]).name
        if name in PROVIDER_MD5:
            path = Path(item["local_path"])
            if not path.is_file() or md5(path) != PROVIDER_MD5[name]:
                raise SystemExit(f"{name} is not the expected original input file")
            paths[name] = path
    missing = set(PROVIDER_MD5) - set(paths)
    if missing:
        raise SystemExit(f"original inputs missing from manifest: {sorted(missing)}")
    return paths


def read_h5_metadata(path: Path):
    with h5py.File(path, "r") as f:
        m = f["matrix"]
        barcodes = [b.decode() for b in m["barcodes"][:]]
        names = [b.decode() for b in m["features/name"][:]]
        ids = [b.decode() for b in m["features/id"][:]]
        ftype = [b.decode() for b in m["features/feature_type"][:]]
    return barcodes, names, ids, ftype


def recorded_unique_names(names, ftype):
    """The recorded analysis's gene identifiers for the included features.

    The source analysis read each sample with sc.read_10x_h5 (Gene Expression
    features only) and called var_names_make_unique(): a feature whose symbol
    already occurred keeps the symbol, each later duplicate gets '-1', '-2', ...
    appended. Selecting (h5_row, gene_id) from that convention is purely
    mechanical and involves no scientific computation.
    """
    out = []
    seen: Counter[str] = Counter()
    for i, t in enumerate(ftype):
        if t != "Gene Expression":
            continue
        symbol = names[i]
        n = seen[symbol]
        seen[symbol] += 1
        out.append((i, symbol if n == 0 else f"{symbol}-{n}", symbol))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-inputs", required=True, help="JSON manifest of original inputs")
    ap.add_argument("--reference-dir", required=True, help="original terminal artifacts")
    ap.add_argument("--destination", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.source_inputs).read_text())
    src = verify_original(manifest)
    ref_dir = Path(args.reference_dir)
    dest = Path(args.destination)

    inputs = dest / "inputs"
    reference_out = dest / "reference"
    inputs.mkdir(parents=True, exist_ok=True)
    reference_out.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- 1. h5 copies
    sample_files = {s: f"{s}_filtered_feature_bc_matrix.h5" for s in SAMPLES}
    for sample, filename in sample_files.items():
        shutil.copyfile(src[filename], inputs / filename)

    # ------------------------------------------------------------ 2. gene identities
    frames = []
    for sample in SAMPLES:
        filename = sample_files[sample]
        barcodes, names, ids, ftype = read_h5_metadata(src[filename])
        for h5_row, gene_id, symbol in recorded_unique_names(names, ftype):
            frames.append(
                {
                    "sample": sample,
                    "h5_row": h5_row,
                    "gene_id": gene_id,
                    "gene_symbol": symbol,
                    "ensembl_id": ids[h5_row],
                }
            )
    gene_identities = pd.DataFrame(frames)
    if gene_identities.duplicated(["sample", "gene_id"]).any():
        raise SystemExit("gene_id is not unique within a sample")
    gene_identities["h5_row"] = gene_identities["h5_row"].astype(int)
    gene_identities.to_csv(inputs / "gene_identities.csv", index=False)

    # ---------------------------------------------------------------- 3. cell groups
    cell_obs = pd.read_csv(
        ref_dir / "cell_clusters_umap.csv",
        dtype=str,
        usecols=["cell_id", "sample", "leiden_res_0.50"],
    )
    if set(cell_obs["sample"]) != set(SAMPLES):
        raise SystemExit("unexpected samples in reference cell table")
    if cell_obs.duplicated(["sample", "cell_id"]).any():
        raise SystemExit("reference cell table has duplicate (sample, cell_id)")

    groups = cell_obs.rename(columns={"cell_id": "recorded_id", "leiden_res_0.50": "cluster"})
    id_universe = set(gene_identities["gene_id"])  # placeholder, unused
    rows = []
    for sample in SAMPLES:
        filename = sample_files[sample]
        barcodes, names, ids, ftype = read_h5_metadata(src[filename])
        idx = pd.Index(barcodes)
        part = groups[groups["sample"] == sample]
        recorded = part["recorded_id"].to_numpy()
        pos = idx.get_indexer(recorded)
        missing = pos < 0
        # The recorded pooled identifiers are unique via the '-1' disambiguation
        # that the source applied to the 20 s1d3 barcodes that coincide with an
        # s1d1 barcode; strip that extra suffix to recover the stored barcode.
        if missing.any():
            stripped = [r[:-2] if r.endswith("-1-1") else r for r in recorded[missing]]
            if [s for s in stripped] != [r[:-2] for r in recorded[missing]]:
                raise SystemExit("unexpected recorded identifier format")
            pos[missing] = idx.get_indexer(stripped)
        if (pos < 0).any():
            raise SystemExit(f"{sample}: recorded cells absent from stored barcodes")
        rows.append(
            pd.DataFrame(
                {
                    "sample": sample,
                    "barcode": [barcodes[p] for p in pos],
                    "cluster": part["cluster"].to_numpy(),
                }
            )
        )
    cell_groups = pd.concat(rows, ignore_index=True)
    if cell_groups.duplicated(["sample", "barcode"]).any():
        raise SystemExit("cell_groups rows are not unique")
    # keep the recorded export's row order (s1d1 block, then s1d3 block)
    cell_groups.to_csv(inputs / "cell_groups.csv", index=False)

    # --------------------------------------------------- 4. reference projection
    de = pd.read_csv(
        ref_dir / "rank_genes_groups_leiden_res_0.50.csv",
        dtype={"group": str, "names": str},
    )
    projection = de.rename(
        columns={
            "group": "cluster",
            "names": "gene",
            "scores": "score",
            "pvals": "pval",
            "pvals_adj": "pval_adj",
            "logfoldchanges": "log2fc",
        }
    )[["cluster", "gene", "score", "pval", "pval_adj", "log2fc"]]
    projection.to_csv(reference_out / "cluster_marker_genes.csv", index=False)
    shutil.copyfile(
        ref_dir / "rank_genes_groups_params.json",
        reference_out / "rank_genes_groups_params.json",
    )

    # ---------------------------------------------------------------- checks
    summary = {
        "cells": int(len(cell_groups)),
        "cluster_labels": sorted(cell_groups["cluster"].unique(), key=int),
        "gene_rows_per_sample": {
            s: int((gene_identities["sample"] == s).sum()) for s in SAMPLES
        },
        "reference_rows": int(len(projection)),
        "reference_clusters": int(de["group"].nunique()),
        "reference_unique_genes": int(de["names"].nunique()),
        "cross_product_satisfied": int(len(projection))
        == int(de["group"].nunique()) * int(de["names"].nunique()),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
