# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: nomarker
#       format_version: '1.0'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# (part1)=
# # part I - basics of matchms
#
# ## Requirements
# For this notebook to work, `matchms` needs to be installed.
# This can be done by running:
#
# ```
# conda create --name matchms python=3.8
# conda activate matchms
# conda install --channel nlesc --channel bioconda --channel conda-forge matchms
# ```

# ## Import MS/MS data
# - matchms has several importing options, e.g.: `load_from_json`, `load_from_mzml`, `load_from_mzxml` etc. Here we are going to use `load_from_mgf`
# - Import spectrum from mgf file downloaded from GNPS (https://gnps-external.ucsd.edu/gnpslibrary, here using `GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf`)

import os
import numpy as np
from matchms.importing import load_from_mgf

path_data = "/inputs" #"..." enter your pathname to the downloaded file
file_mgf = os.path.join(path_data, "GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf")
spectrums = list(load_from_mgf(file_mgf))

print(f"{len(spectrums)} spectrums found and imported")

# ## Inspect spectra
# - Inspect the metadata: inchikey, inchi, smiles
# - Inspect the number of peaks per spectrum

inchikeys = [s.get("inchikey") for s in spectrums]
found_inchikeys = np.sum([1 for x in inchikeys if x is not None])
print(f"Found {int(found_inchikeys)} inchikeys in metadata")

inchi = [s.get("inchi") for s in spectrums]
inchi[:10]

smiles = [s.get("smiles") for s in spectrums]
smiles[:10]

numbers_of_peaks = [len(s.peaks.mz) for s in spectrums]

from matplotlib import pyplot as plt
plt.figure(figsize=(5,4), dpi=150)
plt.hist(numbers_of_peaks, 20, edgecolor="white")
plt.title("Peaks per spectrum (before filtering)")
plt.xlabel("Number of peaks in spectrum")
plt.ylabel("Number of spectra")
#plt.savefig("hist01.png")

# ## Build a data processing pipeline
# Depending on the data that you import, in most cases you might want to further process the spectra. matchms offers numerous 'filters' to process Spectrum objects. They are designed in a way that allows to simply stack them to any processing pipeline you want. In general, `matchms.filtering` contains filters that either will
#
# - harmonize, clean, extend, and/or check the spectrum metadata
# - process or filter spectrum peaks (e.g. remove low intensity peaks, or normalize peak intensities)

from matchms.filtering import default_filters
from matchms.filtering import repair_inchi_inchikey_smiles
from matchms.filtering import derive_inchikey_from_inchi
from matchms.filtering import derive_smiles_from_inchi
from matchms.filtering import derive_inchi_from_smiles
from matchms.filtering import harmonize_undefined_inchi
from matchms.filtering import harmonize_undefined_inchikey
from matchms.filtering import harmonize_undefined_smiles
from matchms.filtering import add_precursor_mz

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


# Here we defined a sequence of filters to be applied to a spectrum, which will apply default filters (a bunch of standard operations to make metadata entries more consistent). Then we run a number of filters that look for inchi, inchikey, and smiles that ended up in wrong fields (`repair_inchi_inchikey_smiles`), and ultimately translate inchi, inchikey, and smiles into another wherever possible.
#
#
# To process the peaks we define another pipeline:

# ### Peak processing pipeline

from matchms.filtering import normalize_intensities
from matchms.filtering import select_by_intensity
from matchms.filtering import select_by_mz

def peak_processing(spectrum):
    spectrum = normalize_intensities(spectrum)
    spectrum = select_by_intensity(spectrum, intensity_from=0.01)
    spectrum = select_by_mz(spectrum, mz_from=10, mz_to=1000)
    return spectrum


# Here we defined a sequence of filters which will normalize the intensities to values between 0 and 1, and finally only keep peaks if they have a normalized intensity > 0.01 and if they have a m/z position between 10 and 1000 Da.
#
#
# Once defined in this way, we can easily apply this processing sequence to all imported spectrums by doing:

spectrums = [metadata_processing(s) for s in spectrums]
spectrums = [peak_processing(s) for s in spectrums]

inchikeys = [s.get("inchikey") for s in spectrums]
inchikeys[:10]

numbers_of_peaks = [len(s.peaks.mz) for s in spectrums]

from matplotlib import pyplot as plt
plt.figure(figsize=(5,4), dpi=150)
plt.hist(numbers_of_peaks, 20, edgecolor="white")
plt.title("Peaks per spectrum (after filtering)")
plt.xlabel("Number of peaks in spectrum")
plt.ylabel("Number of spectra")
#plt.savefig("hist02.png")

# - the filtering did drastically reduce the (initially very high) number of peaks per spectrum
# - this is mostly due to the removal of peaks < 0.01 of the max intensity

# ## Export processed data
# There are multiple options to export your data after processing. Using `save_as_json` or `save_as_mgf` the data can be written back to a `.json` or `.mgf` file.

from matchms.exporting import save_as_json

file_export_json = os.path.join(path_data, "GNPS-NIH-NATURALPRODUCTSLIBRARY_processed.json")
save_as_json(spectrums, file_export_json)

# A alternative that is much faster for reading/writing is to use 'pickle'. Should data handling become an issue (e.g. many thousands spectrums), than this can be a way out.

