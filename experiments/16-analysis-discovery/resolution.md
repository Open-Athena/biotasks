# Source recovery and input tracing — 6 October 2026

The 100-document inventory now has **98 substantive static inspections and two
original access-only leads**. Assessments are **70 apparently suitable, 19
unresolved, and 11 excluded** (the unresolved count includes those two leads). No analysis was
executed. The first 40 records and original route comparison remain unchanged.
This is another research checkpoint, not completion or release readiness.

## The nine previously uninspected documents

| ID | Current assessment | Decisive evidence |
| --- | --- | --- |
| L02 | Apparently suitable | PlantCV multi-object notebook has an explicit image present in its repository tree, segmentation choices and per-leaf traits. Interactive ROI choices need fixing before automated execution. |
| L27 | Excluded | Scirpy scaling guidance assumes an existing data object; it does not supply a worked biological experiment. |
| L39 | Apparently suitable | DESeq2 count/metadata alignment, design contrasts and inference use explicit packaged examples. Current source relocates pasilla files into DESeq2; versions cannot be mixed casually. |
| L40 | Excluded | Minfi's inspected vignette works through import and classes, while later QC/biological-analysis sections are largely outlines. This is a document decision, not a package judgment. |
| L41 | Apparently suitable | Phyloseq uses named GlobalPatterns/enterotype inputs for diversity, ordination and ecological analysis. |
| L42 | Apparently suitable | Phyloseq/DESeq2 workflow supplies study 1457 data and a diagnosis contrast. Appropriateness for the paired study remains an independent statistical-review question. |
| L45 | Unresolved | FTICR-MS workflow has MsDataHub/Zenodo input locators, but HAM004/HAM005 sample biology is not established by the inspected text. |
| L46 | Apparently suitable | Xcms implements peak detection through alignment, gap filling and feature analysis on faahKO mouse data. Shares that study with L47. |
| L48 | Unresolved | DDA/SWATH workflow uses a measured pesticide reference mixture. A biological specimen or biological contrast is not established; do not count it as observed biological coverage. |

Pinned upstream sources recovered the package vignettes after direct rendered
requests failed. They are not certified byte-equivalent to the originally
selected Bioconductor 3.23 pages. Each record preserves its candidate URL and
records the actual inspection URL, source revision and hash separately.

The PlantCV notebook is 7,898,857 bytes because its document includes outputs.
An explicit 8 MB source cap replaced the original 4 MB limit for this file only;
the other selected sources retained 4 MB limits. No source code was executed and
no separate biological input files were retrieved.

## Unresolved inputs are more specific now

- **DREAM olfaction:** the helper maps `leaderboard` to `data/LeaderboardSet.txt`,
  but the pinned tree has `data/leaderboard_set.txt`. E04 also reads absent
  `rg.npy`. Other paper notebooks refer to missing prediction/ranking caches.
  Some caches have recomputation branches, so absence is not automatically a
  fatal failure. No execution was attempted.
- **New-odorant notebook L35:** both spreadsheets previously left untraced are
  present in the repository tree. `newdata_cids.txt` and the named CID64832
  descriptor file are absent. This narrows the remaining gap without implying
  those spreadsheets were downloaded, validated or cleared for reuse.
- **Microbiome DAA E06:** the companion Gupta2019 lesson supplies construction
  code and upstream taxonomy/metadata/phylogeny URLs. Matching the resulting
  object and phenotype fields to the deck's expected `Gupta2019.rds` remains
  unresolved. The record stays unresolved rather than silently creating data.

The [assessment-change ledger](evidence/resolution-assessment-changes.json)
preserves before/after records against the previous checkpoint. The
[input-reference audit](evidence/resolution-input-audit.json) distinguishes tree
presence from validation; its literal references can include output paths and
templates as well as inputs. The [acquisition metadata](evidence/resolution-documents.json)
and [repository trees](evidence/resolution-trees.json) preserve source identities.

## Next questions

The 70 apparently suitable documents have 54 provisional study-cluster labels.
Eleven labels are shared by multiple documents, including six AdK trajectory
examples and three Arabidopsis RNA-seq chapters. Some labels represent multiple
examples or are placeholders, so 54 is not a verified independent-study count.
This reinforces the need to select by study and workflow, not document total.

A stage-count audit found that O01/O02 had previously inherited the static-inspection
default despite their records explicitly saying no notebook cells were recovered.
The previous 91-inspected checkpoint therefore contained 89 substantive inspections
and two legacy access-only leads. A separate stage-correction map fixes current
denominators while preserving the original manifest records and historical outputs.
The frozen 30-document comparison and suitability totals are unaffected.

Manifest/hash checks pass, and all 100 document identities and the first 40
records remain unchanged. Browser validation for this revision is pending: the
shared heavy-work lock was occupied, so the command aborted before Playwright
started. The previous preview's successful browser checks are retained as
historical evidence and do not certify this revision.

The remaining 19 unresolved assessments include earlier frozen-cohort cases.
Their next review should address exact inputs, biological relevance and version
compatibility; any revisions to the frozen comparison should be recorded as a
new analysis rather than rewriting its original results. Independent-study
coverage, source/data/model terms, and a resource-bounded execution shortlist
still need review. Paper/citation discovery and broader language/challenge
searches remain incomplete. Issue #16 stays open pending user satisfaction.
