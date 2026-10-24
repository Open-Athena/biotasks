# Spectral library processing and all-against-all similarity scoring of a GNPS natural-products MS/MS library

## Objective

A single MGF file of MS/MS reference spectra (GNPS NIH Natural Products Library) is supplied under `inputs/`. You must (1) run the two-stage spectrum-processing pipeline over every spectrum, (2) compute all-against-all pairwise similarities for **both** the (standard) greedy cosine score and the modified cosine score, and (3) report the ranked best-match lists for a set of query spectra. Write the requested products under `outputs/`: the processed library, the two similarity families (score and matched-peak count per pair), the ranked match lists, and per-spectrum peak-count summaries before and after peak filtering.

## Supplied input

- `inputs/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` — MGF text file; one MS/MS spectrum per `BEGIN IONS`/`END IONS` block with metadata parameters (precursor/pepmass, charge, instrument, compound name, InChI, SMILES, library/spectrum identifiers) followed by `mz intensity` peak lines. All spectra in the file are used; the input order (order of blocks in the file) defines the **spectrum index** (0-based) used throughout the outputs.

## Analysis protocol

The protocol is stated scientifically below; its precise operational semantics are those of **matchms 0.30.2** with default function arguments, in the order given (a compatible offline environment is available if you prefer to use it; alternative software is permitted as long as it reproduces these semantics).

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

Undefined-annotation harmonization replaces entries that are empty or one of the aliases `"N/A"`, `"NA"`, `"n/a"`, `"no data"` with the empty string. The pipeline neither adds nor removes spectra: one output record per input spectrum, in input order.

### 2. Peak pipeline (applied to every spectrum after metadata processing, in this order)

1. **Normalize intensities**: divide each peak intensity by the maximum intensity within that spectrum (so the maximum becomes exactly 1). A spectrum whose maximum intensity is ≤ 0 retains no peaks.
2. **Intensity filter**: keep peaks whose normalized intensity is **at least 0.01** (boundary inclusive).
3. **m/z filter**: keep peaks with **10 ≤ m/z ≤ 1000** (both boundaries inclusive).

Peak order within a spectrum, as it comes from the input file, is preserved.

### 3. All-against-all similarity

For every ordered pair of processed spectra (reference `i`, query `j`), including the diagonal self-pairs, compute:

- **Greedy cosine score** (peak matching at zero mass shift only), and
- **Modified cosine score** (Watrous et al., PNAS 2012), in which two peaks may also match after shifting the query spectrum's peak m/z values by the difference in precursor m/z (reference precursor m/z minus query precursor m/z).

Matching rule for both: two peaks are a candidate match if their (possibly shifted) m/z values differ by **at most 0.005** (inclusive). With the default weighting (m/z exponent 0, intensity exponent 1), candidate pairs (the union of zero-shift and mass-shift pairs for the modified score) are considered in order of decreasing intensity product `i_ref · i_query`, each peak on each side being usable at most once; this greedily maximizes the summed intensity products of the chosen one-to-one peak pairing. The score is

`Σ_matched (i_ref · i_query) / (sqrt(Σ_ref i_ref²) · sqrt(Σ_query i_query²))`

and `matches` is the number of peak pairs used. Both scores are reported as N × N matrices (row = reference index `i`, column = query index `j`); the computation is symmetric, so the matrices are symmetric. Every spectrum in this library carries a valid positive precursor m/z after the metadata pipeline, which the modified cosine score requires.

### 4. Ranked best-match lists

For a query spectrum, rank **all** spectra in the library by similarity score, descending. The query spectrum itself is part of the ranking (its self-match ranks at or near the top with score 1). Then, per branch below, optionally drop spectra whose matched-peak count is **below 5** (spectra with exactly 5 matches are kept), and take the first (up to) 10 ranked spectra:

| Branch | Query spectrum (index) | Measure          | Match-count filter |
|--------|------------------------|------------------|--------------------|
| A      | 5                      | Greedy cosine    | none               |
| B      | 5                      | Greedy cosine    | ≥ 5 matches       |
| C      | 5                      | Modified cosine  | ≥ 5 matches       |
| D      | 11                     | Modified cosine  | ≥ 5 matches       |
| E      | 97                     | Modified cosine  | ≥ 5 matches       |

