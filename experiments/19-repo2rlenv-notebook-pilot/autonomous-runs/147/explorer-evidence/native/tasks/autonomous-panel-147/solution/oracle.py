#!/usr/bin/env python3
"""Oracle for the GNPS natural-products-library similarity task.

Solves the public question using only <input-dir>/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf
and writes the four requested products into <output-dir>. The computation mirrors
the matchms 0.30.2 semantics pinned in the public question: the two filter
pipelines in the stated order with default arguments, all-against-all
CosineGreedy and ModifiedCosine at tolerance 0.005, and the ranked best-match
branches via scores_by_query(..., sort=True) with >= min_match applied before
truncation to 10.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

MGF_NAME = "GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf"
BRANCHES = [
    # (query_index, score_key, matches_key, min_match or None)
    (5, "CosineGreedy_score", "CosineGreedy_matches", None),   # branch A
    (5, "CosineGreedy_score", "CosineGreedy_matches", 5),      # branch B
    (5, "ModifiedCosine_score", "ModifiedCosine_matches", 5),  # branch C
    (11, "ModifiedCosine_score", "ModifiedCosine_matches", 5), # branch D
    (97, "ModifiedCosine_score", "ModifiedCosine_matches", 5), # branch E
]


def build_pipelines():
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

    def metadata_processing(spectrum):
        # Order and default arguments fixed by the public question.
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

    return metadata_processing, peak_processing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    from matchms.importing import load_from_mgf
    from matchms import calculate_scores
    from matchms.similarity import CosineGreedy, ModifiedCosine

    mgf = os.path.join(args.input_dir, MGF_NAME)
    out = args.output_dir
    os.makedirs(out, exist_ok=True)

    metadata_processing, peak_processing = build_pipelines()

    # Import and pipelines. Input order defines the spectrum index.
    spectrums = list(load_from_mgf(mgf))
    n_before = [len(s.peaks.mz) for s in spectrums]
    spectrums = [metadata_processing(s) for s in spectrums]
    spectrums = [peak_processing(s) for s in spectrums]
    n_after = [len(s.peaks.mz) for s in spectrums]

    # Output 1: processed_spectra.json
    records = []
    for i, s in enumerate(spectrums):
        records.append({
            "spectrum_index": i,
            "spectrum_id": s.get("spectrum_id") or "",
            "compound_name": s.get("compound_name") or "",
            "inchikey": s.get("inchikey") or "",
            "inchi": s.get("inchi") or "",
            "smiles": s.get("smiles") or "",
            "precursor_mz": float(s.get("precursor_mz")),
            "peaks": [[float(m), float(v)]
                      for m, v in zip(s.peaks.mz, s.peaks.intensities)],
        })
    with open(os.path.join(out, "processed_spectra.json"), "w", encoding="utf-8") as f:
        json.dump(records, f)

    # Output 2: similarity_scores.npz (both families, all pairs).
    similarity_measure = CosineGreedy(tolerance=0.005)
    scores_greedy = calculate_scores(spectrums, spectrums, similarity_measure,
                                     is_symmetric=True)
    arr_greedy = scores_greedy.scores.to_array()

    similarity_measure = ModifiedCosine(tolerance=0.005)
    scores_modified = calculate_scores(spectrums, spectrums, similarity_measure,
                                       is_symmetric=True)
    arr_modified = scores_modified.scores.to_array()

    np.savez(
        os.path.join(out, "similarity_scores.npz"),
        cosine_greedy_score=np.asarray(arr_greedy["CosineGreedy_score"], dtype=np.float64),
        cosine_greedy_matches=np.asarray(arr_greedy["CosineGreedy_matches"], dtype=np.int64),
        modified_cosine_score=np.asarray(arr_modified["ModifiedCosine_score"], dtype=np.float64),
        modified_cosine_matches=np.asarray(arr_modified["ModifiedCosine_matches"], dtype=np.int64),
    )

    # Output 3: best_matches.csv (branches A-E). Ranking semantics:
    # scores_by_query(..., sort=True), >= min_match applied before truncation
    # to the first 10 entries; the query's self-match is part of the ranking.
    index_of = {id(s): i for i, s in enumerate(spectrums)}
    rows = []
    for query_idx, score_key, matches_key, min_match in BRANCHES:
        measure = "CosineGreedy" if score_key.startswith("CosineGreedy") else "ModifiedCosine"
        scores_obj = scores_greedy if measure == "CosineGreedy" else scores_modified
        sorted_matches = scores_obj.scores_by_query(spectrums[query_idx],
                                                    name=score_key, sort=True)
        if min_match is not None:
            selected = [x for x in sorted_matches if x[1][matches_key] >= min_match]
        else:
            selected = sorted_matches
        for rank, entry in enumerate(selected[:10], start=1):
            ref, rec = entry[0], entry[1]
            rows.append([
                query_idx,
                measure,
                "none" if min_match is None else str(min_match),
                rank,
                index_of[id(ref)],
                ref.get("smiles") or "",
                ref.get("inchikey") or "",
                repr(float(rec[score_key])),
                int(rec[matches_key]),
            ])
    with open(os.path.join(out, "best_matches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["query_index", "similarity_measure", "min_match_filter", "rank",
                    "matched_spectrum_index", "matched_smiles", "matched_inchikey",
                    "score", "matches"])
        w.writerows(rows)

    # Output 4: peak_counts.csv
    with open(os.path.join(out, "peak_counts.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["spectrum_index", "n_peaks_before_filtering", "n_peaks_after_filtering"])
        for i, (a, b) in enumerate(zip(n_before, n_after)):
            w.writerow([i, a, b])

    print("done: %d spectra; outputs written to %s" % (len(spectrums), out))


if __name__ == "__main__":
    main()
