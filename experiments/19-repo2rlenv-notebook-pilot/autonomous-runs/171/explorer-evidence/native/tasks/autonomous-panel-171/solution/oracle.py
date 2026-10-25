#!/usr/bin/env python3
"""Solver for the GNPS-NIH natural-products spectral similarity task.

Uses only the supplied inputs directory (containing
GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf) and writes the six required CSVs into the
given output directory. Implements the tutorial's processing and scoring
invocations with unchanged parameters.
"""
import argparse
import csv
import os

MGF_NAME = "GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf"

MATCH_HEADER = ["rank", "matched_spectrum_index", "inchikey", "smiles",
                "cosine_score", "matched_peak_count"]
IDENT_HEADER = ["spectrum_index", "inchikey", "smiles"]


def run_pipeline(mgf_path):
    from matchms.importing import load_from_mgf
    from matchms.filtering import (
        default_filters, repair_inchi_inchikey_smiles, derive_inchi_from_smiles,
        derive_smiles_from_inchi, derive_inchikey_from_inchi,
        harmonize_undefined_smiles, harmonize_undefined_inchi,
        harmonize_undefined_inchikey, add_precursor_mz, normalize_intensities,
        select_by_intensity, select_by_mz,
    )

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

    spectrums = list(load_from_mgf(mgf_path))
    spectrums = [metadata_processing(s) for s in spectrums]
    spectrums = [peak_processing(s) for s in spectrums]
    return spectrums


def top_matches(spectrums, scores, query, score_name, match_name, min_match,
                top=10):
    index_of = {id(s): i for i, s in enumerate(spectrums)}
    sorted_matches = scores.scores_by_query(query, name=score_name, sort=True)
    if min_match is None:
        selected = sorted_matches[:top]
    else:
        selected = [x for x in sorted_matches if x[1][match_name] >= min_match][:top]
    rows = []
    for rank, (ref, values) in enumerate(selected):
        if ref is None:
            raise SystemExit("unexpected None reference in scores_by_query output")
        idx = index_of.get(id(ref))
        if idx is None:
            candidates = [i for i, s in enumerate(spectrums) if s == ref]
            if len(candidates) != 1:
                raise SystemExit("cannot uniquely resolve matched spectrum index")
            idx = candidates[0]
        rows.append([rank, idx, ref.get("inchikey") or "", ref.get("smiles") or "",
                     float(values[score_name]), int(values[match_name])])
    return rows


def compute_tables(spectrums):
    from matchms import calculate_scores
    from matchms.similarity import CosineGreedy, ModifiedCosine

    tables = {}
    similarity_measure = CosineGreedy(tolerance=0.005)
    scores = calculate_scores(spectrums, spectrums, similarity_measure,
                             is_symmetric=True)
    tables["cosine_spectrum_5_top10"] = top_matches(
        spectrums, scores, spectrums[5],
        "CosineGreedy_score", "CosineGreedy_matches", None)
    tables["cosine_spectrum_5_min5"] = top_matches(
        spectrums, scores, spectrums[5],
        "CosineGreedy_score", "CosineGreedy_matches", 5)
    del scores, similarity_measure

    similarity_measure = ModifiedCosine(tolerance=0.005)
    scores = calculate_scores(spectrums, spectrums, similarity_measure,
                             is_symmetric=True)
    for query_index in (5, 11, 97):
        tables["modified_cosine_spectrum_%d_min5" % query_index] = top_matches(
            spectrums, scores, spectrums[query_index],
            "ModifiedCosine_score", "ModifiedCosine_matches", 5)
    return tables


def identifier_rows(spectrums):
    return [[i, s.get("inchikey") or "", s.get("smiles") or ""]
            for i, s in enumerate(spectrums)]


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    mgf_path = os.path.join(args.input_dir, MGF_NAME)
    if not os.path.isfile(mgf_path):
        raise SystemExit("missing input file: %s" % mgf_path)

    spectrums = run_pipeline(mgf_path)
    tables = compute_tables(spectrums)

    os.makedirs(args.output_dir, exist_ok=True)
    write_csv(os.path.join(args.output_dir, "spectrum_identifiers.csv"),
              IDENT_HEADER, identifier_rows(spectrums))
    for name in ["cosine_spectrum_5_top10.csv", "cosine_spectrum_5_min5.csv",
                 "modified_cosine_spectrum_5_min5.csv",
                 "modified_cosine_spectrum_11_min5.csv",
                 "modified_cosine_spectrum_97_min5.csv"]:
        key = name[:-4]
        write_csv(os.path.join(args.output_dir, name), MATCH_HEADER, tables[key])

    print("spectra:", len(spectrums))
    print("outputs written:", sorted(os.listdir(args.output_dir)))


if __name__ == "__main__":
    main()
