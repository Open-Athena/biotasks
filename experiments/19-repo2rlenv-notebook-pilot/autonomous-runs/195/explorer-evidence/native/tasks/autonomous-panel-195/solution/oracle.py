#!/usr/bin/env python3
"""Reference solution: process the GNPS natural-products library and compute
all-pairs greedy cosine / modified-cosine similarities plus the ranked
matches for spectrum index 97.

Uses only the supplied inputs directory; no reference answers are accessed.
"""
import argparse
import csv
import os

import numpy as np
from matchms.importing import load_from_mgf
from matchms.exporting import save_as_json
from matchms import calculate_scores
from matchms.similarity import CosineGreedy, ModifiedCosine
from matchms.filtering import (
    default_filters,
    repair_inchi_inchikey_smiles,
    derive_inchi_from_smiles,
    derive_smiles_from_inchi,
    derive_inchikey_from_inchi,
    harmonize_undefined_smiles,
    harmonize_undefined_inchi,
    harmonize_undefined_inchikey,
    add_precursor_mz,
    normalize_intensities,
    select_by_intensity,
    select_by_mz,
)

QUERY_INDEX = 97
MIN_MATCH = 5
TOP_N = 10


def metadata_processing(spectrum):
    spectrum = default_filters(spectrum)
    spectrum = repair_inchi_inchikey_smiles(spectrum)
    spectrum = derive_inchi_from_smiles(spectrum)
    spectrum = derive_smiles_from_inchi(spectrum)
    spectrum = derive_inchikey_from_inchi(spectrum)
    spectrum = harmonize_undefined_smiles(spectrum)
    spectrum = harmonize_undefined_inchi(spectrum)
    spectrum = harmonize_undefined_inchikey(spectrum)
    spectrum = add_precursor_mz(spectrum)
    return spectrum


def peak_processing(spectrum):
    spectrum = normalize_intensities(spectrum)
    spectrum = select_by_intensity(spectrum, intensity_from=0.01)
    spectrum = select_by_mz(spectrum, mz_from=10, mz_to=1000)
    return spectrum


def write_metadata_csv(spectrums, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["spectrum_index", "compound_name", "precursor_mz",
                    "inchikey", "smiles"])
        for i, s in enumerate(spectrums):
            w.writerow([
                i,
                s.get("compound_name"),
                s.get("precursor_mz"),
                s.get("inchikey"),
                s.get("smiles"),
            ])


def write_best_matches(spectrums, scores, path):
    sorted_matches = scores.scores_by_query(
        spectrums[QUERY_INDEX], name="ModifiedCosine_score", sort=True)
    best_matches = [x for x in sorted_matches
                    if x[1]["ModifiedCosine_matches"] >= MIN_MATCH][:TOP_N]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "smiles", "inchikey",
                    "ModifiedCosine_score", "ModifiedCosine_matches"])
        for rank, match in enumerate(best_matches):
            spec, score = match
            w.writerow([
                rank,
                spec.get("smiles"),
                spec.get("inchikey"),
                score["ModifiedCosine_score"],
                score["ModifiedCosine_matches"],
            ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    mgf = os.path.join(args.input_dir, "GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf")
    if not os.path.isfile(mgf):
        # fall back to any MGF in the input directory
        candidates = [n for n in os.listdir(args.input_dir)
                       if n.lower().endswith(".mgf")]
        if len(candidates) != 1:
            raise SystemExit("expected exactly one MGF input, found: %r" % candidates)
        mgf = os.path.join(args.input_dir, candidates[0])

    os.makedirs(args.output_dir, exist_ok=True)

    spectrums = list(load_from_mgf(mgf))
    spectrums = [metadata_processing(s) for s in spectrums]
    spectrums = [peak_processing(s) for s in spectrums]
    n = len(spectrums)
    if QUERY_INDEX >= n:
        raise SystemExit("query index %d out of range (N=%d)" % (QUERY_INDEX, n))

    # 1. Processed spectral library.
    save_as_json(spectrums,
                 os.path.join(args.output_dir, "processed_spectra.json"))

    # 2. All-pairs greedy cosine (no shift), tolerance 0.005.
    cosine = CosineGreedy(tolerance=0.005)
    cosine_scores = calculate_scores(spectrums, spectrums, cosine,
                                     is_symmetric=True)
    cosine_array = cosine_scores.scores.to_array()
    np.savez_compressed(
        os.path.join(args.output_dir, "cosine_greedy_scores.npz"),
        CosineGreedy_score=cosine_array["CosineGreedy_score"],
        CosineGreedy_matches=cosine_array["CosineGreedy_matches"],
    )

    # 3. All-pairs greedy modified cosine, tolerance 0.005.
    modified = ModifiedCosine(tolerance=0.005)
    modified_scores = calculate_scores(spectrums, spectrums, modified,
                                       is_symmetric=True)
    modified_array = modified_scores.scores.to_array()
    np.savez_compressed(
        os.path.join(args.output_dir, "modified_cosine_scores.npz"),
        ModifiedCosine_score=modified_array["ModifiedCosine_score"],
        ModifiedCosine_matches=modified_array["ModifiedCosine_matches"],
    )

    # 4. Per-spectrum metadata keyed by spectrum index.
    write_metadata_csv(
        spectrums, os.path.join(args.output_dir, "spectrum_metadata.csv"))

    # 5. Ranked modified-cosine matches for query spectrum index 97.
    write_best_matches(
        spectrums, modified_scores,
        os.path.join(args.output_dir, "best_matches_spectrum97.csv"))

    print("processed %d spectra; outputs written to %s" % (n, args.output_dir))


if __name__ == "__main__":
    main()

