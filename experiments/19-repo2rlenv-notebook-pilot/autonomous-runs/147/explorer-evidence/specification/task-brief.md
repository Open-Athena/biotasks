# Spectral library processing and all-against-all similarity scoring of a GNPS natural-products MS/MS library

## Objective

A single MGF file of MS/MS reference spectra (GNPS NIH Natural Products Library) is supplied. You must (1) run the notebook's two-stage spectrum-processing pipeline over every spectrum, (2) compute all-against-all pairwise similarities for **both** the (standard) greedy cosine score and the modified cosine score, and (3) report the ranked best-match lists for a set of query spectra, exactly following the analysis protocol below. The final requested products are the processed library, the two similarity families (score and matched-peak count per pair), the ranked match lists, and per-spectrum peak-count summaries before and after peak filtering.

## Supplied input

- `inputs/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` — MGF text file; one MS/MS spectrum per `BEGIN IONS`/`END IONS` block with metadata parameters (precursor/pepmass, charge, instrument, compound name, InChI, SMILES, library/spectrum identifiers) followed by `mz intensity` peak lines. All spectra in the file are used; the input order (order of blocks in the file) defines the **spectrum index** (0-based) used throughout the outputs.

## Analysis protocol

The protocol below is stated scientifically; its precise operational semantics are those of **matchms 0.30.2** with default function arguments, in the notebook's order (an offline environment providing this build can be supplied for convenience; alternative software is permitted as long as it reproduces these semantics).

### 1. Metadata pipeline (applied to every spectrum, in this order, default arguments)

1. `default_filters`
2. `repair_inchi_inchikey_smiles`
3. `derive_inchi_from_smiles`
4. `derive_smiles_from_inchi`
5. `derive_inchikey_from_inchi`
6. `harmonize_undefined_smiles`
7. `harmonize_undefined_inchi`
8. `harmonize_undefined_inchikey`
9. `add_precursor_mz`

Undefined-annotation harmonization replaces entries that are empty or one of the aliases `""`, `"N/A"`, `"NA"`, `"n/a"`, `"no data"` with the empty string. The pipeline neither adds nor removes spectra: the number of spectra is unchanged, one output record per input spectrum in input order.

### 2. Peak pipeline (applied to every spectrum after metadata processing, in this order)

1. **Normalize intensities**: divide each peak intensity by the maximum intensity within that spectrum (so the maximum becomes exactly 1). A spectrum whose maximum intensity is ≤ 0 retains no peaks.
2. **Intensity filter**: keep peaks whose normalized intensity is **at least 0.01** (boundary inclusive; peaks exactly at 0.01 are kept).
3. **m/z filter**: keep peaks with **10 ≤ m/z ≤ 1000** (both boundaries inclusive).

Peak order within a spectrum (as it comes from the input file, ascending in m/z) is preserved.

### 3. All-against-all similarity

For every ordered pair of processed spectra (reference `i`, query `j`), including the diagonal self-pairs, compute:

- **Greedy cosine score** (peak matching at zero mass shift only), and
- **Modified cosine score** (Watrous et al., PNAS 2012), in which two peaks may also match after shifting the query spectrum's peak m/z values by the difference in precursor m/z (reference precursor m/z minus query precursor m/z).

Matching rule for both: two peaks are a candidate match if their (possibly shifted) m/z values differ by **at most 0.005** (inclusive). With the default weighting (m/z exponent 0, intensity exponent 1): candidate pairs (the union of zero-shift and mass-shift pairs for the modified score) are considered in order of decreasing intensity product `i_ref · i_query` (stable ordering for equal products), each peak on each side being usable at most once; this greedily maximizes the summed intensity products of the chosen one-to-one peak pairing. The score is

  `Σ_matched (i_ref · i_query) / (sqrt(Σ_ref i_ref²) · sqrt(Σ_query i_query²))`

and `matches` is the number of peak pairs used. Both scores are reported as an N × N pair of matrices (row = reference index `i`, column = query index `j`; the computation is symmetric, so the matrices are symmetric by construction). Every spectrum in this library carries a valid positive precursor m/z after the metadata pipeline, which the modified cosine score requires.

### 4. Ranked best-match lists

