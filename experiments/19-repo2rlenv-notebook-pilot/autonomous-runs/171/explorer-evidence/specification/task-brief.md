# Spectral similarity analysis of the GNPSc NIH natural-products spectral library

## Objective
Given a curated GNPS-NIH natural-products MS/MS spectral library file, perform the full processing pipeline and similarity analysis, and report, for four designated query spectra, the library compounds most similar to each query under two related cosine-based similarity measures — the standard "greedy" cosine score and the "modified" cosine score with precursor-m/z-shifted peak matching.

## Input
- `data/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` — GNPS natural-products library in Mascot Generic Format, ~39 MB. Every spectrum's metadata fields (PEPMASS, CHARGE, INCHI, SMILES, compound_name, etc.) are present in the file. Spectra appear in a deterministic file order; all positional references below are 0-based indices into this order (index 0 = first spectrum in the file).
- Self-matches: the raw file's library-declared inchikey/inchi fields are present as undefined/missing entries; do not pre-filter or discard spectra for that reason — they are recovered downstream by the metadata chain below.

## Method
This follows the matchms tutorial "spectral processing and similarity search" preset (matchms ~0.3.x). Use of matchms is permitted but any implementation producing the same filtered spectra, matched peak assignments, scores, and counts is acceptable.

### Step 1 — Parse
Load all spectra from the MGF in file order, including all metadata.

### Step 2 — Metadata processing (per spectrum)
Apply this chain: standard metadata-cleanup defaults, repair of misplaced identifier entries, then convert between SMILES/InChI/inchikey wherever possible, harmonize undefined entries of each to the empty string, and set `precursor_mz` from the PEPMASS field.
(Equivalently, in matchms: `default_filters → repair_inchi_inchikey_smiles → derive_inchi_from_smiles → derive_smiles_from_inchi → derive_inchikey_from_inchi → harmonize_undefined_smiles → harmonize_undefined_inchi → harmonize_undefined_inchikey → add_precursor_mz`.)

### Step 3 — Peak processing (per spectrum)
1. Normalize all peak intensities by dividing by the maximum peak intensity.
2. Retain peaks whose normalized intensity is ≥ 0.01.
3. Retain peaks whose m/z is within [10, 1000], inclusive.

### Step 4 — Pairwise similarity scores
Compute, for each required (query, reference) spectrum pair, a (score, matched_peak_count) result under each measure, with m/z-match tolerance **0.005** (two peaks are candidates when their m/z difference is within the tolerance, inclusive), intensity power 1, m/z power 0:

- **CosineGreedy** — peak pairs match only with no mass shift. Pool all candidate pairs within tolerance, sort by descending product of normalized intensities, and greedily assign indices to distinct peaks of each spectrum (each peak can be used at most once). Score = matched-intensity-product sum divided by √(Σ intensities₁²) · √(Σ intensities₂²).
- **ModifiedCosine** — as above, but candidate peak pairs are additionally assessed under a constant mass shift equal to the difference in precursor-m/z of the two spectra, with pooled (unshifted ∧ shifted) candidate pairs considered together in the same greedy assignment. Reference: Watrous et al., PNAS 2012. Requires `precursor_mz` on every spectrum (set by Step 2).

Both scores are float values in [0, ~1], possibly marginally above 1 due to floating-point rounding; report raw values without clamping.

### Step 5 — Per-query match lists
For each specified query, rank all library spectra by score descending and take the top matches per the per-output filter.

## Required outputs
Write these files under `results/`, as CSV (standard quoting, UTF-8, one header row):

1. `results/spectrum_identifiers.csv` — one row per input spectrum, in file order:
   `spectrum_index,inchikey,smiles`
   (values after Step 2–3 processing; empty string for unavailable fields)

2. `results/cosine_spectrum_5_top10.csv` — for the query at file-order index 5, top 10 matches by CosineGreedy score, no other filter:
   `rank,matched_spectrum_index,inchikey,smiles,cosine_score,matched_peak_count`

3. `results/cosine_spectrum_5_min5.csv` — same schema, same query, restricted to matches with ≥ 5 matched peaks, top 10 by score.

4. `results/modified_cosine_spectrum_5_min5.csv` — same schema (cosine_score = modified cosine score), query index 5, restricted to matches with ≥ 5 matched peaks, top 10 by score.

5. `results/modified_cosine_spectrum_11_min5.csv` — same as Output 4, query index 11.

6. `results/modified_cosine_spectrum_97_min5.csv` — same as Output 4, query index 97.

Conventions:
- `rank` is the 0-based position after sorting by score descending (`rank=0` is the highest-scoring match; the query itself can appear, typically as the self-match with the top score).
- `matched_spectrum_index` is the 0-based file-order index of the matched library spectrum.
- `inchikey`/`smiles` in match tables are those of the matched spectrum after Step 2–3 (identical to the corresponding row of `spectrum_identifiers.csv`).
- `matched_peak_count` is an integer; `cosine_score` a raw float.
- If fewer than 10 spectra satisfy a table's filter, emit only those rows.
- Match tables do not need the full library-vs-library matrix; each requires only the query-vs-all-library rows (though computing all pairs is also acceptable).

Correctness of each output is assessed against the reference results of this pipeline: table membership (by `matched_spectrum_index`), sequence of scores (descending), matched-peak-count agreement, identity/consistency between `inchikey`/`smiles` fields and `spectrum_identifiers.csv`, and score numeric agreement within a tolerance that accounts for floating-point rounding.

## Environment / constraints
- Offline, no network access.
- 4 CPUs, 8 GB RAM, 10 GB disk, 600-second wall-clock budget.
- Supplied environment (for convenience): matchms 0.30.2, rdkit 2024.9.6, numpy 2.2.6 on Python 3.13 (see `pyproject.toml`). Solvers are free to use other software producing the specified outputs. The tolerance, peak-processing thresholds, and match-list filters must not be altered.
