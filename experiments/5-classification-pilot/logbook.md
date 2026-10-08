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

## Iterative expansion completed

Published v0.2 at 57ebcf13251ce1a67ad641ccc7593f68483d8643. The user then clarified
that repository expansion and vocabulary refinement should alternate, and asked
to continue through the bounded vocabulary milestone before corpus annotation.

Checkpointed round 3 at a5daab2: 13 documents acquired, one CytoVI source exceeded
8 MiB and was retained as a failed acquisition rather than raising the cap.
Checkpointed round 4 at 4b66168: four sources added mass cytometry, vegetation
ecology, integration and a csaw migration stub. Checkpointed challenge inputs at
4017090: four sources recovered the migrated ChIP chapter and challenged generic
software, synthetic RNA and upstream simulation boundaries. Repository expansion
inputs and explicit refinement materializer were checkpointed at 8e9ec7c.
Acquisition JSON records retain exact inputs, timings, statuses and resource peaks.

The final pass has 35 source annotations across 31 hosts. Separately inspected
29 root READMEs and retained two unavailable checks. Repository field states are
17 supported, 10 insufficient, two not applicable and two unavailable. Added
four operation terms and seven modalities; all 18 candidate fields have substantive
examples. Revisited the original 14 records; iteration-diff.json preserves the
comparison. Source identity reconciliation yields 20 exact frozen-registry
matches and 15 outside candidates; no corpus labels changed.

Evidence-locator, vocabulary, identity, distinct-count and targeted boundary
checks pass. The bounded milestone is complete. No independent biological review,
notebook execution, model calls, paid compute, or full-inventory annotation was
performed. Future vocabulary changes require new evidence and affected-record
review. Final publication is recorded in the issue comment, with immutable links.
