# RMSD analysis of the adenylate kinase closed→open transition

## Background and objective

You are given an atomistic molecular-dynamics trajectory of adenylate kinase (AdK) sampling the transition from a closed (PDB 1AKE) to an open (PDB 4AKE) conformation, a matching molecular topology, and an open-state reference coordinate file. AdK has three domains whose backbone positions move differently around a comparatively stable CORE:

- **CORE**: residues 1–29, 60–121, 160–214
- **LID**: residues 122–159
- **NMP**: residues 30–59

All domain selections below are applied to **backbone atoms**. Here "backbone atoms" means the N, CA, C and O atoms of the protein residues (the standard protein backbone selection); "alpha-carbon" means the atom named CA in each residue; residue identifiers (resid) are the topology's residue numbering, 1–214.

Compute the following root-mean-square-deviation (RMSD) results, in **Ångström**, over the full trajectory (frame indices 0–97; frame 0 is the closed-state starting structure):

$$\mathrm{RMSD}(\mathbf{x},\mathbf{x}^{ref})=\sqrt{\frac{\sum_i w_i\,|\mathbf{x}_i-\mathbf{x}^{ref}_i|^2}{\sum_i w_i}}$$

with $w_i=1$ where no weighting is stated. "Optimal rigid-body superposition" means the translation and rotation minimizing the (weighted) RMSD of the stated fitting group; the translation places the fitting group's (weighted) centroid onto the reference's, followed by the optimal rotation. Where mass weighting is used, atomic masses are those given in the topology.

## Inputs (read-only)

- `inputs/mdanalysis-rmsd/adk.psf` — topology (PSF format; 3341 atoms) for both the trajectory and the open-state structure.
- `inputs/mdanalysis-rmsd/adk_dims.dcd` — trajectory sampling the closed→open transition (98 frames).
- `inputs/mdanalysis-rmsd/adk_open.crd` — open-state AdK coordinates (PDB 4AKE mapped onto this topology).

The trajectory and the open-state structure share the same topology, so selections produce atom sets in identical order.

## Required analyses

**A. Open-vs-closed backbone RMSD (single value).** Take the backbone atoms of trajectory frame 0 (closed state) and of the open-state coordinates. Center both coordinate sets at their centers of geometry, apply optimal rigid-body superposition (unweighted), and report the resulting backbone RMSD.

**B. Backbone-referenced trajectory RMSDs.** Use trajectory frame 0 as the reference. For each trajectory frame, superimpose the frame onto the reference using **all backbone atoms** (fitting group), minimizing the (unweighted) backbone RMSD. Report, per frame:

1. the RMSD of the backbone fitting group itself;
2. the RMSD of each domain selection (CORE, LID, NMP), computed **after that single backbone superposition only** — no per-domain re-alignment and no per-domain re-centering; the domain coordinates are simply the correspondingly transformed trajectory positions compared against the domain's reference (frame-0) positions.

**C. Alpha-carbon CORE RMSD.** Restrict the analysis to the protein's alpha-carbon atoms. Superimpose each frame onto frame 0 using **only the alpha-carbons of the CORE domain** as the fitting group, and report the (unweighted) RMSD of that group.

**D. Mass-weighted branch.** Fitting group = **all protein alpha-carbons** (residues 1–214), with **mass weighting**. For each frame, superimpose onto frame 0 minimizing this weighted alpha-carbon RMSD. Report, per frame:

1. the mass-weighted alpha-carbon RMSD of the fitting group;
2. the mass-weighted RMSD of each domain selection (CORE, LID, NMP — backbone atoms weighted by atomic mass), computed after the same single superposition, with no per-domain re-alignment or re-centering.

**E. Residue-number-weighted branch.** Same fitting group and procedure as D, but the weight of every atom is its **residue number** (resid): the fitting-group alpha-carbon RMSD is resid-weighted, and each domain's RMSD is computed on its backbone atoms, each weighted by its residue number, after the same single superposition (no per-domain re-alignment or re-centering). This is an unconventional weighting used here to demonstrate custom-weight RMSD; it is part of the requested result.

In all trajectory analyses (B–E) the reference is trajectory frame 0, and every frame of the trajectory (0–97) is analyzed.

## Output files (CSV)

Write these files to the output directory. One row per trajectory frame (`Frame` = integer frame index 0…97), one row set per file. RMSD values in Å. Only the columns listed below are compared; any additional columns (such as a trajectory-derived time column) are ignored.

1. `backbone_rmsd.csv` — columns: `Frame`, `Backbone`, `CORE`, `LID`, `NMP` (analysis B).
2. `ca_core_rmsd.csv` — columns: `Frame`, `CORE` (analysis C).
3. `mass_weighted_rmsd.csv` — columns: `Frame`, `C-alphas`, `CORE`, `LID`, `NMP` (analysis D).
4. `resid_weighted_rmsd.csv` — columns: `Frame`, `C-alphas`, `CORE`, `LID`, `NMP` (analysis E).
5. `open_closed_backbone_rmsd.csv` — a single row with column `Backbone` (analysis A).

All values are finite; no missing values are expected. Rows are identified by `Frame`, and the frame keys must be identical across files 1–4.

## Environment and constraints