import pickle

file_export_pickle = os.path.join(path_data, "GNPS-NIH-NATURALPRODUCTSLIBRARY_processed.pickle")
pickle.dump(spectrums, 
            open(file_export_pickle, "wb"))

# ## Compute spectra similarities : Cosine score
# In the following part the Cosine similarity scores between all possible spectra pairs will be calculated.

from matchms import calculate_scores
from matchms.similarity import CosineGreedy

similarity_measure = CosineGreedy(tolerance=0.005)
scores = calculate_scores(spectrums, spectrums, similarity_measure, is_symmetric=True)

scores.scores.shape

scores_array = scores.scores.to_array()
scores_array[:5, :5]["CosineGreedy_score"]

scores_array = scores.scores.to_array()
scores_array[:5, :5]["CosineGreedy_matches"]

# ## Get highest scoring results for a spectrum of interest

best_matches = scores.scores_by_query(spectrums[5], name="CosineGreedy_score", sort=True)[:10]
print([x[1] for x in best_matches])

[x[0].get("smiles") for x in best_matches]

from rdkit import Chem
from rdkit.Chem import Draw

for i, smiles in enumerate([x[0].get("smiles") for x in best_matches]):
    m = Chem.MolFromSmiles(smiles)
    Draw.MolToFile(m, f"compound_{i}.png")

# ## Alternative: Get highest scoring results above min_match criteria

min_match = 5
sorted_matches = scores.scores_by_query(spectrums[5], name="CosineGreedy_score", sort=True)
best_matches = [x for x in sorted_matches if x[1]["CosineGreedy_matches"] >= min_match][:10]
[x[1] for x in best_matches]

# ## Computing spectra similarities between all spectra - Modified Cosine score
# In the following part the **Modified Cosine similarity** scores (Watrous et al., 2012) between all possible spectra pairs will be calculated.
#
# The modified cosine score aims at quantifying the similarity between two
# mass spectra. The score is calculated by finding best possible matches between
# peaks of two spectra. Two peaks are considered a potential match if their
# m/z ratios lie within the given 'tolerance', or if their m/z ratios
# lie within the tolerance once a mass-shift is applied. The mass shift is
# simply the difference in precursor-m/z between the two spectra.
# See Watrous et al. [PNAS, 2012, https://www.pnas.org/content/109/26/E1743]
# for further details.

from matchms.similarity import ModifiedCosine

similarity_measure = ModifiedCosine(tolerance=0.005)
scores = calculate_scores(spectrums, spectrums, similarity_measure, is_symmetric=True)

min_match = 5
sorted_matches = scores.scores_by_query(spectrums[5], name="ModifiedCosine_score", sort=True)
best_matches = [x for x in sorted_matches if x[1]["ModifiedCosine_matches"] >= min_match][:10]
[x[1] for x in best_matches]

scores_array = scores.scores.to_array()

plt.figure(figsize=(6,6), dpi=150)
plt.imshow(scores_array[:50, :50]["ModifiedCosine_score"], cmap="viridis")
plt.colorbar(shrink=0.7)
plt.title("Modified Cosine spectra similarities")
plt.xlabel("Spectrum #ID")
plt.ylabel("Spectrum #ID")
#plt.savefig("modified_cosine_scores.png")

min_match = 5

plt.figure(figsize=(6,6), dpi=150)
plt.imshow(scores_array[:50, :50]["ModifiedCosine_score"] * (scores_array[:50, :50]["ModifiedCosine_matches"] >= min_match), cmap="viridis")
plt.colorbar(shrink=0.7)
plt.title("Modified Cosine spectra similarities (min_match=5)")
plt.xlabel("Spectrum #ID")
plt.ylabel("Spectrum #ID")
#plt.savefig("modified_cosine_scores_min_match5.png")

# This suggests that -for instance- `spectrums[11]` seems to have several related other ones among the first 50 spectrums. Let's have a closer look at it.

min_match = 5
sorted_matches = scores.scores_by_query(spectrums[11], name="ModifiedCosine_score", sort=True)
best_matches = [x for x in sorted_matches if x[1]["ModifiedCosine_matches"] >= min_match][:10]
[x[1] for x in best_matches]

[x[0].get("smiles") for x in best_matches]

# ### Plot the compounds with the highest modified Cosine score

from rdkit import Chem
from rdkit.Chem import Draw

for i, smiles in enumerate([x[0].get("smiles") for x in best_matches]):
    m = Chem.MolFromSmiles(smiles)
    Draw.MolToFile(m, f"compound_{i}.png")

# ## Inspect a case that doesn't work that well...

masses = [s.get("precursor_mz") for s in spectrums]

np.where(np.array(masses) > 600)

min_match = 5
sorted_matches = scores.scores_by_query(spectrums[97], name="ModifiedCosine_score", sort=True)
best_matches = [x for x in sorted_matches if x[1]["ModifiedCosine_matches"] >= min_match][:10]
[x[1] for x in best_matches]

from rdkit import Chem
from rdkit.Chem import Draw

for i, smiles in enumerate([x[0].get("smiles") for x in best_matches]):
    m = Chem.MolFromSmiles(smiles)
    Draw.MolToFile(m, f"compound_{i}.png")


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