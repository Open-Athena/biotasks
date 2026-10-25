# Spectral similarity analysis of the GNPS-NIH natural-products MS/MS library

## Input
`inputs/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` — the GNPS-NIH natural-products MS/MS spectral library in Mascot Generic Format (~39 MB, 1267 spectra). Spectra appear in a deterministic file order; every positional reference below is a 0-based index into this order (index 0 = first spectrum in the file). The raw file's library-declared inchikey/inchi fields are mostly undefined; do not pre-filter or discard spectra for that reason — identifiers are recovered by the metadata chain below. No spectra are excluded for any other reason; the population of every output is the full parsed library.

## Processing pipeline (matchms tutorial "spectral processing and similarity search" preset)
Use of matchms (~0.30) is permitted; any implementation producing the same filtered spectra, matched peak assignments, scores and counts is equally acceptable.

1. **Parse** all spectra from the MGF in file order, keeping all metadata.
2. **Metadata processing** (per spectrum, in this order): standard metadata-cleanup defaults; repair of identifier entries stored in wrong fields; convert between SMILES / InChI / inchikey wherever possible; harmonize undefined entries of each to the empty string; set `precursor_mz` from the PEPMASS field.
3. **Peak processing** (per spectrum, in this order): normalize all peak intensities by dividing by the maximum peak intensity; retain peaks whose normalized intensity is ≥ 0.01; retain peaks whose m/z is within [10, 1000] inclusive.

## Similarity measures
For each (query, library-spectrum) pair compute a (score, matched_peak_count) result under each measure, with m/z-match tolerance **0.005** (inclusive), intensity power 1, m/z power 0:

- **CosineGreedy score** — candidate peak pairs are (query peak, library peak) with |Δm/z| ≤ 0.005, no mass shift. Pool all candidate pairs, sort by descending product of normalized intensities, and greedily assign indices to distinct peaks of each spectrum (each peak used at most once). Score = (sum of intensity products over assigned pairs) / (√(Σ query intensities²) · √(Σ library intensities²)).
- **Modified cosine score** (Watrous et al., PNAS 2012) — as above, but candidate peak pairs are additionally assessed under a constant mass shift equal to the difference in precursor-m/z of the two spectra; unshifted and shifted candidates are pooled in the same greedy assignment. Requires `precursor_mz` on every spectrum (set in Step 2).

Scores are raw floats in [0, ~1], possibly marginally above 1 by floating-point rounding; report raw values without clamping.

## Per-query match lists
For each specified query, rank **all** library spectra by score descending (the query itself competes and typically appears as the top self-match).

## Required outputs
Write these CSV files (UTF-8, one header row, standard minimal quoting) into the output directory:

1. `spectrum_identifiers.csv` — one row per input spectrum, in file order:
   `spectrum_index,inchikey,smiles`
   (values after Steps 2–3; empty string for unavailable fields)
2. `cosine_spectrum_5_top10.csv` — query at file-order index 5, CosineGreedy score, top 10 by score, no other filter:
   `rank,matched_spectrum_index,inchikey,smiles,cosine_score,matched_peak_count`
3. `cosine_spectrum_5_min5.csv` — same schema and query, restricted to matches with ≥ 5 matched peaks, top 10 by score.
4. `modified_cosine_spectrum_5_min5.csv` — same schema (cosine_score = modified cosine score), query index 5, matches with ≥ 5 matched peaks, top 10 by score.
5. `modified_cosine_spectrum_11_min5.csv` — as Output 4, query index 11.
6. `modified_cosine_spectrum_97_min5.csv` — as Output 4, query index 97.

Conventions:
- `rank` is the 0-based position after sorting by score descending (rank 0 = highest-scoring match).
- `matched_spectrum_index` is the 0-based file-order index of the matched library spectrum.
- `inchikey`/`smiles` in match tables are those of the matched spectrum after Steps 2–3 (identical to the corresponding row of `spectrum_identifiers.csv`).
- `matched_peak_count` is an integer; `cosine_score` is a raw float.
- If fewer than 10 spectra satisfy a table's filter, emit only those rows.
- Each match table requires only the query-vs-all-library rows (computing the full library-vs-library matrix is also acceptable).

