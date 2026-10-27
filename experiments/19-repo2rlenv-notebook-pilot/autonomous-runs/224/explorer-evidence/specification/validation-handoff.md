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

## Measured facts (from execution/inspection)

- Executed environment: Python 3.13.13, MDAnalysis 2.11.0, MDAnalysisTests 2.11.0, pandas 3.1.0, numpy 2.5.4 (trial/environment.txt; full lock retained). Exit 0, ~3.8 s.
- Reference CSVs: 98 data rows, 0-based frames 0-97 (this is an input property of adk_dims.dcd, not an answer; do paste into public brief — I did not).
- `time_ps` observed column: min 0.9999999119200186, max 97.99999136816182, i.e. t ≈ (frame+1)·dt with dt ≈ 0.9999999119200186 ps (DCD header float32 parsing by MDAnalysis DCDReader). Comparator must use a tolerance for this column (relative ~1e-6 covers the dt-vs-1.0 discrepancy and any (frame+1)·1.0 reconstruction).
- Frame-0 self-reference RMSDs are near 1e-7/1e-8 (not exactly 0) due to float32 coordinates and float64 centering; tolerance must accommodate.
- Same Frame/Time columns appear in all three exported reference CSVs; RMSD values in Å.

## Consequential method facts, verified in pinned mdanalysis-2.11.0 source (MDAnalysis/analysis/rms.py; can be re-cited via package_inspection for mdanalysis 2.11.0)

1. **Mass propagation to group selections** (lines 691-711 of `_prepare`): `if not self.weights_groupselections: if not iterable(self.weights): self.weights_groupselections = [self.weights] * len(self.groupselections)`; note `lib.util.iterable` treats strings as non-iterable. Lines 706-707 convert `'mass'` to `atoms['mobile'].masses`. CONSEQUENCE: the executed endpoint D mass-weights the CORE/LID/NMP domain RMSDs (backbone atom masses, which differ between N/CA/C/O). The notebook narrative flatly contradicts this ("these remain unweighted below") — a narrative-vs-execution conflict from the 2.4.0-dev0 era. The graded reference is the executed 2.11.0 behavior; the public brief therefore defines analysis D with mass-weighted domains. VALIDATION QUESTION: confirm that solver-eligible MDAnalysis versions apply the same propagation (check CHANGELOG entries around weights handling, or execute a probe on an alternative version).
2. **Group-selection computation** (`_single_frame`, lines 782-824): fit on `select` (QCP, `CalcRMSDRotationalMatrix`), rotation applied to all trajectory coordinates as `x' = (x - com)·R + ref_com`, then `rmsd(refpos, mobile_positions, center=False, superposition=False)` per group with `refpos` = raw (uncentered) frame-0 reference positions of the group. No per-domain refit. From-scratch implementations must reproduce this convention, not center the domain groups independently.
3. **Weight normalization**: `w_i = w'_i / mean(w')` (lines 270-274, 708-711, 715-721). This differs from a naive `sqrt(Σw d²/Σw)` by a constant factor when mean ≠ 1 — validation should confirm which convention reference values obey (they obey mean-normalized; the notebook's background formula is Σw d²/Σw).
4. **Reference frame handling** (lines 723-744): reference positions captured at `ref_frame=0` (explicit for B/C; default for D/E — confirmed `ref_frame=0` default in signature line 393). Reference coordinates restored via `trajectory[current_frame]` after capture.
5. **Scalar endpoint A**: `rms.rmsd(a, b, center=True, superposition=True)` centers both sets at center of geometry (unweighted), then QCP; both universes freshly loaded (u at frame 0). NOTE: `superposition` implies centering per docstring line 202-207.
6. **Units**: RMSD module docstring declares results `[[frame, time (ps), RMSD (A)]]` (line 131) — the notebook column header "Time (ns)" is a false unit label; the public schema uses `time_ps` and this mapping (ps values unchanged) is documented in the review.

## Input derivation (construction must materialize)

- Stage three files as task inputs, byte-identical to MDAnalysisTests 2.11.0 packaged data (observed paths `MDAnalysisTests/data/adk.psf`, `MDAnalysisTests/data/adk_dims.dcd`, `MDAnalysisTests/data/adk_open.crd`), pinned by SHA-256 against the retained lock. Do not ship MDAnalysisTests itself to the solver if avoidable; the three data files suffice (PSF+DCD for trajectory universe, PSF+CRD for reference universe).
- `reference_open.crd` is loaded with the SAME PSF topology, so `backbone` selection order matches atom-for-atom between the two universes.
- Already-applied dependency exclusion (validated, byte-identical outputs after removal): `MDAnalysisTests/analysis/test_rms.py` — contains hardcoded expected RMSD constants for these exact inputs (e.g. 4.68953 = mass-weighted CA at frame 49; 4.6997 = backbone select at frame 49; also 4.74920, 4.7857, 1.9154, 2.7139, 6.820321761927005). If MDAnalysisTests is present in any solver/verifier image, these fixtures must be removed again.
- Residual fixture overlaps previously reported and NOT established as answer-bearing: `MDAnalysisTests/analysis/test_align.py` constant 6.820321761927005 (first-vs-last-frame backbone superposition — a different computation from any endpoint), `legacy_DCD_adk_coords.npy` / `legacy_DCD_NAMD_coords.npy` (raw coordinate fixtures, different frame/atom subsets). No reference-test allowance remains to remove them; construction should re-audit if MDAnalysisTests ships.

## Representation / identity constraints

- Row order = trajectory frame order; the series is a time series, position encodes frame correspondence. No reordering, deduplication or sorting.
- Column-to-reference mapping for grading: public `frame,time_ps,backbone|ca|core|lid|nmp...` columns map positionally onto the reference CSV columns `Frame, Time (ns), Backbone/CORE/LID/NMP` etc. Column names in reference artifacts must not be treated as unit statements (see fact 6).
- Expected row counts derive from the input trajectory length (98 in the recorded runs); the count itself is an input property, not part of the answer.
- No missing values expected in any column; all frames included.

## Unresolved questions and validation duties

1. Recovered endpoints A and B: construction must rerun and record; validation must then confirm byte/numeric agreement and independent provenance (out-of-scope for this session; no values claimed).
2. Mass-to-groupselections propagation across MDAnalysis versions eligible to solvers (see fact 1) — an executable check, not yet performed.
3. Tolerance calibration: RMSD values are float64 QCP outputs over float32 coordinates; expect reproducibility to ~1e-6 or better across MDAnalysis builds, but this is unmeasured — calibrate in the executable stage, including the near-zero frame-0 values and the time column.
4. The DCDReader DeprecationWarning (ts copying) is a pre-existing source characteristic, not a defect; behavior change is announced for MDAnalysis 3.0 — pin/verify version if environments drift.
5. `time_ps` for the (frame+1)-ps fallback route: grader must accept both reader-reported and reconstructed values within tolerance (see measured facts).
