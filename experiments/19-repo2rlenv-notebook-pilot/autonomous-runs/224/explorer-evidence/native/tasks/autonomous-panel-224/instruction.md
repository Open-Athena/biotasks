# Quantifying adenylate kinase's open-to-closed transition with RMSD

## Scientific question

Adenylate kinase (AdK) transitions between a closed and an open conformation; its LID and NMP domains move around a comparatively stable CORE domain. Using the supplied topology, a trajectory that samples the closed-to-open transition, and a separate open-conformer coordinate set, quantify this motion with root-mean-square deviations (RMSD, in Angstrom) of atomic positions under several selection and weighting schemes.

AdK's domains, restricted to **backbone atoms**, are defined by residue identifier:

- CORE: `resid 1-29` or `resid 60-121` or `resid 160-214`
- LID: `resid 122-159`
- NMP: `resid 30-59`

Here "backbone" means **the atoms named N, CA, C and O within recognized protein residues** (the standard MDAnalysis `backbone` selection). Terminal carboxyl oxygens are **not** part of the backbone for this analysis: the supplied topology's C-terminal residue (GLY 214) carries terminal oxygens named OT1 and OT2 and no atom named O, and those OT atoms are excluded from every backbone quantity below.

## Supplied inputs

- `inputs/structure.psf` — CHARMM PSF topology for AdK (defines atoms, masses, residue numbers, bonds; also the selection universe for both coordinate sets).
- `inputs/trajectory.dcd` — DCD trajectory sampling the closed-to-open transition (98 frames). **Frame index 0** (a closed conformer) is the reference structure for all trajectory-based RMSD analyses below.
- `inputs/reference_open.crd` — CHARMM coordinate file of the open conformer, read together with the same PSF topology.

## Method

For every RMSD below, coordinates are optimally superimposed (translation + rotation minimizing the weighted RMSD, as in the QCP algorithm) before or as part of the deviation calculation, unless stated otherwise. A weighted RMSD uses weights normalized by the mean of the weights. All RMSD values are in Angstrom.

### A. Single open-vs-closed backbone RMSD

Compute the unweighted RMSD between the backbone atoms (N, CA, C, O; excluding OT atoms) of the trajectory's frame 0 (closed conformer) and the backbone atoms of the open reference structure (`inputs/reference_open.crd`), after centering each coordinate set at its center of geometry and optimally superimposing them. Report one value.

### B. Backbone and per-domain RMSD vs. frame 0

Over every frame of the trajectory, superimpose the full protein **backbone** onto the frame-0 backbone conformation (unweighted best fit). Record:

1. the unweighted backbone RMSD of that fit;
2. then, **without any further alignment**, the unweighted RMSD of the CORE, LID and NMP backbone groups (each computed on the coordinates after the backbone fit has been applied to all atoms, against the corresponding frame-0 reference coordinates).

One row per frame.

### C. Alpha-carbon CORE RMSD vs. frame 0

Restricting the analysis universe to the alpha-carbon (CA) atoms of the protein, superimpose on, and report the unweighted RMSD of, the CORE-domain CA atoms versus their frame-0 positions. One row per frame.

### D. Mass-weighted RMSD

Over every frame, superimpose and report the RMSD of the **protein CA atoms weighted by atomic mass** (mass-weighted fit and mass-weighted RMSD, reference frame 0). Then, without further alignment, report the RMSD of the CORE, LID and NMP backbone groups against their frame-0 coordinates with **each atom weighted by its atomic mass**. One row per frame.

### E. Residue-number-weighted RMSD (custom-weighting variant)

Over every frame, superimpose and report the RMSD of the protein CA atoms with each CA **weighted by its residue number** (reference frame 0). Then, without further alignment, report the RMSD of the CORE, LID and NMP backbone groups with each atom **weighted by its residue number**. One row per frame. (This weighting is a defined comparison of weighting schemes, not a conventional physical metric.)

## Required outputs

Write the following files (UTF-8, comma-separated, header row exactly as given, one data row per trajectory frame **in trajectory frame order**, no index column; RMSD in Angstrom):

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

Common conventions: `frame` is the 0-based trajectory frame index. `time_ps` is the per-frame trajectory time in picoseconds; use your tool's reported trajectory time if it provides one, else `(frame + 1)` ps — the reader's timestep is approximately 1 ps and the first frame sits at t approximately 1 ps, so both agree to within float rounding. All frames of the trajectory are included; no frames are filtered, subsampled or interpolated.

## Resources and software

Any tool chain may be used provided the outputs satisfy the definitions above (an MDAnalysis-compatible environment can be supplied for convenience; it is not a requirement). The reference method semantics are those of the MDAnalysis `MDAnalysis.analysis.rms` module (QCP superposition; group-selection RMSDs computed without re-fitting after the primary fit; mass/residue-number weighting normalized by the mean weight; "backbone" = N, CA, C, O atoms of protein residues).

Execution limits: offline, 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 s wall clock.

## Acceptance rules

## Acceptance rules (grading addendum)

The reference method semantics are those of the MDAnalysis `MDAnalysis.analysis.rms` module (QCP optimal superposition; group-selection RMSDs computed without re-fitting after the primary fit; mass and residue-number weights normalized by the mean weight; "backbone" = N, CA, C, O atoms of protein residues). Acceptance compares the parsed scientific content of your emitted outputs against reference values computed with those semantics on the supplied inputs; no particular library is mandated.

**Compared artifacts.** Exactly the five declared files, each read at its declared path relative to the submitted output root: the four CSV tables and the single JSON object. No other files are inspected, and no fallback locations are searched.

**Row alignment and ordering.** Each CSV must carry exactly one data row per trajectory frame, in trajectory frame order. The `frame` column must equal the 0-based frame index (row i carries frame i); rows are aligned with the reference by this frame index, so the frame column is checked exactly, not numerically. Row count must match the reference exactly (no missing, extra, subsampled or duplicated frames).

**Headers.** Each CSV header row must match the required column names exactly, in order, with no extra or index column (strict string comparison). The JSON object must contain exactly the keys `value` and `unit`, with `unit` exactly the string `angstrom` and `value` a finite non-negative number.

**time_ps.** Per the question's convention, `time_ps` is accepted either as the tool-reported trajectory time or as `(frame + 1)` ps; a submitted value passes if it lies within 1e-4 ps (absolute) of the reference `time_ps` (the two documented conventions agree well within that bound).

**RMSD numeric comparison.** Every RMSD column is compared row-by-row against the reference value r with the limit `|x - r| <= 1e-6 + 1e-6 * |r|` (rtol 1e-6, atol 1e-6, denominator = the reference magnitude), applied per cell; i.e. the maximum accepted deviation is the largest of 1e-6 absolute and a 1e-6 relative difference. This bound covers permutation-level differences (e.g. reordering summations) and ordinary CSV float round-tripping, while remaining far below the ~1e-3-scale differences between genuinely different selections, weightings or superposition choices. Non-finite (NaN/Inf), negative, unparseable or missing values fail, including the meaningful near-zero frame-0 self-RMSD values, which must be reported rather than replaced by exact 0.

**Structural integrity.** Malformed CSV (ragged rows, empty fields, duplicated or blank rows), unreadable JSON, missing files and wrong declared paths are failed checks, not errors.

**No leakage reliance.** Grading reads only the declared output files; agreement is with the reference scientific values, not with any particular serialization format or library version, beyond the tolerances stated above.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