For a query spectrum, rank **all** spectra in the library by similarity score, descending. The query spectrum itself is part of the ranking (its self-match ranks at or near the top with score 1). Then, per branch below, optionally drop spectra whose matched-peak count is **below 5** (spectra with exactly 5 matches are kept), and take the first (up to) 10 ranked spectra:

| Branch | Query spectrum (index) | Measure          | Match-count filter |
|--------|------------------------|------------------|--------------------|
| A      | 5                      | Greedy cosine    | none               |
| B      | 5                      | Greedy cosine    | ≥ 5 matches       |
| C      | 5                      | Modified cosine  | ≥ 5 matches       |
| D      | 11                     | Modified cosine  | ≥ 5 matches       |
| E      | 97                     | Modified cosine  | ≥ 5 matches       |

(Index 97 is the spectrum the original analysis singles out for having one of the highest precursor masses.)

If several spectra obtain exactly equal scores, their relative order within the tied group is unspecified; any ranking that is non-increasing in score and selects the same rows is acceptable (validation will measure whether ties in fact occur inside or at the boundary of the top-10 windows; if they do, tied groups will be compared as sets).

## Required outputs

Write the following files. Floats must be serialized at full precision (shortest round-trip representation or better).

### 1. `processed_spectra.json`

A JSON array with one object per spectrum, **in input order** (array position = spectrum index):

```json
{"spectrum_index": 0, "spectrum_id": "CCMSLIB00000079350", "compound_name": "(2R)-...", "inchikey": "XTJNPXYDTGJZSA-PKOBYXMFSA-N", "inchi": "InChI=1S/...", "smiles": "OC(=O)...", "precursor_mz": 408.156, "peaks": [[103.050735, 0.012904279647174126], ...]}
```

- `spectrum_id`: the library spectrum identifier (e.g. `CCMSLIB…`) from metadata; empty string if absent.
- `compound_name`, `inchikey`, `inchi`, `smiles`: post-pipeline values; undefined entries are the empty string.
- `precursor_mz`: post-`add_precursor_mz` numeric precursor m/z.
- `peaks`: the retained (m/z, normalized intensity) pairs after the peak pipeline, ascending in m/z, as `[mz, intensity]` pairs.

Additional metadata keys may be included but are not required.

### 2. `similarity_scores.npz`

A single NumPy `.npz` archive with four N × N arrays (`N` = number of spectra):

- `cosine_greedy_score` (float64), `cosine_greedy_matches` (integer) — greedy cosine
- `modified_cosine_score` (float64), `modified_cosine_matches` (integer) — modified cosine

Row = reference index, column = query index; diagonal included.

### 3. `best_matches.csv`

CSV with header
`query_index,similarity_measure,min_match_filter,rank,matched_spectrum_index,matched_smiles,matched_inchikey,score,matches`
and one row per ranked entry of each branch A–E above:

- `query_index`: 5, 11 or 97; `similarity_measure`: `CosineGreedy` or `ModifiedCosine`; `min_match_filter`: `none` or `5`.
- `rank`: 1-based rank within the branch's final (post-filter, truncated) list, starting at 1 after truncation; `matched_spectrum_index`: the index of the matched spectrum.
- `matched_smiles`, `matched_inchikey`: the matched spectrum's post-pipeline values (empty string if undefined).
- `score`: the pair's similarity score; `matches`: the matched-peak count.

### 4. `peak_counts.csv`

CSV with header `spectrum_index,n_peaks_before_filtering,n_peaks_after_filtering`, one row per spectrum: the number of peaks as imported (before any peak processing) and the number of peaks remaining after the peak pipeline.

## Environment and limits

Software choice is open; the reference semantics for the pipeline and similarity measures are those of matchms 0.30.2 as described above, and a compatible offline environment is available if you prefer to use it. Execution is offline. Limits: 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s wall-clock for the full analysis. Numerical comparison of scores will use a small (to-be-calibrated) absolute tolerance; match counts are integers and must agree exactly. Cross-output consistency is checked (e.g. the diagonal `matches` of each score matrix equals each spectrum's retained peak count, and `matched_spectrum_index` rows join to `processed_spectra.json`).
