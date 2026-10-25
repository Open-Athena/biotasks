import os as _export_os
import csv as _export_csv
import numpy as _export_np

_export_dir = "/work/outputs"
_export_os.makedirs(_export_dir, exist_ok=True)

# 1) Processed spectral library (product of the metadata/peak processing pipelines)
from matchms.exporting import save_as_json as _export_save_as_json
_export_save_as_json(
    spectrums,
    _export_os.path.join(_export_dir, "GNPS-NIH-NATURALPRODUCTSLIBRARY_processed.json"),
)

# 2) All-pairs Modified Cosine results (survives in scores/scores_array)
_export_np.savez(
    _export_os.path.join(_export_dir, "modified_cosine_scores.npz"),
    ModifiedCosine_score=scores_array["ModifiedCosine_score"],
    ModifiedCosine_matches=scores_array["ModifiedCosine_matches"],
)

# 3) Spectrum identifiers to interpret matrix indices (positional order of spectrums)
with open(_export_os.path.join(_export_dir, "spectrum_identifiers.csv"),
          "w", newline="", encoding="utf-8") as _export_fh:
    _export_writer = _export_csv.writer(_export_fh)
    _export_writer.writerow(["spectrum_index", "inchikey", "smiles"])
    for _export_i, _export_s in enumerate(spectrums):
        _export_writer.writerow([_export_i, _export_s.get("inchikey"), _export_s.get("smiles")])

# 4) Top modified-cosine matches for the inspected spectrum spectrums[97] (last surviving best_matches)
with open(_export_os.path.join(_export_dir, "best_matches_spectrum_97.csv"),
          "w", newline="", encoding="utf-8") as _export_fh:
    _export_writer = _export_csv.writer(_export_fh)
    _export_writer.writerow(["rank", "smiles", "inchikey",
                             "ModifiedCosine_score", "ModifiedCosine_matches"])
    for _export_i, _export_match in enumerate(best_matches):
        _export_writer.writerow([_export_i,
                                 _export_match[0].get("smiles"),
                                 _export_match[0].get("inchikey"),
                                 float(_export_match[1]["ModifiedCosine_score"]),
                                 int(_export_match[1]["ModifiedCosine_matches"])])
