# Classification pilot protocol

Status: local research draft for discussion, October 8, 2026. Based on the agreed
classification proposal in BioTasks issue #5, following notebook discovery in #16.
This pilot does not reopen either completed study or change its published results.

## Question and comparison

Can independent scientific-field, data-modality and operation labels describe
notebook content more faithfully than inherited repository categories?

Compare two distinct annotation subjects: a repository's declared scope from its
pinned root README, and a document's content from narrative and code. Preserve
unclassified or insufficient-evidence states instead of transferring labels.
Repository records here describe hosting repositories, not automatically every
upstream toolkit. Named tools in notebook records are separately recorded, but
canonical tool-project resolution is future work.

## Sample and budget

Ten purposively selected entries from the existing 100-document candidate pool:
G01, G02, E01, E05, E09, A04, L09, L14, L28 and L17. They cover eight hosts and five
source formats, including two within-repository contrasts. Selection tests broad
teaching collections, specialized documentation, code versus learner exercises,
and supplied upstream analyses. It is not a random or representative sample.

Read only pinned source documents (4 MiB cap each) and root READMEs (128 KiB cap,
two candidate filenames per host). No biological data, environments, model calls,
notebook execution or paid compute. One sequential worker, shared nonblocking
lock, thread caps and reduced priority. Estimated memory: 100 MiB for document
acquisition, 50 MiB for README acquisition. Actual peaks and UTC start/end times
are in acquisition.json and repository-acquisition.json. Source-selection and
acquisition-script hashes are recorded; no pre-run Git commit was made for this
local exploratory draft.

## Interpretation and validation

Annotations are explicit assistant judgments, supported by exact source locators.
This pass reviewed targeted narrative and code; it does not claim exhaustive
operation annotation. Notebook cells are zero-based, text lines one-based.
Repository README assertions are declared scope, not verified capabilities.

The vocabulary is provisional. Distinguish implemented operations (source code
present), exercises, discussion, and upstream-supplied results. Do not equate
source implementation with a successful run or a scientifically valid method.
Withheld labels and review questions preserve ambiguities. All operation lists
are selected, not exhaustive; absence of a label is not proven absence.

Checks validate vocabulary membership, source locators and identity/count
consistency. Biological judgment has no independent reviewer yet. The full
inventory's classified denominator is unchanged: these pilot candidates have
not been reconciled to its canonical registry. A scale-up must join by canonical
document identity, deduplicate representations, and count separate annotation
statuses before calculating classified fractions.

## Local reproduction

The two acquisition scripts fetch only static source text; apply the shared-node
resource guards and lock described in AGENTS.md when rerunning them. Then run
`python experiments/5-classification-pilot/build_pilot.py` to materialize the
explicit annotations and structural checks. vocabulary.md is an editable review
companion to vocabulary.json; both must remain aligned when the draft changes.

No source code from inspected documents is executed. Upstream text caches remain
local and ignored by Git. Pinned URLs, revisions, original-byte hashes and exact
locators are retained for review and reacquisition.

## v0.2 extension

Four additional static inspections test the boundaries: G04 cloud/IGV access,
L25 T-cell receptor and expression analysis, L40 methylation-array introduction,
and L01 whole-plant RGB imaging. This brings the pilot to 14 documents and 12
hosting repositories. Eight root READMEs remain independently inspected; the four
new hosts are explicitly unreviewed rather than inheriting notebook labels.

L01 resolves the old floating `main` link to an immutable revision and is not
assumed to be the historical bytes. L40 uses the prior recovered source revision,
not the rendered page. L25 has a verified 7,926,146-byte source, so it alone gets
an 8 MiB cap; embedded outputs are omitted from inspection text. Estimated memory
for the extension reader is 150 MiB. The executable inputs were committed before
acquisition. The initial 4 MiB cap failure and one nonblocking lock rejection are
preserved in extension-acquisition-failure.json and logbook.md. See the successful
extension-acquisition.json for start/end, exit and peak RSS.

Reproduce with `inspect_sources.py --sample extension-sample.json --prefix extension-`
under the same shared-resource guard, then build_pilot.py and render_vocabulary.py.
Run validate_pilot.py for source-backed accounting and boundary checks. These
checks do not substitute for an independent biological review. The v0.1 draft
is retained in Git at commit 543e514.
