# Classification pilot logbook

## October 8, 2026

After agreement on separate repository and notebook classification, drafted a
local vocabulary and inspected ten pinned documents plus eight root READMEs.
The pilot is deliberately small and separate from the published explorer.

The first examples showed that operation identity alone overstates coverage:
GWAS can be a learner exercise, PCA can be supplied for rendering, and simulation
can be upstream rather than run locally. Added operation roles. Predicted atomic
coordinates and trajectories also require a broader data-modality field than an
assay-only vocabulary, with input origin retained separately.

Kept four README-based field records insufficient rather than filling them from
notebooks or repository names. Recorded the marker-testing versus treatment
inference distinction and two taxonomy questions: Immunology versus immune-cell
setting, and Bioimage analysis versus Cell biology. See README.md for the sample
matrix, caveats and proposed decisions. Structural validation passed; no
independent biological review, execution, inventory relabeling or publication.

## Boundary follow-up

Working rules are in decisions.md. The immune repertoire source exceeded the initial 4 MiB cap; GitHub metadata reports 7,926,146 bytes, so the pinned source alone is allowed 8 MiB with a 150 MiB working-set estimate. The first resumed acquisition aborted at the nonblocking shared lock (exit 1; reader did not launch). No blocking wait or polling loop was started.

Extension acquisition completed after the independent rule-writing work, with a 56,096 KiB peak RSS. Four additional documents yielded v0.2: immune receptor and expression fields can coexist, operation targets distinguish computed clonotype clusters from supplied expression clusters, minfi method lists remain discussion-only, and whole-plant RGB imaging does not inherit microscopy or cell-biology labels. Source-backed structural and accounting checks pass for 14 documents and 12 hosts. Eight READMEs were reviewed; four extension hosts remain explicitly unreviewed. No independent biological review or execution is claimed.