Any software may be used (an offline environment containing MDAnalysis 2.11.0 is available for convenience; its use is not required). Execution is offline. Limits: ≤4 CPU, ≤8 GiB RAM, ≤10 GiB disk, 600 s runtime.

## Acceptance rules

# Acceptance-rule addendum

This addendum defines exactly how submitted outputs are compared. It does not change the scientific question in the task statement.

## What is graded, and where

The grader reads only the five declared output files, at exactly the declared paths (relative to the submission output root):

1. `backbone_rmsd.csv` — compared columns: `Frame`, `Backbone`, `CORE`, `LID`, `NMP`
2. `ca_core_rmsd.csv` — compared columns: `Frame`, `CORE`
3. `mass_weighted_rmsd.csv` — compared columns: `Frame`, `C-alphas`, `CORE`, `LID`, `NMP`
4. `resid_weighted_rmsd.csv` — compared columns: `Frame`, `C-alphas`, `CORE`, `LID`, `NMP`
5. `open_closed_backbone_rmsd.csv` — compared column: `Backbone`

Files must not be nested in any additional subdirectory (for example an extra `outputs/` layer below the supplied output root); a file at the wrong declared path counts as missing and fails. Only the columns listed above are compared; any additional columns (such as a trajectory-derived time column) are ignored. Each required column name must appear exactly once in the header row; a missing, duplicated or case-mismatched required column fails. Files must be plain comma-separated CSV with exactly one header row; ragged rows fail.

## Row grain, alignment and identifiers

- Files 1–4 hold one row per trajectory frame. Rows are identified and matched by the `Frame` column, which must contain integer frame indices. Duplicate `Frame` keys, missing `Frame` keys, or extra `Frame` keys fail. The set of `Frame` keys must be identical across files 1–4 and must equal the reference file's frame key set (the task's full set of frames 0–97, all 98 frames, every frame analyzed). Physical row order is not compared; rows are joined by `Frame` before any value comparison.
- File 5 must contain exactly one data row; its `Backbone` value is compared directly.
- Every cell in the compared columns must parse as a finite number. Empty cells, NaN, +Inf, −Inf or non-numeric text fail the affected check. Zero is a meaningful value and must be preserved; it is never treated as missing.
- Each scientific check compares one analysis branch (A–E) against its corresponding reference file, cell by cell, at matched `Frame` and column identities. A duplicated, dropped, reordered-by-meaning or truncated frame set is not masked by the numeric tolerance; the multiplicity and coverage of frames is part of the contract.

## Numeric comparison rule

All compared RMSD values are in Ångström. For a submitted value `v` and the corresponding reference value `v_ref` (same file, same `Frame` row, same column), the cell passes if and only if

    |v − v_ref| ≤ 5×10⁻⁶ Å + 10⁻⁶ · |v_ref|

The deviation is measured from the reference value, and the relative term uses the magnitude of the reference value as its denominator. The same rule applies to the single value in file 5. A submission passes only if every compared cell in every file passes and all structural rules above hold.

Boundary and justification: the compared quantities are ordinary float64 RMSD values serialized as decimal text. The absolute term (5×10⁻⁶ Å) is the floor of the rule: it covers the near-zero frame-0 self-comparison values (order 10⁻⁷–10⁻⁸ Å, where all correct methods return noise-level values numerically indistinguishable from zero) and the small residual differences between independent optimal-rigid-body-superposition implementations of the publicly stated weighted Kabsch/QCP procedure, which an executed independent NumPy implementation measured to agree with the reference pipeline well inside this floor. The relative term (10⁻⁶ of the reference magnitude, up to ≈1.4×10⁻⁵ Å for the largest RMSDs ≈14 Å) bounds the accepted observable serialization/algebra deviation; it is set so that the accepted output difference remains orders of magnitude below any physically meaningful RMSD difference. The tolerance is a limit on observable submission-vs-reference output differences, not a guarantee that every conceivable wrong method is detected — but any output differing from the reference beyond this boundary, for example from per-domain re-alignment, a different fitting group, wrong weights (mass vs resid), wrong domain intervals or dropped frames, fails.

Because the relative term is 10⁻⁶, output written with fewer than about 7 significant digits (e.g. fixed 4-decimal rounding) may exceed the boundary and fail; write values with enough precision to preserve the computed result (standard full-precision float formatting is sufficient). Values are compared after parsing; formatting/round-trip differences are not separately normalized.

## Checks

One structural check covers the five files (existence, column names, frame grain, uniqueness, cross-file frame-key identity, single-row endpoint, finite parseable values). Five scientific checks each compare one analysis branch against its reference file joined on `Frame`: analysis A (`open_closed_backbone_rmsd.csv`, `Backbone`), analysis B (`backbone_rmsd.csv`, `Backbone`/`CORE`/`LID`/`NMP`), analysis C (`ca_core_rmsd.csv`, `CORE`), analysis D (`mass_weighted_rmsd.csv`, `C-alphas`/`CORE`/`LID`/`NMP`) and analysis E (`resid_weighted_rmsd.csv`, `C-alphas`/`CORE`/`LID`/`NMP`). Missing or malformed files fail the corresponding checks rather than being skipped. Acceptance requires all checks to pass; no partial credit is given. The grader never executes submission code.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
