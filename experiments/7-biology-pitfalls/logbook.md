# Issue 7 research logbook

## 2026-09-30 — scope and baseline

Research branch: `codex/research/7-biology-pitfalls`, created from recorded main
revision `37271415c4c201ba9dbbda66c203caa4050744c3`. The historical branch name
predates the broader improvement scope. No generator, model trial or biological
analysis was run.

Initial question: identify recurring computational-biology pitfalls in literature.
The user broadened it to general software and statistics/ML, then to improvements
of code and analysis artifacts, including benefits beyond correctness. The user
reviewed a temporary Markdown scope draft and authorized updating issue #7 and
continuing the research.

Published title: “Catalog improvement opportunities for computational biology
code and analysis artifacts”. The issue body was fetched after editing and
checked for exact equality with the approved draft; the `agent-generated` label
and open state were verified. `issue-scope.json` preserves that retrieved
publication snapshot. The issue body contains the research budget and deliverable.

## 2026-09-30 — literature synthesis

The initial 32-entry biology draft was replaced by the consolidated
[improvement catalog](../../docs/improvements/README.md), with explicit starting
conditions, intended benefits and biological relevance. The initial local draft had
45 entries and 41 selected publications. The
[method](../../docs/improvements/research-method.md) records search routes,
selection, consolidation, limitations and coverage gaps; the
[source register](../../docs/improvements/sources.md) records evidence locations
and access limitations through its catalog links.

SERA's prompt-generation implementation was inspected at commit
`1ca8673bd527b164dc9eb89841c96416ec8ce1a7`, without execution. A candidate
interpretation of its broad directions as a verified defect taxonomy was rejected:
the inspected artifact is a prompt generator. Defects4J and BugsInPy were followed
as discovery sources, with a later reproduction study supporting concrete
software improvements. Guidance supplies additional conditional opportunities;
it is not relabeled as experimental proof.

Evidence limits: selected sections/excerpts/captions, one reviewing assistant,
no systematic database screening or source-analysis reruns. Initial BugsInPy
paper retrieval failed; that draft used its abstract for the collection-level claim.
No statistics on catalog prevalence, task suitability or teacher-data quality
were produced. No paid compute, generated teacher demonstrations, rendered task
prompts or evaluation outcomes exist for this work.

## 2026-09-30 — broader pipeline question

The user raised verifiability, SFT usefulness and teacher reasoning availability
as a possible repository-wide discussion. A separate temporary issue draft was
prepared for review. It proposes evaluating these dimensions across pipeline
stages and distinguishing final artifacts, observable tool traces, generated
explanations and internal reasoning. After the user authorized filing it, the
draft was published as [issue #11](https://github.com/Open-Athena/biotasks/issues/11).
The exact title/body, `agent-generated` label and open state were verified.
Issue #7 remains the catalog question; existing deterministic-reward requirements
are unchanged.

## 2026-09-30 — final software-evidence review

On resuming issue #7, the review identified limited direct software-defect
evidence beyond environment setup. The 2024 arXiv deposit of the 2020 BugsInPy
paper supplied the previously inaccessible full text. Its selected sections
clarified source-fix and reproducibility criteria; this is an access correction,
not an additional publication.

Screened six pinned pandas patch records; cross-checked four retained records
against upstream metadata, source changes and regressions. Added logical-type
dispatch, compound-label indexing and optional-return contracts, and strengthened
the existing input-contract entry with an explicit error-handling example.
The final catalog has 48 entries and 45 source records: 41 publications plus four
upstream fixes. Biological applications of the added generic defects are inferred.

`software-evidence.json` records selection, revisions, named tests and exclusions.
Record 5's patch/metadata mismatch was excluded rather than counted as another
independent example. These inspections did not execute the source tests and
do not establish defect prevalence or current pandas behavior.

## Validation and publication

`validation-initial.txt` preserves the 45-entry audit. `validation.txt` records
the final structural audit and semantic self-review. Checks cover entry/source
IDs, required fields, reciprocal citations, local links/anchors, navigation and
whitespace. They do not reproduce scientific findings. No runtime or prompt
template changed, so CLI/package tests are not evidence for this documentation
synthesis.

The approved scopes for issues #7 and #11 are published. The research checkpoint
preserves the source-selection records, issue scope and validation evidence.
The maintained documentation is extracted to a fresh pipeline branch from current
main for review, with a permalink to this checkpoint. The research branch itself
must not be merged. The PR and issue provide the current publication state.


## 2026-09-30 — independent review and hypotheses

Issue #7 was reopened after the user clarified that it must remain open until
PR #12 merges. The PR uses a closing reference; no merge has been performed.
The user requested independent review and clarified that plausible opportunities
without established evidence should also be tracked. Supporting evidence is
therefore an entry attribute, not an inclusion requirement. This clarification
does not change the separate task-verifiability and teacher-data discussion in
issue #11 or authorize execution of catalog ideas.

The [independent report](independent-review-b2f021a.md) preserves the review of
pipeline head `b2f021a30166fd782dc569b6c3b3e7095a56b9af`, including its scope and
limits, and separately identifies inspections of subsequent working-tree edits.
Its P2 finding identified missing fitted-preprocessing leakage. I06 now covers
learned transformations as well as supervised selection, cites B08 pitfall 4,
and preserves fixed-transform and transductive alternatives. The reviewer
confirmed that this correction addresses the finding.

The hypothesis follow-up identified a P3 wording inconsistency: the definition
of inferred application assumed general evidence, while I49–I50 did not claim
such support. The author broadened the definition to cover proposed applications
of unvalidated ideas and separately records evidence status. The author also
revised the extension guidance so it does not require new evidence for admission.
These resolutions are in pipeline commit
`f361fc7fe3bd84fd234096da347e9ab537d5b7b3` and are mirrored in this snapshot.
The review report retains its original observations rather than rewriting them.

I49 proposes bounded intermediate processing; I50 develops shared-state isolation
from a visible SERA direction. Both are explicitly unvalidated hypotheses with
origin, conditions, tradeoffs and validation needs. Neither claims an observed
biological defect or demonstrated improvement. There are now 50 entries: the
original 48 sourced descriptions and two hypotheses. The 45 source records are
unchanged in count. Broader generic software coverage remains incomplete.

SERA describes 51 bug types, but its pinned generator contains 30 seed directions
and constructs one initial plus 50 generated prompts. The output JSON was absent
from the inspected revision. No complete 51-to-catalog mapping was recovered or
performed, and no model generation was run. Different units and selective
coverage explain the counts; fewer entries are not evidence of better coverage.

`validation-review.txt` preserves the revised structural audit. The checker now
allows absent citations for explicit hypotheses with origin and validation fields;
all cited mappings remain reciprocal. The independent review is a targeted source
check, not a rerun of scientific analyses or upstream regressions. The source
universe was not independently double screened. Original scope and validation
records remain intact at their existing paths and in checkpoint `aabc801`.
