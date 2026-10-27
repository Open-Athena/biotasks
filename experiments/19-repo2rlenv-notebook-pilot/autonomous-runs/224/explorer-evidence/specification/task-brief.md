# Quantifying adenylate kinase's open-to-closed transition with RMSD

## Scientific question

Adenylate kinase (AdK) transitions between a closed and an open conformation; its LID and NMP domains move around a comparatively stable CORE domain. Using the supplied topology, a trajectory that samples the closed-to-open transition, and a separate open-conformer coordinate set, quantify this motion with root-mean-square deviations (RMSD, in Å) of atomic positions under several selection and weighting schemes.

AdK's domains, restricted to **backbone atoms**, are defined by residue identifier:

- CORE: `resid 1-29` or `resid 60-121` or `resid 160-214`
- LID: `resid 122-159`
- NMP: `resid 30-59`

Here "backbone" has the standard protein backbone meaning (N, CA, C, O, plus terminal OXT where present), as implemented in the MDAnalysis selection language.

## Supplied inputs

- `inputs/structure.psf` — CHARMM PSF topology for AdK (defines atoms, masses, residue numbers, bonds; also the selection universe for both coordinate sets).
- `inputs/trajectory.dcd` — DCD trajectory sampling the closed-to-open transition. **Frame index 0** (a closed conformer) is the reference structure for all trajectory-based RMSD analyses below.
- `inputs/reference_open.crd` — CHARMM coordinate file of the open conformer, read together with the same PSF topology.

The inputs are byte-identical copies of the MDAnalysis 2.11.0 packaged test data for this system (adk.psf / adk_dims.dcd / adk_open.crd); their identities will be pinned in the task bundle.

## Method

For every RMSD below, coordinates are optimally superimposed (translation + rotation minimizing the weighted RMSD; the QCP algorithm as implemented in MDAnalysis's `analysis.rms`) before or as part of the deviation calculation, unless stated otherwise. A weighted RMSD over N atoms with weights w_i uses w_i normalized by the mean of the weights: w_i = w'_i / mean(w'). All RMSD values are in Å.

### A. Single open-vs-closed backbone RMSD

Compute the unweighted RMSD between the backbone atoms of the trajectory's frame 0 (closed conformer) and the backbone atoms of the open reference structure (`inputs/reference_open.crd`), after centering each coordinate set at its center of geometry and optimally superimposing them. Report one value.

### B. Backbone and per-domain RMSD vs. frame 0

Over every frame of the trajectory, superimpose the full protein **backbone** onto the frame-0 backbone conformation (unweighted best fit). Record:

1. the unweighted backbone RMSD of that fit;
2. then, **without any further alignment**, the unweighted RMSD of the CORE, LID and NMP backbone groups (each computed on the coordinates after the backbone fit has been applied to all atoms, against the corresponding frame-0 reference coordinates).

One row per frame.

### C. Alpha-carbon CORE RMSD vs. frame 0

Restricting the analysis universe to the alpha-carbon (CA) atoms of the protein, superimpose on, and report the unweighted RMSD of, the CORE-domain CA atoms versus their frame-0 positions. One row per frame.

### D. Mass-weighted RMSD

Over every frame, superimpose and report the RMSD of the **protein CA atoms weighted by atomic mass** (mass-weighted fit and mass-weighted RMSD). Then, without further alignment, report the RMSD of the CORE, LID and NMP backbone groups against their frame-0 coordinates with **each atom weighted by its atomic mass** (domains mass-weighted as well, per the default propagation of `weights='mass'` to group selections when no separate group weights are given). One row per frame.

### E. Residue-number-weighted RMSD (custom-weighting variant)

Over every frame, superimpose and report the RMSD of the protein CA atoms with each CA **weighted by its residue number**. Then, without further alignment, report the RMSD of the CORE, LID and NMP backbone groups with each atom **weighted by its residue number**. One row per frame. (This weighting is a demonstration of custom weights, not a conventional physical metric; it is requested as a defined comparison of weighting schemes.)

## Required outputs

Write the following files (UTF-8, comma-separated, header row exactly as given, one data row per trajectory frame **in trajectory frame order**, no index column; RMSD in Å; `time_ps` as described below):

1. `outputs/backbone_domain_rmsd.csv` (analysis B):
   `frame,time_ps,backbone_rmsd_angstrom,core_rmsd_angstrom,lid_rmsd_angstrom,nmp_rmsd_angstrom`
2. `outputs/ca_core_rmsd.csv` (analysis C):
   `frame,time_ps,ca_core_rmsd_angstrom`
3. `outputs/mass_weighted_rmsd.csv` (analysis D):
   `frame,time_ps,ca_mass_weighted_rmsd_angstrom,core_rmsd_angstrom,lid_rmsd_angstrom,nmp_rmsd_angstrom`
4. `outputs/resid_weighted_rmsd.csv` (analysis E):
   `frame,time_ps,ca_resid_weighted_rmsd_angstrom,core_rmsd_angstrom,lid_rmsd_angstrom,nmp_rmsd_angstrom`
5. `outputs/open_closed_backbone_rmsd.json` (analysis A): a JSON object
   `{"value": <number>, "unit": "angstrom"}`

Common conventions: `frame` is the 0-based trajectory frame index. `time_ps` is the per-frame trajectory time in picoseconds; use your tool's reported trajectory time if it provides one, else `(frame + 1)` ps — both agree for this file to within float rounding (the reader's timestep is ≈1 ps and the first frame sits at t ≈ 1 ps). All frames of the trajectory are included; no frames are filtered, subsampled or interpolated.

## Resources and software

Any tool chain may be used provided the outputs satisfy the definitions above (an MDAnalysis-compatible environment can be supplied for convenience; it is not a requirement). The reference method semantics are those of the MDAnalysis `MDAnalysis.analysis.rms` module (QCP superposition; group-selection RMSDs computed without re-fitting after the primary fit; mass/residue-number weighting normalized by the mean weight).

Execution limits: offline, 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s wall clock — ample for this workload (the reference completes in seconds).
