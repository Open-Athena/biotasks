## Input materialization to execute
1. Construction must rerun the exact original source's `scores_by_query`/filter calls on the original MGF (sha256 `b7d33f02...f985f72`) under the pinned matchms 0.30.2 environment to export reference CSVs for the branches not already serialized:
   - CosineGreedy spectrums[5] unrestricted top-10 (source call-172),
   - CosineGreedy spectrums[5] min_match≥5 top-10 (source calls 187–188),
   - ModifiedCosine spectrums[5] min_match≥5 top-10 (source call-209),
   - ModifiedCosine spectrums[11] min_match≥5 top-10 (source call-236 row).
   These are unchanged original source operations on the original input (policy-approved faithful recomputation), and must carry separate provenance and independent validation. The exported `best_matches_spectrum_97.csv` already exists as a reference for Output 6, and the identifiers CSV (`spectrum_identifiers.csv`, hash `b864071c5d772712733ae9f7ecddb1750c4647215d4663f283716afa788ee2e7`) for Output 1. Imported proofs: MGF parsing retains 1267 spectra (trial log), 97-table already produced 10 rows (output-audit.json).
2. Export format must exactly match the task schemas (six columns as specified): `rank, matched_spectrum_index, inchikey, smiles, cosine_score, matched_peak_count`.

## Comparison rules to validate before grading
- **Identifiers CSV**: row count = 1267, file-order 0..1266, inchikey/smiles string equality per row; empty-string treatment must be captured if any row is missing a derived identifier (privately, all reference rows are populated per output-audit distinct counts, but do not let a solver assume this — grading compares exact reference strings).
- **Match tables**: schema, row count = min(10, passing-count) as measured in materialized reference; `matched_spectrum_index` set equality with reference set; per-row `matched_peak_count` exact-integer match; score-order non-increasing; `inchikey`/`smiles` consistent with the identifiers row of the same index (cross-file consistency check).
- **Numerical tolerance (unmeasured — calibrate before finalizing)**: propose initial abs tolerance ~1e-9, rel tolerance ~1e-12, to be measured by rerunning reference and by testing against an independent pure-Python reimplementation. Byte-identical replays (two recorded runs) show intra-stack determinism, not portability. A broader cross-stack measurement must precede any finalized tolerance.
- **Tie handling (unmeasured)**: reference 97-table samples show distinct scores; must audit all five reference tables for score ties and specifically for rank-9/10 boundary ties. If ties exist, grader must accept any tie-block permutation; otherwise require exact rank order (probing with tie-preserving checks).
- **Sensitivity probes for grading rule correctness** (validation should confirm these produce nonzero output differences): (a) tolerance 0.005→0.003; (b) ModifiedCosine without mass-shift matching (spectrum-97 733 matched-peaks top row must drop); (c) min_match 6 → fewer/different rows; (d) peak-before-metadata filter order must be tested for numerical effect (expected unchanged, verify empirically). These guards against a solver passing with an over-relaxed or incorrectly-specified grader.

## Output semantics checks
- `cosine_score` must not be clipped or rounded to [0,1]: reference values can marginally exceed 1.0. A solver clamping to 1.0 should fail the numerical check (validate that the grader's tolerance is tighter than this bias).
- Score and matched_peak_count are jointly defined by the greedy match assignment; the peak-count check is exact-integer, the score check is the primary floating-point comparison.

## Pending validation list
1. Materialize missing reference tables (see above) and rerun the two-rerun reproducibility protocol on the new exports.
2. Tie audit across all match tables.
3. Cross-implementation numerical calibration for `cosine_score` tolerance.
4. Confirm sensitivity probes (a)–(d) actually change outputs as expected.
5. Confirm sensitivity/rank-off-by-one and schema-offset probes distinguish a sloppier tolerance variant.

## Classification of changes if any output shifts
- Different spectrum-index universe (e.g., different parsing order, dropped spectra) = different population, not a tolerance issue.
- Different matched index sets at a boundary rank = different candidate/filer application; fail, not average.
- Different matched_peak_count for same pair = different matching semantics (e.g., shifted-pair omission vs different greedy rule); fail.
