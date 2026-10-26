import os as _exp_os
import csv as _exp_csv
import numpy as _exp_np
from matchms.exporting import save_as_json as _exp_save_as_json

_exp_out_dir = "/work/outputs"
_exp_os.makedirs(_exp_out_dir, exist_ok=True)

# Endpoint 1: processed spectral library (metadata + peak pipelines applied)
_exp_save_as_json(spectrums, _exp_os.path.join(_exp_out_dir, "processed_spectra.json"))

# Endpoint 2: full Modified Cosine similarity matrices (final state of scores_array)
_exp_np.savez_compressed(
    _exp_os.path.join(_exp_out_dir, "modified_cosine_scores.npz"),
    ModifiedCosine_score=scores_array["ModifiedCosine_score"],
    ModifiedCosine_matches=scores_array["ModifiedCosine_matches"],
)

# Context table giving the spectrum index referenced by the matrices their metadata
with open(_exp_os.path.join(_exp_out_dir, "spectrum_metadata.csv"), "w", newline="", encoding="utf-8") as _exp_f:
    _exp_w = _exp_csv.writer(_exp_f)
    _exp_w.writerow(["spectrum_index", "compound_name", "precursor_mz", "inchikey", "smiles"])
    for _exp_i, _exp_s in enumerate(spectrums):
        _exp_w.writerow([
            _exp_i,
            _exp_s.get("compound_name"),
            _exp_s.get("precursor_mz"),
            _exp_s.get("inchikey"),
            _exp_s.get("smiles"),
        ])

# Endpoint 3: final ranked matches (ModifiedCosine, min_match=5) for spectrums[97]
with open(_exp_os.path.join(_exp_out_dir, "best_matches_spectrum97.csv"), "w", newline="", encoding="utf-8") as _exp_f:
    _exp_w = _exp_csv.writer(_exp_f)
    _exp_w.writerow(["rank", "smiles", "inchikey", "ModifiedCosine_score", "ModifiedCosine_matches"])
    for _exp_r, _exp_match in enumerate(best_matches):
        _exp_spec, _exp_score = _exp_match
        _exp_w.writerow([
            _exp_r,
            _exp_spec.get("smiles"),
            _exp_spec.get("inchikey"),
            _exp_score["ModifiedCosine_score"],
            _exp_score["ModifiedCosine_matches"],
        ])
