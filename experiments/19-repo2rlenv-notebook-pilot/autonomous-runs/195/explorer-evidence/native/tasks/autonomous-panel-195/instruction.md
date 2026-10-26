# Process a GNPS natural-products MS/MS library and compute all-pairs spectral similarities

## Input

- `inputs/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` — the GNPS NIH Natural Products Library as an MGF file (~39 MB). It contains MS/MS spectra with peak lists and per-spectrum metadata (including the precursor m/z, provided by the MGF `PEPMASS` field).

Let N be the number of spectra in the file. The **spectrum index** (0-based) of each spectrum is its position in file order when the file is read sequentially; all outputs below are keyed by this index.

## Objective

1. **Import** all spectra from the MGF in file order.

2. **Metadata processing** per spectrum, in this order (these are the matchms 0.30.0 reference-pipeline semantics; a pinned environment providing matchms 0.30.0, rdkit 2024.9.6 and numpy 2.2.6 is supplied for convenience — alternative implementations are allowed if they reproduce the same scientific result):
   - default metadata harmonization filters;
   - repair of inchi/inchikey/smiles entries placed in wrong fields;
   - derive inchi from smiles;
   - derive smiles from inchi;
   - derive inchikey from inchi;
   - harmonize undefined smiles;
   - harmonize undefined inchi;
   - harmonize undefined inchikey;
   - add/harmonize precursor m/z (taking `precursor_mz`/`precursormz`/`pepmass` as the precursor-m/z source and making it a positive float).

3. **Peak processing** per spectrum, in this order:
   - normalize peak intensities so the maximum intensity of the spectrum equals 1 (a spectrum whose intensities are all ≤ 0 ends up with no peaks);
   - keep only peaks whose normalized intensity is ≥ 0.01 (bound inclusive);
   - keep only peaks with m/z between 10.0 and 1000.0 inclusive.

4. **All-pairs similarity**, for both measures below, over all ordered pairs of the processed spectra (including each spectrum with itself):
   - **Greedy cosine (no mass shift)** — peak-matching tolerance 0.005.
   - **Greedy modified cosine** — peak-matching tolerance 0.005, additionally allowing peaks to match after applying the mass shift equal to the difference of the two spectra' precursor m/z; the zero-shift and the precursor-mass-shift candidate matchings are considered together in the greedy assignment.

   For both measures, a candidate peak pair (one peak from each spectrum) matches when their m/z values differ by at most 0.005 after the applicable shift (bound inclusive). Candidate pairs are considered in decreasing order of the product of the two peaks' intensities, and each peak may be used in at most one matched pair (greedy one-to-one assignment). The score is

   `score = (Σ over matched pairs of I_a·I_b) / (‖I_a‖₂ · ‖I_b‖₂)`,

   where `I_a`, `I_b` are the processed (normalized) intensity vectors of the two spectra and the norms are over **all** peaks of each spectrum (intensity cosine restricted to the matched peaks; no m/z weighting). The **matches** value is the number of matched peak pairs. The score is dimensionless and lies in [0, 1] up to floating-point rounding.

5. **Ranked matches for spectrum index 97** (a high-precursor-mass case): take all library spectra as candidates, keep those whose modified-cosine match count with the query is ≥ 5 (inclusive), order the survivors by modified-cosine score descending, and take the first (up to) 10 entries. The query's self-comparison is an ordinary candidate.

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

Score matrices are symmetric in (i, j); diagonal entries are each spectrum's self-comparison.

## Resources and environment

Offline execution; 4 CPUs, 8 GiB RAM, 600 s wall-clock limit. The all-pairs calculations involve N×N pairs per measure; the reference run of this exact analysis completes comfortably within these limits. A pinned environment (matchms 0.30.0, rdkit 2024.9.6, numpy 2.2.6 on Python 3.13) is provided; its availability is convenience, not a mandate, except that the metadata-harmonization and export-format semantics follow that reference preset.

Output representations must follow the schemas above exactly (file names, array/field names, column names, index semantics); numerical precision and comparison tolerances are handled at grading.

