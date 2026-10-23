# Domain-motion RMSD analysis of an adenylate kinase trajectory

## Objective

You are given an adenylate kinase (AdK) simulation trajectory that samples a closed → open conformational transition, its topology, and a separately supplied open-conformation reference structure. AdK contains a stable CORE domain and two mobile domains that move around it:

- **CORE**: residues 1–29, 60–121, 160–214
- **LID**: residues 122–159
- **NMP**: residues 30–59

Characterize this domain motion by computing, per trajectory frame and per weighting scheme, the root-mean-square deviation (RMSD, in Ångström) of backbone and alpha-carbon atom sets relative to a reference frame, plus one static structure-vs-structure comparison, exactly as specified below.

## Supplied inputs

The analysis uses three molecular files, all available offline in the supplied environment from the installed MDAnalysisTests package (`MDAnalysis.tests.datafiles`: `PSF`, `DCD`, `CRD`), with versions pinned by the environment lock:

- **Topology** (PSF): atom/residue identities, including atom names, residue numbers (`resid`) and atomic masses, for the AdK system.
- **Trajectory** (DCD): 98 frames of coordinates. The DCD stores no absolute timestamps; each frame's "time" value is assigned by the trajectory reader's default timestep convention.
- **Reference structure** (CRD): coordinates of the open AdK conformation, sharing the same topology.

Software choice is open: any tool that reads these files and computes the quantities below is acceptable. A compatible offline environment (including MDAnalysis 2.11.0 and MDAnalysisTests 2.11.0, among others) is supplied for convenience.

## Definitions

- **Backbone atom**: a protein backbone atom named `N`, `CA`, `C`, or `O` (terminal oxygens `OT*` are not backbone).
- **Alpha-carbon**: an atom named `CA`.
- **Residues** are identified by their residue numbers as defined in the topology.
- **Reference frame** for all trajectory analyses: frame 0 (the first frame, i.e. the closed conformation).
- **Optimal superposition**: the translation and rotation that minimize the (weighted) RMSD of the selected atom set (Kabsch/QCP).
- **Weighted RMSD** with per-atom weights $w_i$:
  $$\mathrm{RMSD} = \sqrt{\frac{\sum_i w_i \left|\mathbf{x}_i - \mathbf{x}_i^{\mathrm{ref}}\right|^2}{\sum_i w_i}}$$
  Unweighted means all $w_i$ equal. (Any common rescaling of the weights leaves the value unchanged.)
- **Domain-group RMSD after global fitting**: once a frame has been superimposed onto the reference frame by fitting the designated fitting group, a domain's RMSD is computed from the already-transformed coordinates against the reference domain coordinates **as they appear in the reference frame**, with no additional fitting and no re-centering (neither centroid subtraction nor rotation) applied to the domain or its reference coordinates.

## Required computations

1. **Backbone and per-domain RMSD (unweighted).** For each trajectory frame, superimpose the frame onto the reference frame by optimal (unweighted) fitting on **all backbone atoms** of the system. Report (a) the RMSD of that full backbone set, and (b) the RMSD of each domain's backbone atoms (CORE, LID, NMP as listed above), computed after the global fit per the "domain-group RMSD after global fitting" rule, unweighted.

2. **CORE alpha-carbon RMSD (unweighted).** For each trajectory frame, compute the RMSD of the **alpha-carbon atoms of CORE-domain residues** after optimal (unweighted) superposition of that same atom set onto its frame-0 counterpart.

3. **Mass-weighted RMSD.** For each trajectory frame, superimpose the frame onto the reference frame by optimal fitting on **all protein alpha-carbon atoms**, with each atom weighted by its **atomic mass** (from the topology), reporting the mass-weighted RMSD of that alpha-carbon set. Then report the mass-weighted RMSD of each domain's backbone atoms (CORE, LID, NMP), each atom weighted by its atomic mass, computed after the global fit per the "domain-group RMSD after global fitting" rule.

4. **Residue-number-weighted RMSD.** Identical construction to computation 3, except the fitting group (all protein alpha carbons) is weighted by each atom's **residue number**, and each domain's backbone atoms are weighted by their residue numbers.

5. **Open-vs-closed backbone RMSD (static comparison).** Compute the RMSD between the backbone atoms of the **first trajectory frame** (closed conformation) and the backbone atoms of the supplied **open-conformation reference structure** (same topology), after subtracting the centers of geometry of the two backbone coordinate sets and applying optimal rotational superposition. Unweighted. This is a single value.

## Required outputs

Write five CSV files (comma-separated, one header row, no index column) to the task output directory. One row per trajectory frame for outputs 1–4, ordered by increasing frame index.

1. `backbone_rmsd.csv` — header: `Frame,Time (ns),Backbone,CORE,LID,NMP`
2. `core_ca_rmsd.csv` — header: `Frame,Time (ns),CORE`
3. `mass_weighted_rmsd.csv` — header: `Frame,Time (ns),C-alphas,CORE,LID,NMP`
4. `resid_weighted_rmsd.csv` — header: `Frame,Time (ns),C-alphas,CORE,LID,NMP`
5. `open_closed_backbone_rmsd.csv` — header: `backbone_rmsd_angstrom`, exactly one data row (the value from computation 5)

Column conventions:

- `Frame` is the 0-based frame index.
- `Time (ns)` holds the per-frame time value assigned by the trajectory reader for that frame (the file contains no stored absolute times; the column label is retained from the original analysis labeling).
- All RMSD values are in Ångström, written at full precision.
- The backbone, CORE, LID and NMP atom sets and all weightings are exactly as defined above; do not modify the inputs, skip frames, or alter the reference frame.

## Environment and constraints

- Offline execution: no network access.
- Time limit 600 s; 4 CPUs, 8 GiB RAM, 10 GiB disk.
- The supplied environment is provided for convenience only; meeting the output specifications above with any toolchain is acceptable.
