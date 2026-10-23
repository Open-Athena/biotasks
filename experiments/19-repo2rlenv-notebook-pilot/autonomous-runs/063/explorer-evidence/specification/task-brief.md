# RMSD analysis of the adenylate kinase closed→open transition

## Background and objective

You are given an atomistic molecular-dynamics trajectory of adenylate kinase (AdK) sampling the transition from a closed (PDB 1AKE) to an open (PDB 4AKE) conformation, a matching molecular topology, and an open-state reference coordinate file. AdK has three domains whose backbone positions move differently around a comparatively stable CORE: **CORE** (residues 1–29, 60–121, 160–214), **LID** (residues 122–159) and **NMP** (residues 30–59). All domain selections below are applied to **backbone atoms**.

Compute the following root-mean-square-deviation (RMSD) results, in **Ångström**, over the full trajectory (frame indices 0–97; frame 0 is the closed-state starting structure):

$$\mathrm{RMSD}(\mathbf{x},\mathbf{x}^{ref})=\sqrt{\frac{\sum_i w_i\,|\mathbf{x}_i-\mathbf{x}^{ref}_i|^2}{\sum_i w_i}}$$

with $w_i=1$ where no weighting is stated. "Optimal rigid-body superposition" means the translation and rotation minimizing the (weighted) RMSD of the stated fitting group; the translation places the fitting group's weighted centroid onto the reference's, followed by the optimal rotation.

## Inputs (read-only)

- `inputs/mdanalysis-rmsd/adk.psf` — topology (PSF format; 3341 atoms) for both the trajectory and the open-state structure.
- `inputs/mdanalysis-rmsd/adk_dims.dcd` — trajectory sampling the closed→open transition (98 frames).
- `inputs/mdanalysis-rmsd/adk_open.crd` — open-state AdK coordinates (PDB 4AKE mapped onto this topology).

The trajectory and the open-state structure share the same topology, so selections produce atom sets in identical order.

## Required analyses

**A. Open-vs-closed backbone RMSD (single value).** Take the backbone atoms of trajectory frame 0 (closed state) and of the open-state coordinates. Center both coordinate sets at their centers of geometry, apply optimal rigid-body superposition, and report the resulting backbone RMSD.

**B. Backbone-referenced trajectory RMSDs.** Use trajectory frame 0 as the reference. For each trajectory frame, superimpose the frame onto the reference using **all backbone atoms** (fitting group), minimizing the backbone RMSD. Report, per frame:

1. the RMSD of the backbone fitting group itself;
2. the RMSD of each domain selection (CORE, LID, NMP), computed **after that single backbone superposition only** — no per-domain re-alignment and no per-domain re-centering; the domain coordinates are simply the correspondingly transformed trajectory positions compared against the domain's reference (frame-0) positions.

**C. Alpha-carbon CORE RMSD.** Restrict the analysis to the protein's alpha-carbon atoms. Superimpose each frame onto frame 0 using **only the alpha-carbons of the CORE domain** as the fitting group, and report the RMSD of that group.

**D. Mass-weighted branch.** Fitting group = **all protein alpha-carbons** (residue identifier 1–214), with **mass weighting**. For each frame, superimpose onto frame 0 minimizing this weighted alpha-carbon RMSD. Report, per frame:

1. the mass-weighted alpha-carbon RMSD of the fitting group;
2. the mass-weighted RMSD of each domain selection (CORE, LID, NMP, backbone atoms weighted by atomic mass), computed after the same single superposition, with no per-domain re-alignment or re-centering.

**E. Residue-number-weighted branch.** Same fitting group and procedure as D, but the weight of every atom is its **residue number** (resid): the fitting-group alpha-carbon RMSD is resid-weighted, and each domain's RMSD is computed on its backbone atoms, each weighted by its residue number, after the same single superposition (no per-domain re-alignment or re-centering). This is an unconventional weighting used here to demonstrate custom-weight RMSD; it is part of the requested result.

In all trajectory analyses the reference is trajectory frame 0, and every frame of the trajectory is analyzed.

## Output files (CSV)

One row per trajectory frame (`Frame` = integer frame index 0…97), one row set per file. RMSD values in Å. Only the columns listed below are compared; any additional columns (such as a trajectory-derived time column) are ignored.

1. `backbone_rmsd.csv` — columns: `Frame`, `Backbone`, `CORE`, `LID`, `NMP` (analysis B).
2. `ca_core_rmsd.csv` — columns: `Frame`, `CORE` (analysis C).
3. `mass_weighted_rmsd.csv` — columns: `Frame`, `C-alphas`, `CORE`, `LID`, `NMP` (analysis D).
4. `resid_weighted_rmsd.csv` — columns: `Frame`, `C-alphas`, `CORE`, `LID`, `NMP` (analysis E).
5. `open_closed_backbone_rmsd.csv` — a single row with column `Backbone` (analysis A).

All values are finite; no missing values are expected. Rows are identified by `Frame`, and the frame keys must be identical across files 1–4.

## Environment and constraints

Any software may be used (an offline environment containing MDAnalysis 2.11.0 is available for convenience; its use is not required). Execution is offline. Limits: ≤4 CPU, ≤8 GiB RAM, ≤10 GiB disk, 600 s runtime.
