# Task: RMSD analysis of the adenylate kinase open↔closed transition

Adenylate kinase (AdK) has a stable CORE domain flanked by the LID and NMP domains, which move as the enzyme transitions between closed and open conformations. You are supplied with the topology, a trajectory sampling the closed→open transition, and the open-conformation coordinates. Quantify this conformational change by computing the root mean square deviation (RMSD) of atomic positions, in Angstrom, in five analyses below.

## Supplied inputs

- `inputs/adk.psf` — protein topology (PSF) for the AdK structure; 214 residues with atom counts and atom order shared by all supplied coordinate data.
- `inputs/adk_trajectory.dcd` — trajectory (DCD) sampling the closed→open transition.
- `inputs/adk_open.crd` — coordinates (CRD) of the open conformation of the same structure.

(File byte identities are pinned separately at task setup.)

## Definitions

For coordinate arrays **x** (one row per atom, atoms in matching order between compared structures) and reference **x**^(ref):

- **RMSD(x, x^(ref)) = sqrt( (1/n) Σᵢ |xᵢ − xᵢ^(ref)|² )**
- **Weighted RMSD(x, x^(ref)) = sqrt( Σᵢ wᵢ |xᵢ − xᵢ^(ref)|² / Σᵢ wᵢ )** (invariant to any overall positive scaling of the weights).
- **Optimal superposition**: the displacement / rotation pair that minimizes the (weighted) RMSD; rotations are proper (determinant +1). RMSD under optimal superposition is the minimum over such pairs, with coordinates first expressed relative to the appropriate weighted centroid.
- **Backbone atoms**: the main-chain protein atoms (N, CA, C, O).
- **Domains** (residue numbers as in the topology):
  - CORE = backbone atoms of residues 1–29, 60–121, 160–214
  - LID = backbone atoms of residues 122–159
  - NMP = backbone atoms of residues 30–59

## Required analyses

**A. Open vs. closed endpoint conformations.** RMSD between the backbone atoms of the open structure (`adk_open.crd`) and the trajectory's first frame (closed conformation). Subtract the center of geometry of each set, apply optimal superposition, and report the resulting backbone RMSD.

**B–E. Trajectory RMSD versus frame 0.** For each of the analyses below, the reference is frame 0 of the trajectory itself. For each trajectory frame, first superimpose the frame onto frame 0 by the optimal (weighted, where weights are specified) rigid-body transformation determined by the fitting group; then report:

1. the RMSD of the fitting group under that fit; and
2. for each listed domain group, the RMSD between the frame's transformed coordinates and the **untransformed frame-0 coordinates** of that group's atoms, **computed without any further fitting, centering, or re-alignment** of the group (the group RMSD measures residual domain displacement under the single global superposition).

**B. Backbone and domains (unweighted).** Fitting group: all backbone atoms, unweighted. Report four series: backbone (under the fit), CORE, LID, NMP (group RMSDs, unweighted). Group atom sets are the backbone atoms of the full structure given by the domain definitions above.

**C. CORE restricted to alpha-carbons.** Restrict the entire analysis to the alpha-carbon (CA) atoms. Fitting group: the alpha-carbons of the CORE domain. Report the CORE fit RMSD.

**D. Mass-weighted.** Fitting group: all alpha-carbons of the protein, with each atom weighted by its mass (mass-weighted centroids for the superposition). Report the mass-weighted fit RMSD for the alpha-carbons, and mass-weighted group RMSDs for CORE, LID, NMP. Group atom sets are the backbone atoms of the **full structure** (not restricted to alpha-carbons), and the group RMSDs are also mass-weighted (each atom weighted by its mass).

**E. Residue-number-weighted.** Same structure as D, but each atom is weighted by its residue number instead of its mass — in the fitting group (alpha-carbons of the protein) and in the CORE, LID, NMP group RMSDs (backbone atoms, full structure, weighted by residue number).

Note that in D and E the fitting group and the reported group RMSDs use the specified weighting; the groups being compared are the full-structure backbone atom sets, independent of the alpha-carbon restriction on the fitting group.

## Required outputs

Write CSV files (UTF-8, one header row, comma-separated). All RMSD values are in Angstrom and must be finite. Each trajectory table contains exactly one row per trajectory frame, ordered by strictly increasing frame index (the row order is the time series). The frame column is the 0-based trajectory frame index. Do not output a time column.

1. `outputs/rmsd_backbone_open_closed.csv` — analysis A. Columns: `rmsd_backbone_angstrom`. One data row.
2. `outputs/rmsd_backbone_domains.csv` — analysis B. Columns: `frame`, `rmsd_backbone_angstrom`, `rmsd_core_angstrom`, `rmsd_lid_angstrom`, `rmsd_nmp_angstrom`.
3. `outputs/rmsd_ca_core.csv` — analysis C. Columns: `frame`, `rmsd_core_ca_angstrom`.
4. `outputs/rmsd_mass_weighted.csv` — analysis D. Columns: `frame`, `rmsd_ca_mass_angstrom`, `rmsd_core_mass_angstrom`, `rmsd_lid_mass_angstrom`, `rmsd_nmp_mass_angstrom`.
5. `outputs/rmsd_residue_weighted.csv` — analysis E. Columns: `frame`, `rmsd_ca_resid_angstrom`, `rmsd_core_resid_angstrom`, `rmsd_lid_resid_angstrom`, `rmsd_nmp_resid_angstrom`.

The frame identity is shared across outputs 2–5: each must cover exactly the same set of trajectory frames, once each, in the same order. The RMSD at frame 0 is expected to be near zero (floating-point rounding of identical conformations), not exactly zero.

## Environment and limits

CPU-only; no network access; run within 600 seconds and 8 GiB RAM. Software choice is open: any tools may be used as long as the outputs above are produced. For convenience, a compatible offline environment (MDAnalysis 2.11.0, NumPy, pandas) can be supplied; using it is not a requirement. If you use MDAnalysis, note that its `RMSD` class's current semantics for `weights='mass'` (mass applied to group selections as well) match the definitions in D above.
