PRIVATE VALIDATION HANDOFF — mdanalysis-rmsd

## Endpoint lineage

| # | Endpoint | Source call (inputs/original.py) | Captured? | Reference artifact |
|---|---|---|---|---|
| A | open-vs-closed backbone RMSD scalar | lines 92-95, bare `rms.rmsd(...)` on `u.backbone` (PSF+DCD, current frame) vs `ref.backbone` (PSF+CRD), center=True, superposition=True, unweighted | NO — recovery required | to be recovered by rerun (`open_closed_backbone_rmsd.json`) |
| B | backbone + CORE/LID/NMP table | lines 107-112 `rms.RMSD(u, u, select='backbone', groupselections=[CORE,LID,NMP], ref_frame=0)`, unweighted | NO — `R`/`df` rebound at 149/152; recovery required | recovered table |
| C | Cα-CORE table | lines 147-152 `rms.RMSD(ca, ca, select=CORE, ref_frame=0)`, unweighted | YES | `rmsd_calpha_core.csv` (sha dc413717...) |
| D | mass-weighted table | lines 167-171 `weights='mass'`, no ref_frame (default 0), groupselections CORE/LID/NMP | YES | `rmsd_mass_weighted.csv` (20841677...) |
| E | resid-weighted table | lines 198-205 `weights=ag.resids`, `weights_groupselections=[core.resids, lid.resids, nmp.resids]`, default ref_frame 0 | YES | `rmsd_resid_weighted.csv` (55d28d1e...) |

Recovery (A and B) is approved under `endpoint_recovery`: re-execute the unchanged calls on freshly constructed Universes (`u = mda.Universe(PSF, DCD)` freshly loads at frame 0 — construction must verify this state assumption), with separate provenance. Neither recovered artifact has been observed in this session; values must not be asserted until construction records them.

## Measured facts (from execution/inspection in this session)

- Executed environment: Python 3.13.13, MDAnalysis 2.11.0, MDAnalysisTests 2.11.0, pandas 3.1.0, numpy 2.5.4 (trial/environment.txt; full lock retained). Exit 0, ~3.8 s.
- Reference CSVs: 98 data rows, 0-based frames 0-97 (an input property of adk_dims.dcd, not an answer).
- `time_ps` observed column: min 0.9999999119200186, max 97.99999136816182, i.e. t ≈ (frame+1)·dt with dt ≈ 0.9999999119200186 ps (DCD header float32 parsing by MDAnalysis DCDReader). Comparator must use a tolerance for this column (relative ~1e-6 covers the dt-vs-1.0 discrepancy and any (frame+1)·1.0 reconstruction).
- Frame-0 self-reference RMSDs are near 1e-7/1e-8 (not exactly 0) due to float32 coordinates and float64 centering; tolerance must accommodate.
- Same Frame/Time columns appear in all three exported reference CSVs; RMSD values in Å.

## Consequential method facts, verified in pinned mdanalysis-2.11.0 source (analysis/rms.py, core/selection.py, re-read in this session)

1. **Mass propagation to group selections** (`_prepare`, rms.py:691-711): when `weights_groupselections` is falsy and `self.weights` is non-iterable (`lib.util.iterable` treats strings as non-iterable), `weights='mass'` propagates to all groupselections and is converted to backbone-atom masses per group. CONSEQUENCE: executed endpoint D mass-weights the CORE/LID/NMP domain RMSDs (backbone atom masses, which differ between N/CA/C/O). The notebook narrative ("these remain unweighted below") contradicts this — a 2.4.0-dev0-era narrative-vs-execution conflict. The graded reference is the executed 2.11.0 behavior; the public brief defines analysis D with mass-weighted domains. VALIDATION QUESTION: confirm solver-eligible MDAnalysis versions apply the same propagation.
2. **Group-selection computation** (`_single_frame`): fit on `select` (QCP, `CalcRMSDRotationalMatrix`), rotation applied to all trajectory coordinates as `x' = (x - com)·R + ref_com`, then `rmsd(refpos, mobile_positions, center=False, superposition=False)` per group with `refpos` = raw (uncentered) frame-0 reference positions of the group. No per-domain refit. From-scratch implementations must reproduce this convention, not center the domain groups independently.
3. **Weight normalization**: `w_i = w'_i / mean(w')` (rms.py:273-274, 708-711, 715-721). This differs from a naive `sqrt(Σw d²/Σw)` by a constant factor when mean ≠ 1; reference values obey mean-normalized weighting.
4. **Reference frame handling**: reference positions captured at `ref_frame=0` (explicit for B/C; signature default for D/E). Reference coordinates restored via `trajectory[current_frame]` after capture. Per-frame trajectory time comes from the reader (`ts.time`), i.e. dt from the DCD header.
5. **Scalar endpoint A**: `rms.rmsd(a, b, center=True, superposition=True)` centers both sets at the (unweighted) center of geometry (rms.py:263-268), then QCP (rms.py:276-277). Both universes freshly loaded (u at frame 0). The CRD reference is read with the SAME PSF topology, so the backbone selection order matches atom-for-atom between the universes.
6. **Units**: module docstring declares results `[frame, time (ps), RMSD (Å)]`; the notebook column header "Time (ns)" is a false unit label. Public schema uses `time_ps` with ps values unchanged; reversible relabeling documented here.
7. **Backbone selection membership** (core/selection.py:1309-1338, re-read and PSF-verified in this session): `BackboneSelection` = atoms named exactly N, CA, C, O within recognized protein residues; docstring explicitly "excludes OT* on C-termini". The supplied adk.psf GLY 214 terminates in OT1/OT2 (atoms 3340/3341) and has no atom named O, so the public N/CA/C/O-by-name definition is exactly the reference population. Note that residue-name-level recognition ("protein residues") is part of the selection; the topology's residues are all standard amino acids.

