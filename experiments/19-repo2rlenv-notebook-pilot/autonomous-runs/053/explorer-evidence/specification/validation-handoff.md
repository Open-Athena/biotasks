## Proposed scope (not yet fully validated)

Task covers all five eligible endpoints of the executed analysis, two more than the existing exports: the pairwise open-vs-closed backbone RMSD and the first (backbone-wide, unweighted, with CORE/LID/NMP groups) trajectory table. `inputs/plan.json` excluded these solely because the reference's variable names were overwritten (B) or the expression was unassigned (A); the underlying analyses are fully present in `trial/reference.py` and executed. **Required reference work before solving:** re-run the reference with a minimal restructure that assigns distinct names (or exports immediately) so that A (scalar) and B (5-column table) are captured. No new computation is introduced.

## Measured facts

- Reference executed successfully: exit 0, 3.77 s, peak child RSS ~167 MiB (limits: 600 s, 4 CPU, 8 GiB). Offline environment builds and runs.
- Trajectory has 98 frames; DCD frame time ≈ (frame+1)·dt with dt ≈ 0.9999999119 Å-independent metadata quirk — this is why `Time (ns)` is excluded from graded outputs.
- 214 alpha-carbons (execution log). Outputs in `output-audit.json` are all finite, no ragged rows, one row per frame.
- Two replay runs were byte-identical — determinism of this build only; no portability or correctness claim.

## Methodology verification (pinned source, mdanalysis 2.11.0)

- `MDAnalysis/analysis/rms.py:445-461, 689-711` + `MDAnalysis/lib/util.py:1102-1114` (`iterable('mass') == False`): with `weights='mass'` and default `weights_groupselections=False`, group selections are **mass-weighted**. The notebook narrative ("these remain unweighted") is stale relative to the executed 2.11.0 reference. Public brief pins mass-weighted groups for analysis D.
- `rms.py:770-824`: single global fit of `select`; group RMSDs computed with `center=False, superposition=False` against raw frame-0 group coordinates (`rms.py:733-741`); reported `select` value is the minimal weighted RMSD under the fit (QCP).
- `rms.py:432-440, 618-626`: group selections applied to `atomgroup.universe.select_atoms(...)` — full universe, regardless of any AtomGroup restriction on `select`. Traps in D/E.
- `rms.py:390-393`: defaults `weights=None`, `ref_frame=0` (B/C pass `ref_frame=0` explicitly; D/E rely on the default). Weight normalization `w/<w'>` (rms.py:703-721) is scale-invariant given the Σw denominator, so the public formula is equivalent.

## Input materialization (proposed, pending)

- Stage the AdK data files from the `MDAnalysisTests` 2.11.0 distribution (datafiles `PSF`, `DCD`, `CRD`) as `inputs/adk.psf`, `inputs/adk_trajectory.dcd`, `inputs/adk_open.crd`; record sha256 identities. **Redistribution review is not yet established** (provenance.json: "keep biological inputs ... private until checked separately") — publish only after that passes. Solver receives only the three input files and the brief.

## Comparison rules (proposed, uncalibrated — no numeric tolerances asserted)

- **Structural**: each of outputs 2–5 has one row per trajectory frame (98 expected), `frame` strictly increasing, no duplicates; same frame set across the four tables under one shared identity mapping. Output 1 = 1 row × 1 value column.
- **Numerical**: per-cell RMSD comparison in Å between solver and reference, using `max(absolute_component, relative_component)` form because frame-0 values are near zero (~1e-7 measured in the audit). **Tolerance values must be calibrated by measurement**, not assumed: (a) acceptable spread — independent reimplementation of Kabsch/QCP superposition in float64, and re-runs on this stack; (b) unacceptable deviations that must fail — any of: unweighted groups in D (the stale-narrative reading); per-group re-fitting or re-centering in B/D/E; alpha-carbon-restricted group sets in D/E; wrong reference frame; LID/NMP columns swapped; domain residue ranges mis-tiled; missing final-frame rows. Do not adopt a tolerance that admits the unacceptable set.
- **Representation**: row order is the time series — require ordered comparison keyed by `frame`; explicitly include a row-permutation probe that must FAIL. Column names per the brief; numeric formatting free.
- Cross-file: no cross-table numeric identity is expected except that all tables describe the same frames (identity check only). Note analysis C (CA-only, unweighted) and the CORE column of D (backbone, mass-weighted) are intentionally different quantities.

## Open items before finalization

1. Reference re-run capturing outputs A and B (trivial restructure) and verification that A/B values match the quantities the notebook displays.
2. Input redistribution clearance and file pinning.
3. Executable tolerance calibration as above; only then fix grader thresholds.
4. Solver environment staged offline (pyproject already resolved once; retained uv.lock hash 2f019f7… available).
5. Confirm no solver-visible answer leakage in the staged inputs (inputs contain no reference-derived content under this design).
