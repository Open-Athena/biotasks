#!/usr/bin/env python3
"""Solve the public task: assign CTCF motifs to ChIP-seq peaks with blacklist filtering.

Adaptation of the source analysis onto the supplied inputs, using the
reference packages (bioframe 0.8.0, pandas, numpy):
  - narrowPeak peaks, JASPAR motif track parsed with skiprows=1,
    bed3 blacklist (same parsing conventions as the source);
  - bioframe.overlap with return_index=True (left join, keep_order);
  - per-input-peak-record motif counts by grouping on index_1;
  - strongest motif per peak-coordinate via fillna(-1) + groupby.idxmax();
  - base-level subtraction of blacklist expanded by 1000 bp on both sides.
"""
import argparse
import os

import pandas as pd
import bioframe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    ctcf_peaks = bioframe.read_table(
        os.path.join(args.input_dir, "ENCFF401MQL.bed.gz"), schema="narrowPeak"
    )
    ctcf_motifs = bioframe.read_table(
        os.path.join(args.input_dir, "MA0139.1.tsv.gz"), schema="jaspar", skiprows=1
    )
    blacklist = bioframe.read_table(
        os.path.join(args.input_dir, "ENCFF356LFX.bed.gz"), schema="bed3"
    )

    # Peak-motif overlaps (same chromosome, half-open, positive length).
    df_peaks_motifs = bioframe.overlap(
        ctcf_peaks, ctcf_motifs, suffixes=("_1", "_2"), return_index=True
    )

    # Motifs per input peak record, in input record order: index_1 is the
    # 0-based input peak record identifier, and non-overlapping peaks are
    # retained as rows with null motif fields that count as 0.
    motifs_per_peak = df_peaks_motifs.groupby("index_1")["index_2"].count().values

    # Strongest motif per peak-coordinate group.
    # idxmax returns the first maximum in overlap-result order, i.e. the pair
    # scanned in ascending peak record order then motif record order.
    df_peaks_motifs["pval_2"] = df_peaks_motifs["pval_2"].fillna(-1)
    idxmax_peaks_motifs = (
        df_peaks_motifs.groupby(["chrom_1", "start_1", "end_1"])["pval_2"].idxmax().values
    )
    df_peaks_maxmotif = df_peaks_motifs.loc[idxmax_peaks_motifs]

    df_peaks_maxmotif = df_peaks_maxmotif[
        [
            "chrom_1",
            "start_1",
            "end_1",
            "fc_1",
            "chrom_2",
            "start_2",
            "end_2",
            "pval_2",
            "strand_2",
        ]
    ]
    for i in df_peaks_maxmotif.keys():
        if "_1" in i:
            df_peaks_maxmotif.rename(columns={i: i.split("_")[0]}, inplace=True)

    # Base-level subtraction of the blacklist expanded by 1 kb on both sides.
    df_peaks_maxmotif_clean = bioframe.subtract(
        df_peaks_maxmotif, bioframe.expand(blacklist, 1000)
    )

    os.makedirs(args.output_dir, exist_ok=True)
    df_peaks_maxmotif_clean.to_csv(
        os.path.join(
            args.output_dir, "peaks_with_strongest_motif_blacklist_filtered.csv"
        ),
        index=False,
    )
    pd.DataFrame({"motifs_per_peak": motifs_per_peak}).to_csv(
        os.path.join(args.output_dir, "motifs_per_peak.csv"), index=False
    )


if __name__ == "__main__":
    main()