## Acceptance rules

## Acceptance rules (grading addendum)

All five declared files are read from the supplied submission root at exactly the declared relative paths (`processed_spectra.json`, `cosine_greedy_scores.npz`, `modified_cosine_scores.npz`, `spectrum_metadata.csv`, `best_matches_spectrum97.csv`); files placed in an additional nested directory (e.g. an extra `outputs/` layer) are at the wrong paths and are treated as missing. Every required file must be present and non-empty.

**Identity and ordering.** The spectrum index is the 0-based file-order position; N is the spectrum count of the reference. `processed_spectra.json` must be a JSON array of N spectrum objects in spectrum-index order. `spectrum_metadata.csv` must contain exactly one row per spectrum index, numbered 0..N-1 in order (no duplicates, no gaps, no reordering — index order is part of the requested output). `best_matches_spectrum97.csv` rows are compared in rank order (rank 0, 1, ... as listed). Row order is not normalized away for CSV outputs.

**processed_spectra.json.** Each spectrum entry must be a JSON object whose set of metadata field names equals that of the reference entry at the same index (no extra and no missing fields). String-valued fields (e.g. compound_name, inchikey, smiles, and other harmonized metadata strings) are compared as exact strings; missing metadata is an empty string, not `null` or a placeholder. `charge` is an integer-valued field: an integer or a JSON number with the same value is accepted; booleans and strings are not. `peaks_json` must be a list of `[m/z, intensity]` pairs given as JSON numbers (strings are rejected) with all values finite; within each spectrum the peak lists are compared after canonical m/z-then-intensity ordering (so a different within-spectrum ordering is accepted), with peak counts exactly equal and m/z and normalized-intensity values equal within 1e-9 absolute.

**npz archives.** Each archive must contain exactly the two named arrays and no other keys (`CosineGreedy_score` + `CosineGreedy_matches`; `ModifiedCosine_score` + `ModifiedCosine_matches`). Scores must be a 2-D floating-point array and matches a 2-D integer array, both shaped N x N in spectrum-index layout, symmetric in (i, j). Nonfinite (NaN/inf) scores and negative match counts are rejected. Scores are compared to the reference within 1e-8 absolute (pure absolute tolerance; no relative term and no denominator). Match counts are compared exactly as integers. Conversion of a whole score matrix to a narrower floating type (e.g. float32) is not accepted: it must preserve the reference values within the stated tolerance.

**spectrum_metadata.csv.** Header row must be exactly `spectrum_index,compound_name,precursor_mz,inchikey,smiles` (field names and order). compound_name, inchikey and smiles are compared as exact strings; missing metadata is an empty field. `precursor_mz` must parse as a finite number and equal the reference value within 1e-9 absolute; any plain decimal formatting of the same value (including exponent notation) is accepted.

**best_matches_spectrum97.csv.** Header row must be exactly `rank,smiles,inchikey,ModifiedCosine_score,ModifiedCosine_matches`. `rank` must run 0.. in listed order; at most 10 rows. Scores must be non-increasing down the list. `ModifiedCosine_matches` must be integers >= 5. `smiles`/`inchikey` are the metadata of the matched candidate spectrum, compared as exact strings. `ModifiedCosine_score` must equal the reference value within 1e-8 absolute and `ModifiedCosine_matches` must equal the reference integer exactly. Additionally, cross-file consistency is enforced against the submission's own outputs: each row's score and match count must occur in row 97 of the submitted `ModifiedCosine_score`/`ModifiedCosine_matches` matrices at some candidate index whose row in the submitted `spectrum_metadata.csv` carries that row's smiles/inchikey.

**CSV encoding.** CSVs are parsed as standard comma-separated with quoting per RFC 4180 with a single header row; text encoding is UTF-8. CRLF and LF line endings are both accepted; any quoting style that decodes to the same field values is accepted. Row counts must match the reference exactly (no extra trailing rows or ragged rows).

**Reference values are never disclosed**; all comparisons are computed against the private reference outputs at grading time.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
