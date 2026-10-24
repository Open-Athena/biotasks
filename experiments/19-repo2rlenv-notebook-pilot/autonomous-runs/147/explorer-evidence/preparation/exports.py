import csv as _exp_csv
from matchms.exporting import save_as_json as _exp_save_as_json

_exp_out_dir = "/work/outputs"
os.makedirs(_exp_out_dir, exist_ok=True)

# 1) Processed spectra library (end product of the metadata + peak pipelines)
_exp_processed_json = os.path.join(_exp_out_dir, "processed_spectra.json")
_exp_save_as_json(spectrums, _exp_processed_json)

# 2) All-pairs Modified Cosine similarity: scores and matched peak counts
_exp_scores_npz = os.path.join(_exp_out_dir, "modified_cosine_scores.npz")
np.savez(
    _exp_scores_npz,
    modified_cosine_score=scores_array["ModifiedCosine_score"],
    modified_cosine_matches=scores_array["ModifiedCosine_matches"],
)

# 3) Spectrum identifiers (context for the similarity matrix and match lists)
_exp_ids_csv = os.path.join(_exp_out_dir, "spectrum_identifiers.csv")
with open(_exp_ids_csv, "w", newline="", encoding="utf-8") as _exp_f:
    _exp_w = _exp_csv.writer(_exp_f)
    _exp_w.writerow(["spectrum_index", "compound_name", "inchikey", "smiles"])
    for _exp_i, _exp_s in enumerate(spectrums):
        _exp_w.writerow([
            _exp_i,
            _exp_s.get("compound_name") or "",
            _exp_s.get("inchikey") or "",
            _exp_s.get("smiles") or "",
        ])

# 4) Top Modified Cosine matches (min_match >= 5) for the queried spectrum
#    (query = spectrums[97] in the original script)
_exp_matches_csv = os.path.join(_exp_out_dir, "best_matches_spectrum_97.csv")
with open(_exp_matches_csv, "w", newline="", encoding="utf-8") as _exp_f:
    _exp_w = _exp_csv.writer(_exp_f)
    _exp_w.writerow([
        "query_index", "query_smiles", "rank",
        "matched_smiles", "matched_inchikey",
        "modified_cosine_score", "modified_cosine_matches",
    ])
    for _exp_r, _exp_entry in enumerate(best_matches, start=1):
        _exp_ref = _exp_entry[0]
        _exp_score_entry = _exp_entry[1]
        _exp_w.writerow([
            97,
            spectrums[97].get("smiles") or "",
            _exp_r,
            _exp_ref.get("smiles") or "",
            _exp_ref.get("inchikey") or "",
            float(_exp_score_entry["ModifiedCosine_score"]),
            int(_exp_score_entry["ModifiedCosine_matches"]),
        ])