## Environment / constraints
- Offline, no network access.
- 4 CPUs, 8 GB RAM, 600-second wall-clock budget.
- Supplied environment (for convenience): matchms 0.30.2, rdkit 2024.9.6, numpy 2.2.6 on Python 3.13. The tolerance, peak-processing thresholds and match-list filters must not be altered.

## Acceptance rules

## Acceptance rules

### File set and parsing
Each of the six required CSV files must exist at its declared path relative to the output root, be UTF-8 text with one header row, and be readable as standard CSV (`csv.reader` semantics, minimal quoting; CRLF and LF line endings both acceptable). Files at any other path (e.g. nested under an extra `outputs/` layer) are at the wrong declared path and are not found. A missing, unreadable, empty (zero data rows where data rows are required), ragged (wrong field count), or malformed file fails its checks.

### CSV conventions
- Header rows are compared exactly (names, order, count): `spectrum_index,inchikey,smiles` for `spectrum_identifiers.csv`; `rank,matched_spectrum_index,inchikey,smiles,cosine_score,matched_peak_count` for the five match tables.
- `spectrum_index`, `rank`, `matched_spectrum_index` and `matched_peak_count` must be nonnegative integers in plain canonical decimal form (no signs, blanks, decimals or exponent notation). An unavailable identifier field is the empty string.
- `cosine_score` must be a finite real number in a standard decimal or exponent form a Python `float()` accepts; `NaN`, `inf` and empty are rejected. Scores are compared as parsed float values, not as strings; any serialization preserving the parsed value (shortest round-trip `repr`, fixed precision, or extra exponent digits) is equally acceptable. Scores are raw, unclamped values (values marginally above 1 from floating-point rounding are not errors).
- Completely blank physical lines are ignored; blank cells are not (an empty `cosine_score` or integer cell fails).

### spectrum_identifiers.csv
One row per input spectrum, in input file order: `spectrum_index` must equal the 0-based row position (0..n-1) in every row. Each row's `inchikey`/`smiles` are compared to the reference values of the same `spectrum_index`. The number of spectra (and therefore rows) is read from the reference table, not hardcoded. An empty `inchikey`/`smiles` is significant: the empty string is compared like any other value (a non-empty value where the reference is empty, or vice versa, fails). No columns beyond the declared ones exist; row-aligned tuple comparison means that repeated identifier values across different spectra do not license different values in a row.

### Match tables (five files)
Each table lists at most 10 rows for its specified query, filter and measure, with `rank` = 0-based file position after sorting. Validation compares, against the reference table, per matched-spectrum value and per table:
- Row count must not exceed 10 and must contain all qualifying spectra if fewer than 10 exist (row count is compared exactly against the reference, which reflects the number of spectra satisfying each table's filter).
- `rank` must equal 0..n-1 consecutively in file order.
- Rows must be sorted by descending `cosine_score` (ascending rank order with non-increasing scores).
- `matched_spectrum_index` must lie in [0, number_of_spectra) and be unique within a table.
- For each listed spectrum index, the `inchikey`, `smiles`, `cosine_score` and `matched_peak_count` must match the reference values for that same index (match tables are compared per spectrum identity, not per row position). Cross-check: the `inchikey`/`smiles` of every listed row must equal the same-index row of the submission's own `spectrum_identifiers.csv`.
- The set of listed `matched_spectrum_index` values must equal the reference set for that table (each of the requested "top 10 ranked lists" is a selection of ten spectra; a different selection of indices is a wrong answer even if all looked-up, in-range and unique).
- Scores are compared with an absolute tolerance of **1e-12** on the floating-point difference between parsed submission and reference values; `matched_peak_count` is compared exactly as an integer.
- Ordering tolerance for ties: if two or more rows carry scores equal to each other within 1e-12 (in the reference's ordering), any permutation of those rows within the tied block is accepted; relative order of rows with scores differing by more than 1e-12 must match the reference. This addresses artifacts of unstable stable-sort behavior on exactly tied scores, not different numeric results.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