(Index 97 is the spectrum the original analysis singles out for having one of the highest precursor masses.) If several spectra obtain exactly equal scores, their relative order within the tied group is unspecified; any ranking that is non-increasing in score and selects the same rows is acceptable.

## Required outputs

Write the following files under `outputs/`. Floats must be serialized at full precision (shortest round-trip representation or better).

### 1. `processed_spectra.json`

A JSON array with one object per spectrum, **in input order** (array position = spectrum index):

```json
{"spectrum_index": 0, "spectrum_id": "CCMSLIB00000079350", "compound_name": "(2R)-...", "inchikey": "XTJNPXYDTGJZSA-PKOBYXMFSA-N", "inchi": "InChI=1S/...", "smiles": "OC(=O)...", "precursor_mz": 408.156, "peaks": [[103.050735, 0.012904279647174126], ...]}
```

- `spectrum_id`: the library spectrum identifier from the spectrum metadata (GNPS accessions of the form `CCMSLIB…`); empty string if absent.
- `compound_name`, `inchikey`, `inchi`, `smiles`: post-pipeline values; undefined entries are the empty string.
- `precursor_mz`: post-`add_precursor_mz` numeric precursor m/z.
- `peaks`: the retained (m/z, normalized intensity) pairs after the peak pipeline, in input-file peak order, as `[mz, intensity]` pairs.

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
- `score`: the pair's similarity score (full precision); `matches`: the matched-peak count.

### 4. `peak_counts.csv`

CSV with header `spectrum_index,n_peaks_before_filtering,n_peaks_after_filtering`, one row per spectrum, in spectrum-index order: the number of peaks as imported (before any peak processing) and the number of peaks remaining after the peak pipeline.

## Environment and limits