## Correction to previous handoff — dependency-answer exposure (verified this session)

- RETRACTED: the earlier claim that the `MDAnalysisTests/analysis/test_align.py` constant 6.820321761927005 is "a different computation from any endpoint." It is the unweighted, geometry-centered, QCP-optimal-superposition first-vs-last-frame backbone RMSD on the same PSF/DCD (test_align.py:236-266) — exactly the quantity recovered endpoint B computes at its final trajectory frame (unweighted backbone fit vs frame 0). The frame-LAST value of recovered `backbone_domain_rmsd.csv`'s backbone column coincides with this hard-coded constant. This file is therefore **answer-bearing** and must be treated like the already-validated exclusion of `MDAnalysisTests/analysis/test_rms.py`.
- Construction must ensure MDAnalysisTests is absent from solver/verifier environments: the only required inputs are the three staged data files (adk.psf, adk_dims.dcd, adk_open.crd), so MDAnalysisTests need not ship. If it cannot be avoided, a fresh verified exclusion with a removal receipt must be performed before endpoint values are recorded or shipped; the exhausted "no reference-test allowance remains" status is NOT evidence of non-exposure and must not be carried forward.
- Already validated exclusion (byte-identical outputs after removal, both reference tests): `MDAnalysisTests/analysis/test_rms.py` (hardcoded expected RMSD constants for these exact inputs, e.g. 4.68953 = mass-weighted CA at frame 49 = exported `C-alphas` value at frame 49; 4.6997 = backbone select at frame 49; also 4.74920, 4.7857, 1.9154, 2.7139).
- Remaining unfixed fixtures, reported honestly and NOT established as non-answer-bearing: `test_align.py` (see above — answer-bearing for endpoint B's final frame), `legacy_DCD_adk_coords.npy` / `legacy_DCD_NAMD_coords.npy` / `legacy_DCD_c36_coords.npy` (raw trajectory-coordinate fixtures for other frame/atom subsets, not RMSD tables).

## Input derivation (construction must materialize)

- Stage three files as task inputs, byte-identical to MDAnalysisTests 2.11.0 packaged data (observed paths `MDAnalysisTests/data/adk.psf`, `MDAnalysisTests/data/adk_dims.dcd`, `MDAnalysisTests/data/adk_open.crd`), pinned by SHA-256 (adk.psf sha256 96cec916c4b5b19a7acb91bd1e672fb9c8b032aee1e7f0868a50655902c9b5b8; DCD/CRD to be pinned from the installed artifacts at staging time). Do not ship MDAnalysisTests to the solver.
- Software (MDAnalysis) is not an input; the task supplies only the three molecular data files.

## Representation / identity constraints

- Row order = trajectory frame order; the series is a time series, position encodes frame correspondence. No reordering, deduplication or sorting.
- Column mapping for grading: public `frame,time_ps,backbone|ca|core|lid|nmp...` columns map positionally onto the reference CSV columns (`Frame`, `Time (ns)`, `Backbone`/`CORE`/`LID`/`NMP` etc.). Reference column names must not be treated as unit statements (see fact 6).
- Expected row counts derive from the input trajectory length (98 in the recorded runs); the count is an input property, not part of the answer.
- No missing values expected in any column; all frames included.

## Unresolved questions and validation duties

1. Recovered endpoints A and B: construction must rerun and record; validation must then confirm numeric agreement and independent provenance (out-of-scope for this session; no values claimed).
2. Mass-to-groupselections propagation across MDAnalysis versions eligible to solvers (see fact 1) — an executable check, not yet performed.
3. Tolerance calibration: RMSD values are float64 QCP outputs over float32 coordinates; expect reproducibility to ~1e-6 or better across MDAnalysis builds, but this is unmeasured — calibrate in the executable stage, including the near-zero frame-0 values and the time column (~1e-6 relative).
4. The DCDReader DeprecationWarning (ts copying) is a pre-existing source characteristic, not a defect; a behavior change is announced for MDAnalysis 3.0 — pin/verify version if environments drift.
5. `time_ps` fallback route: grader must accept both reader-reported and (frame+1)·1.0 reconstructed values within tolerance.
6. Residual fixtures if MDAnalysisTests cannot be excluded from environments (test_align.py answer-bearing for endpoint B's final frame; legacy DCD npy fixtures) — re-audit at construction with fresh receipts.
