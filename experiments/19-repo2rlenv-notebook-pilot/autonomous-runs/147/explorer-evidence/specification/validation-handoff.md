## Input materialization

- Single input: stage `GNPS-NIH-NATURALPRODUCTSLIBRARY.mgf` at `inputs/` (task-relative). The trial staging used the byte-identical copy committed in the matchms-docs repository at the notebook's pinned revision (primary GNPS endpoint unreachable; identity pinned by size 38,997,460 bytes and sha256 9276602a818f91334e56f5bc7719c6924736a029d5e1a22026f52b18255d9f85 — keep this identity in the manifest; do not surface hashes in the public brief).
- No supplied intermediates or scope reductions; the whole pipeline runs from the MGF.

## Private comparison rules (proposed; to be validated, not yet a contract)

**Output 1 (`processed_spectra.json`).** Parse; check array length equals the spectrum count N of the MGF. Compare per record, by array position: exact string equality for spectrum_id/compound_name/inchikey/inchi/smiles (undefined → ""); floats (precursor_mz, peaks mz/intensity) with a calibrated absolute tolerance τ. Peaks: first probe the staged MGF that every raw peak list is ascending (and ideally strictly increasing) in m/z — the greedy kernel assumes ascending order; if confirmed, compare peak lists elementwise after validating the solver output is ascending; also probe for duplicate m/z values within a spectrum. Include zero-length `peaks` handling: probe the reference for spectra that retain 0 peaks after filtering (max-intensity peak always survives the intensity filter within the [10,1000] m/z window, but a spectrum with all peaks outside 10–1000 would retain none — measure whether this occurs; if it does, require the record with empty `peaks` and `n_peaks_after_filtering` 0).

**Output 2 (`similarity_scores.npz`).** Shapes (N,N) for all four arrays. `matches` arrays: exact integer equality (boundary caveat below). `score` arrays: max-absolute-difference ≤ τ, τ to be calibrated. Symmetry check: matrix equals its transpose within τ. Diagonal check: `score[i,i]` ≈ 1.0 (note observed values slightly above 1, e.g. 1.0000000000000003 — τ must tolerate this), and `matches[i,i]` equals spectrum i's `n_peaks_after_filtering` from Output 4 (internal consistency probe; also detects dropped or reordered spectra).

**τ calibration (must run before finalizing; do not ship an uncalibrated threshold).** The score kernel is numba-compiled with `fastmath=True` (spectrum_similarity_functions.py:89), so bitwise identity across CPU/compiler is not guaranteed. Proposed: (a) rerun the reference in a second environment (different CPU/BLAS or reordered summation) and measure the distribution of |Δscore|; (b) confirm the chosen τ accepts all reruns while rejecting deliberately wrong variants (below); τ should be an absolute tolerance on scores in [0,1+ε].

**Output 3 (`best_matches.csv`).** For each branch A–E: exactly the expected branch rows (A: 10 rows unfiltered; B–E: up to 10 rows). Check schema/order: `rank` sequential from 1; scores non-increasing within each branch; `matches` ≥ 5 in branches B–E; branch A may contain fewer than 5 matches. Compare `matched_spectrum_index` sequences, `matches` integers exactly, and `score` within τ. `matched_smiles`/`matched_inchikey` must equal the corresponding Output 1 record (join consistency). Self-match handling: query's own index must appear (expected at rank 1 with score ≈1) — confirm in each branch whether the query's self-match meets the ≥5 filter in branches B–E (probe: if not, it is legitimately absent; do not require presence).
**Tie probes (must run):** for each branch, compute the ranked list down to rank 12 and check for exact score ties inside the top 10 and spanning ranks 10/11 (filter boundary too: ties at matches==5). If ties exist at any consequential boundary, compare tied groups as sets and document; if no ties, demand exact rank order. Sorting detail: `scores_by_query` uses `np.argsort()[::-1]` with default (unstable) quicksort (`Scores.py:290–295`), so tie order is implementation-defined — measure, don't assume.

**Output 4 (`peak_counts.csv`).** N rows, indices 0..N−1 in order; integers exact; `n_peaks_after_filtering` equals `len(peaks)` per record of Output 1.

## Discriminating variants to test against (must produce failures)

1. Exclusive intensity threshold (drop peaks at exactly 0.01) — probe how many retained peaks sit at exactly 0.01 to confirm the boundary is discriminating.
2. Exclusive m/z bounds (drop m/z exactly 10 or 1000) — probe counts at the bounds.
3. `min_match` as strictly-greater-than-5 in branches B–E.
4. Branch A implemented with the ≥5 filter (or branches B–E without it).
5. Modified-cosine shift sign inverted (query − reference instead of reference − query).
6. Greedy pairing order ascending instead of descending intensity product.
7. Dropping the diagonal self-match from ranked lists or matrices.
8. Cosine computed without intensity normalization or normalized per-file (global max) instead of per-spectrum.
9. Match-count matrices compared with float tolerance instead of exact integers (boundary caveat: peaks with |Δm/z| exactly equal to 0.005 — probe count; if nonzero, matches comparisons near those pairs need scrutiny).

## Unvalidated assumptions to resolve before releasing the solver draft

- No exact score ties in/near any top-10 window (probe as above).
- Raw MGF peak lists ascending in m/z; no duplicate m/z within spectra.
- No spectra dropped or returned as None by any metadata filter (trial evidence: identifier table has N rows — confirm N matches the MGF block count).
- Every spectrum has a positive numeric precursor m/z post-pipeline (trial run passed ModifiedCosine's assertions — reconfirm on the materialized input).
- JSON serialization is lossless for the floats involved (round-trip check).
- Grading/verification runtime: parsing ~6 MB JSON + ~50 MB npz + small CSVs fits the 120 s verifier timeout (expected yes; confirm).

## Evidence citations for the private record

Boundary inclusivity: matchms 0.30.2 `select_by_intensity.py:37`, `select_by_mz.py:35`; normalization: `normalize_intensities.py:35–45`; matching kernel and fastmath: `spectrum_similarity_functions.py:72–111`; modified-cosine shift/union/stable sort: `ModifiedCosine.py:106–136`; greedy sort: `CosineGreedy.py:86–103`; sort/tie semantics and identity-based query lookup: `Scores.py:279–296`; undefined-alias harmonization: `harmonize_undefined_inchikey.py:32–43`; JSON export shape: `save_as_json.py` + `Spectrum.to_dict` (`peaks_json`), confirmed against the recorded reference artifact. Execution facts: `trial/result.json` (94 s, ~0.98 GiB RSS, both similarity runs completed), `output-audit.json` (N=1267 rows; 0 empty inchikey/smiles), two byte-identical replays (serialization-level only). Reference values seen during inspection remain private and are not embedded in the public brief.
