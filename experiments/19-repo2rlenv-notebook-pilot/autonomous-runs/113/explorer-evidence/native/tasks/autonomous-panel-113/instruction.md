# Domain-motion RMSD analysis of an adenylate kinase trajectory

## Objective

You are given an adenylate kinase (AdK) simulation trajectory that samples a closed → open conformational transition, its topology, and a separately supplied open-conformation reference structure. AdK contains a stable CORE domain and two mobile domains that move around it:

- **CORE**: residues 1–29, 60–121, 160–214
- **LID**: residues 122–159
- **NMP**: residues 30–59

Characterize this domain motion by computing, per trajectory frame and per weighting scheme, the root-mean-square deviation (RMSD, in Ångström) of backbone and alpha-carbon atom sets relative to a reference frame, plus one static structure-vs-structure comparison, exactly as specified below.

## Supplied inputs (under `inputs/`)

- **Topology** `adk.psf`: atom/residue identities for the AdK system (closed state, derived from PDB 1AKE), including atom names, residue numbers (`resid`) and atomic masses.
- **Trajectory** `adk.dcd`: 98 frames of coordinates sampling the closed → open transition. The DCD stores no absolute timestamps; each frame's "time" value is assigned by the trajectory reader's default timestep convention.
- **Reference structure** `adk_open.crd`: coordinates of the open AdK conformation (derived from PDB 4AKE), sharing the same topology as `adk.psf`.

Software choice is open: any tool that reads these files and computes the quantities below is acceptable. A compatible offline environment (including MDAnalysis 2.11.0, among others) is supplied for convenience.

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

## Acceptance rules

# Acceptance rules (addendum to the task specification)

The grading compares five CSV files read at the declared output paths (`backbone_rmsd.csv`, `core_ca_rmsd.csv`, `mass_weighted_rmsd.csv`, `resid_weighted_rmsd.csv`, `open_closed_backbone_rmsd.csv`), each relative to the submission output root. Files placed elsewhere (for example under an additional nested output directory) are not found and fail.

## Format conventions

- Each file is plain comma-separated text with exactly one header row and no index column. The header must match the specification exactly (same column names, same order). Ragged rows, empty/missing fields, nonfinite values (NaN/Inf), non-numeric text, surrounding whitespace within fields, NUL bytes and duplicate header names all fail.
- CSV field quoting (RFC 4180 style double-quote enclosure) is a serialization detail only. A quoted field is accepted exactly when its unquoted content satisfies the same rules: the header names must match exactly after parsing, and each numeric field must be a well-formed finite number without surrounding whitespace. Quoting never rescues content that fails those rules; a quoted field containing embedded commas, whitespace or non-numeric text fails just as its unquoted equivalent would.
- Outputs 1–4 contain exactly one data row per trajectory frame, ordered by increasing 0-based frame index and covering every frame of the supplied trajectory without omissions, duplicates or extra rows. The `Frame` column equals the 0-based row position (integer-valued; writing `7` or `7.0` are both accepted since only the parsed value is compared).
- `open_closed_backbone_rmsd.csv` has exactly one data row containing the single RMSD value.
- Values are compared numerically after parsing. Writing numbers in any fixed, scientific or shortest-round-trip notation is acceptable at full precision; rounding that loses scientific precision beyond the tolerances below fails.

## Numeric comparison rules

- For each RMSD column, the submitted value `s` is accepted relative to the reference value `r` when `|s - r| <= max(3e-6 Å, 1e-9 · |r|)`, with the reference value as denominator. The 3e-6 Å absolute floor covers both frame-0 self-comparison values (which legitimately sit near zero) and coordinate-storage/serialization rounding for Å-scale values; the 1e-9 relative tail is a guard for arbitrarily large values only.
- `Time (ns)` holds the reader-assigned per-frame time value and is compared absolutely at 1e-9 (both accepted implementations produce bit-identical frame times for this trajectory). It is a required column with real scientific content; it is not free-form.
- All five outputs must agree with the reference, i.e. membership plus multiplicity per frame row; subsets, permuted rows or added unsupported rows are rejected. Row alignment uses the `Frame` column (not file order alone).
- Nonfinite (NaN/Inf), missing or unparseable numbers fail the corresponding check even where a tolerance would otherwise apply; negative RMSDs fail by value comparison.

## Cross-file consistency

The four per-frame tables report the same trajectory and must carry the identical `Time (ns)` value for each frame. The RMSD columns themselves are different scientific quantities per file and are compared only against their same-named counterpart in the same file at the same frame row.

## Task directories

Read the supplied inputs from `/workspace/inputs/`. Write all required output files under `/workspace/outputs/`, using the relative filenames specified above. The working directory is `/workspace`. Aliases `/inputs/` and `/outputs/` refer to these same directories.
