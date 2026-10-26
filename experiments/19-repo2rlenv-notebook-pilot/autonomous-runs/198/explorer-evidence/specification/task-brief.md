# RMSD analysis of the adenylate kinase open⇄closed transition

Adenylate kinase (AdK) transitions from a closed to an open conformation, with the LID and NMP domains moving around a stable CORE. You are given a topology, a trajectory of this transition, and an open-conformation coordinate set. Compute the RMSD quantities below and write the five output tables.

## Supplied inputs

- `inputs/adk.psf` — AdK topology (CHARMM PSF; atom names, residues, masses)
- `inputs/adk_dims.dcd` — MD trajectory of the closed→open transition (CHARMM-flavor DCD; coordinates in Å)
- `inputs/adk_open.crd` — coordinates of the open conformation, paired with the same PSF topology

Software choice is open. A Python environment with MDAnalysis 2.9.0 is available for convenience, but any implementation matching the definitions below is acceptable. All selections below are given in MDAnalysis selection language; these strings define the atom populations.

## Populations and conventions

Domain definitions (backbone atoms of residue ranges, `resid` as in the topology):

- CORE = `backbone and (resid 1-29 or resid 60-121 or resid 160-214)`
- LID = `backbone and resid 122-159`
- NMP = `backbone and resid 30-59`

Selection tokens used: `backbone` (protein backbone atoms), `name CA` (alpha-carbons of the whole universe), `protein and name CA` (alpha-carbons of the protein).

Conventions common to the trajectory analyses:

- Rows are ordered by trajectory frame (0-based `Frame` index); row position encodes the frame, so output row *i* corresponds to trajectory frame *i*, one row per frame.
- `Time (ps)` is the frame time in picoseconds as reported by the trajectory reader for that frame.
- RMSD is measured in ångström after optimal rigid-body superposition (translation and rotation minimizing the weighted RMSD; the standard quaternion/QCP formulation). Where weights are used, each atom is weighted by the stated quantity; a constant rescaling of the weights does not change the RMSD.
- The reference for every trajectory table below is trajectory frame 0.
- Group RMSDs (CORE/LID/NMP columns) are computed *after* the frame has been superimposed on the reference using the `select` group, with no further fitting applied to the groups.

## Required outputs

Write comma-separated files with a header row, no index column, and at least 12 significant digits for non-integer values. Missing values are not expected.

1. **`open_closed_backbone_rmsd.csv`** — header `backbone_rmsd_angstrom`; one data row. The RMSD between the backbone atoms of the trajectory's first (closed) frame and the open-conformation structure from `adk_open.crd`, computing the deviation after centering both coordinate sets on their centers of geometry and optimal superposition.

2. **`backbone_rmsd.csv`** — headers `Frame, Time (ps), Backbone, CORE, LID, NMP`. Per trajectory frame: the frame is translated and rotated to optimally superimpose its `backbone` atoms (unweighted) onto those of frame 0. `Backbone` = unweighted RMSD of all backbone atoms under this superposition; `CORE`, `LID`, `NMP` = unweighted RMSD of each domain's backbone atoms after applying this same superposition, with no further fitting.

3. **`core_ca_rmsd.csv`** — headers `Frame, Time (ps), CORE`. Per trajectory frame: RMSD versus frame 0 over only the alpha-carbons of the CORE domain (i.e. the selection CORE applied within the `name CA` atom group). The superposition for each frame is determined by this same set of CORE alpha-carbons.

4. **`mass_weighted_rmsd.csv`** — headers `Frame, Time (ps), C-alphas, CORE, LID, NMP`. Per trajectory frame: the frame is superimposed on frame 0 using the `protein and name CA` atoms with atomic-mass weights. `C-alphas` = mass-weighted RMSD of the protein alpha-carbons under this superposition; `CORE`, `LID`, `NMP` = mass-weighted RMSD of each domain's backbone atoms after applying this superposition, with no further fitting. Mass weights apply to every group in this table.

5. **`resid_weighted_rmsd.csv`** — headers `Frame, Time (ps), C-alphas, CORE, LID, NMP`. Same structure as output 4, but each atom is weighted by its residue id instead of its mass: the protein alpha-carbons are weighted by their resids for the superposition and the `C-alphas` column, and each domain's backbone atoms are weighted by their resids for the domain columns.

## Resources

No network access. Budget: 4 CPUs, 8 GiB RAM, 10 GiB disk, and the analysis should complete within 600 seconds (the reference computation takes a few seconds).
