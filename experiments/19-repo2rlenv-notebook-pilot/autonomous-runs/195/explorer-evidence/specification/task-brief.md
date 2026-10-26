# Process a GNPS natural-products MS/MS library and compute all-pairs spectral similarities (greedy cosine and greedy modified cosine)

## Input

- `inputs/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` — the GNPS NIH Natural Products Library as an MGF file (approx. 39 MB). It contains MS/MS spectra with peak lists and per-spectrum metadata (including precursor m/z from `PEPMASS`).

Let N be the number of spectra in the file. The **spectrum index** (0-based) of each spectrum is its position in file order when the file is read sequentially; all outputs below are keyed by this index.

## Objective

1. **Import** all spectra from the MGF in file order.

2. **Metadata processing** per spectrum, applied in this order (this is the matchms 0.30.0 reference pipeline; a pinned environment providing matchms 0.30.0, rdkit 2024.9.6 and numpy 2.2.6 is supplied for convenience — alternative implementations are allowed if they reproduce the same scientific result):
   default metadata harmonization filters; repair of inchi/inchikey/smiles entries placed in wrong fields; derive inchi from smiles; derive smiles from inchi; derive inchikey from inchi; harmonize undefined smiles; harmonize undefined inchi; harmonize undefined inchikey; add/harmonize precursor m/z (taking `precursor_mz`/`precursormz`/`pepmass` as the precursor-m/z source and making it a positive float).

3. **Peak processing** per spectrum, in this order:
   - normalize peak intensities so the maximum intensity of the spectrum equals 1 (a spectrum whose intensities are all ≤ 0 ends up with no peaks);
   - keep only peaks whose normalized intensity is ≥ 0.01 (the bound is inclusive);
   - keep only peaks with m/z between 10.0 and 1000.0 inclusive.

4. **All-pairs similarity**, for both measures below, over all ordered pairs of the processed spectra (including each spectrum with itself):
   - **Greedy cosine (no mass shift)** — peak-matching tolerance 0.005.
   - **Greedy modified cosine** — peak-matching tolerance 0.005, additionally allowing peaks to match after applying the mass shift equal to the difference of the two spectra's precursor m/z.

   For both measures, a candidate peak pair (one peak from each spectrum) matches when their m/z values differ by at most 0.005 after the applicable shift (bound inclusive). Candidate pairs are considered in decreasing order of the product of the two peaks' intensities, and each peak may be used in at most one matched pair (greedy one-to-one assignment). The score is

   `score = (Σ over matched pairs of I_a·I_b) / (‖I_a‖₂ · ‖I_b‖₂)`,

   where `I_a`, `I_I_b` are the processed (normalized) intensity vectors of the two spectra and the norms are over **all** peaks of each spectrum (i.e., the intensity cosine restricted to the matched peaks; no m/z weighting). The **matches** value is the number of matched peak pairs. The score is dimensionless and lies in [0, 1] up to floating-point rounding. For the modified cosine, both the zero-shift and the precursor-mass-shift matchings are considered together in the greedy assignment.

5. **Ranked matches for query #97**: for the query spectrum with spectrum index 97 (a high-precursor-mass case), take all library spectra as candidates, keep those whose modified-cosine match count with the query is ≥ 5, order the survivors by modified-cosine score descending, and take the first (up to) 10 entries. Note that the query's self-comparison is an ordinary candidate.

## Required outputs

All files must be written under `outputs/`.

1. `outputs/processed_spectra.json` — the processed spectral library in matchms' native JSON export format (as written by matchms 0.30.0's `save_as_json`), spectra in spectrum-index order.

2. `outputs/cosine_greedy_scores.npz` — an `.npz` archive (as produced by `numpy.savez`/`savez_compressed`) containing:
   - `CosineGreedy_score`: N×N float array, entry [i, j] = greedy-cosine score between spectrum i and spectrum j;
   - `CosineGreedy_matches`: N×N integer array of matched-peak counts, same layout.

3. `outputs/modified_cosine_scores.npz` — same layout with:
   - `ModifiedCosine_score`: N×N float array;
   - `ModifiedCosine_matches`: N×N integer array.

4. `outputs/spectrum_metadata.csv` — one row per spectrum, in spectrum-index order, with header `spectrum_index,compound_name,precursor_mz,inchikey,smiles`. Missing metadata entries are written as empty fields. This table supplies the identity (compound name, precursor m/z, inchikey, SMILES) of each spectrum index used by the matrices.

5. `outputs/best_matches_spectrum97.csv` — the result of step 5, with header `rank,smiles,inchikey,ModifiedCosine_score,ModifiedCosine_matches`. `rank` is the 0-based position within this final list; `smiles`/`inchikey` are the metadata of the matched (candidate) spectrum; the score/count are the modified-cosine values against query #97.

Matrix entries satisfy: score is symmetric in (i, j); entries [i, i] are each spectrum's self-comparison.

## Resources and environment

Offline execution; 4 CPUs, 8 GiB RAM, 600 s wall-clock limit. The all-pairs calculations involve N×N pairs per measure (N is the number of spectra in the file; the reference run of this exact analysis completes comfortably within the limits). A pinned environment (matchms 0.30.0, rdkit 2024.9.6, numpy 2.2.6 on Python 3.13) is provided; its availability is convenience, not a mandate, except that the metadata-harmonization and export-format semantics follow that reference preset.

Output representations must follow the schemas above exactly (file names, array/field names, column names, index semantics); numerical precision and comparison tolerances are handled at grading.
