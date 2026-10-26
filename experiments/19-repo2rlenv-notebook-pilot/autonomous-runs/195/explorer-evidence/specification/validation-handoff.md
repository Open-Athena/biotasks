# Private validation handoff

## Input derivation and provenance

- Sole input: `GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf`, 39,095,019 bytes, sha256 `b7d33f02fa35ebebc2c3e8150c57be014a5f4edd556531a7fc8e52913f985f72`, staged from `https://external.gnps2.org/gnpslibrary/GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` (GNPS2 mirror) because the canonical `gnps-external.ucsd.edu` URL returned HTTP 502 at staging time. **Unverified assumption:** byte-identity with the canonical URL was inferred from the identical library path and file size, never measured. Every construction/staging step re-verifies size and sha256.
- Measured input facts (from the passing reference run): 1267 spectra imported in file order; raw metadata contains no `inchikey` entries (log: "Found 0 inchikeys"); `PEPMASS` present (precursor_mz column of the exported metadata table: 1267 finite values, min 147.056, max 963.492, none empty). These are measured facts about *this* file, not guaranteed properties to assert generally.
- Matchms MGF parsing via pyteomics reads records in file order and sorts each spectrum's peaks by m/z (`matchms/importing/parsing_utils.py:98–104`); `load_from_mgf` applies default metadata harmonization in the Spectrum constructor. Spectrum index = file order.

## Endpoint lineage and required recoveries

| Public output | Exists in frozen reference? | Lineage |
|---|---|---|
| `processed_spectra.json` | Yes (2bad9068…, 6,077,302 bytes) | `save_as_json(spectrums)` after `metadata_processing` + `peak_processing` on all loaded spectra (original.py lines 118–119, 143). |
| `spectrum_metadata.csv` | Yes (d6a7487f…) | projection of the processed `spectrums` list: index, `compound_name`, `precursor_mz`, `inchikey`, `smiles` (441 rows have empty `compound_name` in the reference — 826 non-empty). |
| `modified_cosine_scores.npz` | Yes (e4def468…, 1267×1267 both arrays) | final `scores_array = scores.scores.to_array()` after `ModifiedCosine(tolerance=0.005)`, `calculate_scores(..., is_symmetric=True)`. |
| `best_matches_spectrum97.csv` | Yes (57f8b0c6…, 10 rows) | `scores_by_query(spectrums[97], name="ModifiedCosine_score", sort=True)` filtered on `matches >= 5`, first 10; rank 0 is the self-match. |
| `cosine_greedy_scores.npz` | **No — recovery required** | rerun the unchanged source calls `CosineGreedy(tolerance=0.005)` + `calculate_scores(spectrums, spectrums, similarity_measure, is_symmetric=True)` on the identical processed state (original.py lines 159–160). The reference run's log records this calculation completing (two full 1267-iteration progress bars), but **no artifact or values for it exist in any supplied evidence**. Construction must produce it with separate provenance and independent validation before grading; no value may be assumed. |

Recovery is authorized by `task_policy.endpoint_recovery` (faithful recomputation of unchanged source calls, same inputs and state). Do not modify the analysis, filters, tolerances or populations during recovery.

## Scientific meaning and identity constraints

