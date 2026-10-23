## Measured facts (from supplied evidence and pinned package source)

- Executed reference: MDAnalysis 2.11.0 / MDAnalysisTests 2.11.0 / numpy 2.5.4 / pandas 3.1.0 (trial/environment.txt); three exported CSVs recorded and byte-identical across two replay runs.
- Group-selection weighting in the executed code: with `weights='mass'` and default `weights_groupselections=False`, `_prepare` (rms.py L691–711, relying on `iterable('mass')==False` from util.py L1102–1114) propagates mass weights to all `groupselections`. This contradicts the notebook prose ("these remain unweighted below") and the class docstring confirms mass applies to both (rms.py L446). Public brief therefore defines the mass table's domain columns as mass-weighted.
- Group RMSDs are computed `center=False, superposition=False` against raw reference group coordinates at ref_frame after the global select-group fit (rms.py L733–741, L800–824); backbone = N/CA/C/O (selection.py L1309–1322).
- Weight mean-normalization (rms.py L708–721) is RMSD-scale-invariant, hence not imposed on solvers.
- Recorded headers/row structure verified by direct reads: 98 data rows per trajectory table, full-precision decimals, frame-0 rows are numerical self-RMSD noise (~1e-7 Å), `Time` is frame-proportional with reader-dependent rounding (dt ≈ 1 − 8.8e-8 per frame in the reference reader).
- DCD contains 98 frames (consistent with all recorded outputs); AdK has 214 residues (log: C-alpha charges shape (214,)).

## Input materialization (proposed)

- Solver inputs = `MDAnalysis.tests.datafiles` PSF/DCD/CRD from the pinned MDAnalysisTests 2.11.0 wheel installed offline in the solver environment (same lock as reference). Construction must record the three file hashes at build time so input identity is pinned.
- Do NOT stage the raw structure files as standalone task inputs: the provenance data-redistribution review is explicitly "not yet established". If direct staging is later preferred, it requires that review first.
- A compatible supplied environment is convenience only; the public contract is the five CSV specifications.

## Endpoint recovery (required before validation)

Two required endpoints are absent from the append-only exports because the notebook overwrites `R`/`df` and the scalar result is unstored. Under the approved recovery policy, construction must rerun the **unchanged original source calls** with separate provenance:

1. `R = rms.RMSD(u, u, select='backbone', groupselections=[CORE, LID, NMP], ref_frame=0); R.run()` followed by the original DataFrame construction with columns `Frame, Time (ns), Backbone, CORE, LID, NMP` → export as `backbone_rmsd.csv`. (Call text is in `inputs/original.py`; no method or input changes.)
2. `rms.rmsd(u.select_atoms('backbone').positions, ref.select_atoms('backbone').positions, center=True, superposition=True)`, executed with the required original state: universes freshly loaded and `u` still at frame 0 (place the recovery run before any trajectory iteration, or rewind `u` to frame 0 — no other state changes) → export as `open_closed_backbone_rmsd.csv`.

Both recovered artifacts need their own determinism check (≥2 fresh-process runs must agree bitwise, as the three exported tables already do).

## Comparison rules (proposed, unvalidated — calibrate before finalizing)

- Parse each CSV; header strings must match exactly; row count must equal the trajectory frame count with `Frame` = 0..N-1 in order (exact integer identity). RMSD columns compared element-wise as approximations of the same quantity; compare `Frame`/`Time` columns as identity metadata across the four trajectory tables (must agree with each other).
- Calibration set for acceptable results: the recorded reference values; an independent recomputation via a separate implementation (e.g. direct Kabsch rotation + weighted RMSD from parsed coordinates) that satisfies the written definitions. Measure the element-wise deviations of acceptable variants to set an absolute tolerance (cover the ~1e-7 self-RMSD frame-0 boundary rows). Do not adopt any tolerance number before this measurement.
- Calibration set for unacceptable results (must fail, with margins recorded): unweighted instead of mass-weighted domain columns in `mass_weighted_rmsd.csv`; per-domain refitting or re-centering of group RMSDs; fitting group changed (all atoms instead of backbone in output 1; all alpha carbons instead of CORE alpha carbons in output 2); ref_frame other than 0; CRD used as the trajectory reference; charges or a different weighting substituted for residue numbers; open/closed comparison computed without centering/superposition or against the last trajectory frame.
- `Time (ns)` column: unresolved choice — exact match privileges the MDAnalysis DCD-reader convention; propose grading only that it is frame-proportional, strictly increasing and within reader-rounding of the reference values (integers from another reader would be scientifically equivalent since the DCD stores no times). Decide at executable validation; do not leak the recorded values.

## Open items

- Data-redistribution review pending (only blocks raw-file staging, not the package-based route).
- No tolerance values asserted anywhere in this draft; all comparison rules provisional pending the calibration above.
- Solver/v verifier timeouts per policy (600 s / 120 s), offline; revisitable.
