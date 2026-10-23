## Input materialization and comparison proposal (private, provisional)

### Measured facts
- Execution succeeded (exit 0, ~2.9 s), 3 declared CSV artifacts present with pinned hashes; 2 subsequent replays byte-identical (finite-sample observation only, not a correctness proof).
- Structural audit: 98 data rows per file, frames 0–97, all numeric columns finite and distinct; Frame columns identical across files; Time (ns) columns identical across files.
- MDAnalysis 2.11.0 sdist inspected (read-only): groupselection weighting propagation, transform pipeline, ref_frame default, weight normalization as described in the review.

### Required construction work (not yet done, values not yet observed)
1. **Recover endpoint B** by rerunning the unchanged original branch — `rms.RMSD(u, u, select='backbone', groupselections=[CORE, LID, NMP], ref_frame=0)` from a freshly loaded universe — as the reference for `backbone_rmsd.csv`, with separate provenance. Alternatively `R.results.rmsd` columns Frame/Backbone/CORE/LID/NMP.
2. **Recover endpoint A** by rerunning the unchanged standalone call `rms.rmsd(u.select_atoms('backbone').positions, ref.select_atoms('backbone').positions, center=True, superposition=True)` with `u` positioned at frame 0 before reading positions (original call precedes any trajectory iteration). Store with separate provenance.
3. Independently validate recovered values (e.g., independent Kabsch implementation) before finalizing the contract; both recovered endpoints are currently unobserved.
4. Input redistribution clearance for adk.psf / adk_dims.dcd / adk_open.crd (LGPL-2.1 MDAnalysisTests data) before solver distribution.

### Proposed comparison rules (to validate, not yet calibrated)
- **Identity**: rows matched by `Frame` key (exact set 0–97, uniqueness, multiplicity 1); columns matched by name; cross-file Frame-key equality for the four trajectory tables. Units Å.
- **Projection**: only `Frame` + RMSD columns compared; `Time (ns)` dropped (DCD-reader-guessed metadata, frame-1-indexed; label unverified). Documented as projection, original recorded artifacts preserved.
- **Same-quantity tolerance**: propose an absolute-plus-relative element for per-frame RMSD, calibrated by measuring (i) rerun-to-rerun spread, (ii) independent-implementation deviations (Kabsch vs QCP; float32 vs float64 coordinate pipelines — the reference internally casts to float64 and the in-file notes warn float32 gives errors up to ~1e-3 Å), (iii) unacceptable-output separations. Do not fix numeric tolerances before these measurements.
- **Near-zero behavior**: frame 0 self-comparison values are ~1e-7–1e-8 Å in the reference (floating-point residue, not exact zero). Validation must measure how an exact-zero frame-0 submission should be treated and calibrate an absolute floor accordingly. Include boundary rows in the probe set.
- **Incorrect outputs the validation must distinguish** (scientific differences, not tolerance cases): per-domain independent re-superposition (changes CORE/LID/NMP columns materially); omitting the reference-centroid translation; backbone vs alpha-carbon fitting groups; unweighted domain columns in the mass branch (narrative suggests this but executed code mass-weights groups — see review; the contract states the executed method); wrong resid ranges (LID 122–159 vs off-by-one); wrong reference (open CRD instead of frame 0).
- **Replay caveats observed**: byte-identical replays show serialization stability only. Row order is scientifically meaningful (frame sequence) and must be enforced via the Frame key, not hash equality.

### Unresolved choices to settle during validation
- Whether to also grade a solver-supplied time column against the DCD-header-derived values (currently excluded).
- Exact CSV column-order strictness (proposed: name-matched, order-agnostic).
- Tolerance values and the frame-0 numeric floor.

### Resource policy
Limits per task_policy: 4 CPU, 8 GiB RAM, 10 GiB disk, offline, 600 s solver and reference timeouts, 120 s verifier timeout; binary reward on all required checks.