- **Matrices:** entry [i, j] = score between spectrum index i (reference) and spectrum index j (query). `to_array()` yields shape (n_references, n_queries); with `is_symmetric=True` the stored sparse upper triangle is expanded, and both measures are commutative, so the matrix is symmetric. Grading may rely on symmetry but should confirm orientation empirically if comparing against a non-matchms implementation.
- **Score:** intensity-only cosine over matched peaks, normalized by the full-spectrum intensity norms (matchms `spectrum_similarity_functions.py:88–110`, m/z power 0, intensity power 1). Known numerical property (observed in the reference run and output audit): self-scores can exceed 1.0 by float rounding (e.g., 1.000000000000003 in the spectrum-97 CSV) — treat as a tolerance design input, not an error.
- **Matches:** count of matched peak pairs, integer, self-comparison equals the spectrum's post-filtering peak count.
- **Filtering boundaries (verified in matchms 0.30.0 source):** intensity ≥ 0.01 on max-normalized intensities, inclusive (`select_by_intensity.py:37`; omitted `intensity_to` default 200.0 is non-binding post-normalization); m/z ∈ [10, 1000] inclusive (`select_by_mz.py:35`); spectra with all intensities ≤ 0 lose all peaks (`normalize_intensities.py:35–40`). Note the notebook prose says "intensity > 0.01" — the executed semantics is inclusive; the public brief states the corrected boundary.
- **Tolerance boundary:** peak match iff |mz₁ − mz₂| ≤ 0.005 after applicable shift, inclusive (`find_matches`, spectrum_similarity_functions.py:75–84).
- **Modified cosine:** union of zero-shift pairs and pairs under shift = precursor_mz(reference) − precursor_mz(query), then one greedy assignment over the merged pair list (ModifiedCosine.py:108–127). Requires a valid positive precursor_mz on every spectrum; established for this input (see measured input facts).
- **Ranked list (query 97):** descending score order produced by `np.argsort(...)[::-1]` with numpy's default (non-stable) sort (Scores.py:291). **Unresolved representation question:** tie order among equal scores is package/algorithm-specific. Score ties among distinct library spectra are not established to exist or not exist in this data — validation must decide how to treat near-equal scores at the rank-10 boundary and within the list (e.g., accept any ordering consistent with the criterion, or verify ties do not occur). Do not invent a deterministic tie-break as a public fact.
- **min_match:** `matches >= 5`, inclusive; `[:10]` keeps up to 10 rows (fewer only if fewer candidates qualify — the reference has exactly 10).
- **CSV/npz field names** (`ModifiedCosine_score`, etc.) are the executed result-field names, and `CosineGreedy_score`/`CosineGreedy_matches` appear in the executed source; they are required output naming, not incidental.
- **Missing metadata:** reference `spectrum_metadata.csv` writes missing `compound_name` as empty fields; `inchikey`/`smiles` columns are fully populated after the metadata pipeline in the reference run, but completeness was not established as a guaranteed property — treat as a data fact to check, not a requirement invented from the reference.

## Exclusions accounted for (source-backed)

- Plain-cosine top-10 lists for query 5 (both unfiltered and min_match variants), and modified-cosine top-10 lists for queries 5 and 11: deterministic rank-order projections of the graded matrices at single query indices; the terminal interpreted instance (query 97) is retained. Solver is not asked to redo these, and the matrices contain the full information.
- RDKit structure images: plot-only renderings of exported SMILES.
- Peaks-per-spectrum histograms: diagnostic QC; counts recoverable from graded outputs.
- "Found 0 inchikeys in metadata" count: diagnostic inspection of raw metadata.

## Open validation questions / unvalidated assumptions

1. **CosineGreedy recovery** must be executed and independently validated before grading (values unobserved; see lineage table).
2. **Comparison mechanics (unresolved, executably demonstrable only at validation):** npz comparison should load arrays rather than compare bytes (zip containers; note all frozen artifacts were byte-identical across two replays, but array-level comparison is the safe contract); `processed_spectra.json` should be compared at spectrum/peak/metadata level (ordering = spectrum index; peak arrays retain m/z-sorted order); CSVs row-keyed by rank/spectrum_index.
3. **Numerical tolerance calibration** for float scores (greedy numba kernels use `fastmath` on `score_best_matches` — cross-implementation variation is possible; two same-platform replays were byte-identical, which is not a portability proof). Left to validation.
4. **Tie handling** in ranked lists (above).
5. **Input provenance:** canonical-URL byte-identity to the staged mirror file was never measured; re-verify hash at materialization.
6. **Environment-idempotence caveat (from outcome.json):** the notebook targeted a 2021-era matchms; the reference preset is matchms 0.30.0 on Python 3.13. The task defines the method by the pinned preset; equivalence to older releases was not compared value-by-value and is not asserted.
7. Resource headroom is measured, not guaranteed: reference run 89 s, peak child RSS ≈ 0.95 GiB (2 replays identical), limits 600 s / 8 GiB / 4 CPUs, offline.