Software choice is open; the reference semantics for the pipeline and similarity measures are those of matchms 0.30.2 as described above. Execution is offline. Limits: 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s wall-clock for the full analysis. Numerical comparison of scores will use a small (to-be-calibrated) absolute tolerance; match counts are integers and must agree exactly. Cross-output consistency is checked (e.g. the diagonal `matches` of each score matrix equals each spectrum's retained peak count, and `matched_spectrum_index` rows join to `processed_spectra.json`).

## Acceptance rules

## Acceptance rules for the four output files

All files are read only from the declared relative paths under the supplied output root (`processed_spectra.json`, `similarity_scores.npz`, `best_matches.csv`, `peak_counts.csv`). Files at any other location — including under an extra `outputs/` subdirectory of the root — do not satisfy the requirement. Missing, malformed, truncated or unreadable files fail the corresponding checks; missing values, nonfinite numbers, NaN and out-of-range entries are rejected, not treated as matches.

Numeric comparison bases: all tolerances are absolute limits on the observable difference from the reference value, i.e. `|dataset value − reference value| ≤ tol` per entry (per-element; no dimension or class conditioning, no rounding before comparison). Integers and string/categorical identifiers are compared exactly.

1. `processed_spectra.json` — JSON array with exactly one record per spectrum in array order; each record's `spectrum_index` must equal its array position (0-based). Required keys: `spectrum_index`, `spectrum_id`, `compound_name`, `inchikey`, `inchi`, `smiles`, `precursor_mz`, `peaks`. The five identifier/annotation strings are compared exactly (case-sensitive; an undefined or absent post-pipeline value is the empty string). `precursor_mz` is compared within `1e-6` (m/z Daltons). `peaks` is the ordered, boundary-inclusive retained list (`[m/z, intensity]` pairs); each m/z is compared within `1e-6` Da and each normalized intensity within `1e-9`, in the same peak order (numeric field equality at the decoded value, not at the printed decimal count; the shortest round-trip and any notation that decodes to the same value are accepted). The grader additionally verifies that retained peaks lie within `[10, 1000]` m/z and normalized intensity `[0.01, 1.0]` (comparisons against the stated boundary-inclusive filters), that each spectrum's maximum normalized intensity is `1` (an empty retained peak list is only acceptable if the reference retained no peaks), and that no peak is reported with intensity `0` where the reference kept a nonzero value. Extra metadata keys beyond the required ones are ignored.

2. `similarity_scores.npz` — one NumPy `.npz` archive containing exactly the four documented arrays, each a full N×N matrix (N = number of spectra, read from the reference): `cosine_greedy_score`, `modified_cosine_score` (any floating dtype; values compared within `1e-9` of the reference entry, including the diagonal) and `cosine_greedy_matches`, `modified_cosine_matches` (any integer dtype; compared exactly). Row = reference index, column = query index; matrix layout (not score labels/identities) fixes the row↔column orientation, and a submission whose matrices are transposed relative to the reference fails. Nonfinite entries fail. Each score matrix may differ from its transpose by at most `1e-9` (symmetry of the underlying computation; self-scores marginally above `1`, e.g. `1.000000000000003`, are permissible and are compared to the reference, not clipped).

3. `best_matches.csv` — the header must be exactly `query_index,similarity_measure,min_match_filter,rank,matched_spectrum_index,matched_smiles,matched_inchikey,score,matches` in that order; each of the five required branches (labels exactly: `5,CosineGreedy,none`; `5,CosineGreedy,5`; `5,ModifiedCosine,5`; `11,ModifiedCosine,5`; `97,ModifiedCosine,5`) contributes at most `10` ranked rows with `rank = 1..k` (1-based within the truncated branch list, no rank tied). Rows for branches that are not one of the five above are rejected. For each row, `matched_spectrum_index` is an integer spectrum index, used at most once per branch; every reported matched spectrum must be one of the reference top-10 rows (through the filter then the truncate-to-10 order) and every reference top-10 row of every branch must appear — the selection may not be `>10` rows and may not drop one row and substitute another (this unconditionally rejects appended or extra values). Substituting the reference's 11th-ranked entry for its 10th, or reordering rows that do not have exactly equal reference scores, is rejected. For each row, `score` is compared within `1e-9` of the reference matrix entry for `(matched_spectrum_index, query_index)`, `matches` exactly, and `matched_smiles`/`matched_inchikey` must equal the reference record's post-pipeline values for the matched spectrum index (empty string where undefined).

4. `peak_counts.csv` — header exactly `spectrum_index,n_peaks_before_filtering,n_peaks_after_filtering`; verified to be exactly one non-negative integer row per spectrum, in 0-based spectrum-index order; both count columns compared exactly (as-imported count before any peak processing; retained count after the normalization + inclusive `0.01` intensity filter + inclusive `[10, 1000]` m/z filter).

5. Cross-output consistency is separately graded and validated on the submission's own values: the number of retained peaks in `processed_spectra.json`, the after-filtering column of `peak_counts.csv` and the diagonal of both match-count matrices must all report the same retained count for every spectrum index; and every `best_matches.csv` row's `matched_smiles` and `matched_inchikey` must equal the values carried by the record of its `matched_spectrum_index` in the submission's own `processed_spectra.json` (empty string where that spectrum's post-pipeline value is undefined).

## Ranking tie rule

The tie rule is stated once: for ranked lists, two reference rows are tied when their reference query-column scores differ by at most `1e-9`. Within a run of tied reference rows (a tied group), any output order is accepted, and each member of a tied group of size ≥ 2 that straddles a rank may be reported at any of those ranks. No tie was observed among the emitted top-10 entries of any required branch. In all branches the reference's minimum gap between adjacent scores that differ at all is ≥ `1.4e-4`, so exact-match detection is not tolerated-away; reordering non-tied rows is a rejected branch error.

## Software and serialization

No specific software is required; alternative tools are accepted if they reproduce the matchms 0.30.2 default semantics (the public question is the semantic contract). No independent software-equivalence or cross-platform portability beyond the tolerances above is promised: the numeric tolerances are limits on observable output differences, not guarantees that every divergent method is detected, and software that decodes to values within these tolerances reproduces the reference answer.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
