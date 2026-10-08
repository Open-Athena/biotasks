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

## Full inventory continuation, October 8, 2026

The user rejected the 35-document stopping point and clarified that the requested endpoint includes both iterative vocabulary refinement and the full inventory/explorer. Inspected every baseline locator plus 15 earlier pilot additions; independently checked all 952 resulting repository rows. Source format validation exposed 25 Git symlink references and three extension/content collisions. Exact-byte reconciliation removed another 19 duplicate locations. Retained total: 4,245 authoring locators, comprising 4,239 confirmed sources and six unresolved historical locators; nine rendered fallbacks remain separate.

Expanded individual review by 22 cases to 57. Clinical/textual knowledge work and protein design exposed missing fields; v0.5 has 20 fields, 31 modalities and 30 operations. Last contrasts C/D fit this version without more terms, but this is not independent semantic validation or proof of saturation. Inventory-wide rule assignments remain provisional and are visibly separated from individual review and insufficient evidence. The final report gives all denominators.

Streaming recovery used ijson 3.5.1, verified source hashes, and discarded outputs; one known 72 MB source was recovered under a targeted 96 MiB transfer cap. Source inspections remained below 150 MiB peak RSS; the local classifier/build/check stages stayed below 150 MiB. Browser startup first encountered an unavailable bundled executable, then an unsupported single-process configuration. Reusing the installed headless Chromium with the prior successful renderer limit passed search, filters, evidence, export and responsive layout checks. Browser contexts were closed. No biological analysis, model API or paid compute was run. Publication links are recorded in issue comments.

The first HTMLPreview check exposed an inert JSON block being evaluated as JavaScript by the preview service. Changed the embedded payload to an escaped JavaScript assignment. Both local and public checks then passed without page errors; the public check targets immutable commit 4d4ec50fcbf983c28e2ccac66d5bdf9a4c67dd94. Source/label/count artifacts are unchanged by the preview compatibility fix.

## 2026-10-08 — Distribution views

Added a Distributions tab with separate document categories and declared repository scope, reviewed/provisional segments, facet coverage, repository size bins including zeros, largest collections and all authoring formats. Counts deduplicate each term per source. Category drilldowns and reviewed-only views retain evidence access; percentages state their denominators and categories remain nonexclusive. No source labels or inventory counts changed. Browser checks cover all three facets, 4,245-document and 952-repository denominator reconciliation, reviewed-only segments, source drilldown and mobile layout. Local build peak RSS was 159 MiB, within the 250 MiB estimate; browser budget was 400 MiB.

Both the classification explorer and the original source inventory now open with distributions. Moved the original source-level domain/format charts ahead of inventory details and added repository-size bins, preserving historical discovery counts with an explicit snapshot label. The classification explorer defaults to its Distributions tab.

## 2026-10-08 — Correct source explorer vocabulary and presentation

Replaced legacy primary-domain charts, filters and visible row labels in the source inventory with the refined 20-field vocabulary. Scope joins use only the independently inspected original mapped repository README, retain label evidence/review state, and never inherit notebook labels or linked tutorial scope. Unmapped/unavailable scope and insufficient field evidence are explicit; overlapping fields no longer sum to the source denominator. Preserved original domains in historical payload evidence. Matched the classification explorer light background, white panels, teal chart bars, typography and controls. Discovery document counts remain the historical discovery snapshot.
