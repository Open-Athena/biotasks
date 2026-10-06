# Notebook2task logbook

## 2026-10-06 — experiment preparation

Read live issues #17 and #10 and current repository guidance. Started from
verified current main `2a1950d239f1ada467c35393991dac87debe35f7` on permanent
research branch `codex/research/17-notebook2task`.

Drafted baseline v0, an output contract, intake manifest, and comparison protocol.
The prompt separates objective extraction, actual reference execution, package
construction, author checks, and independent handoff. These choices implement
the issue's proposed workflow; effectiveness is untested. No scientific claim
or prompt winner follows from this preparation.

Requested source analyses from Gonzalo. None supplied yet. No model settings,
service budget, remote compute, task harness revision, or concurrency allocation
has been selected. Proposed a 60-minute author-job limit with two repair cycles
for discussion; no paid or parallel jobs launched. Runner implementation and
contract validation remain pending backend selection.

Next: freeze supplied sources and splits; agree execution settings and limits;
implement the backend-specific batch runner; checkpoint executable inputs;
run baseline and independent checks before proposing empirical revisions.

### Source-selection steering and explorer

Gonzalo asked to brainstorm familiar sources in Scanpy, DESeq2, and bedtools,
then pointed out that #10 already inspected relevant tutorials. Reused seven
specific records from its final commit `a4075ff9cc6cdf50a6e760b438b9dc4b91f758c1`,
with original source locators and limitations. Added documentation-based PBMC3k,
AlphaGenome, and gReLU suggestions at his request. No new broad inventory run.

Built an HTMLPreview-compatible, self-contained explorer with 14 source
candidates across five repositories, search, repository/role filters, source
links, task proposals, evidence states, and filtered JSON export. Atlas is an
API-guide seed rather than an identified notebook. Seven entries link to prior
inspection records; multiple ideas or analyses can share data. No split assigned.

Gonzalo highlighted Atlas's precomputed scores and allowed a "fake" API within
scope. Record this as a fixture-backed replay API: verified real responses,
explicit supported queries, no invented predictions. No API calls were made.
Current AlphaGenome main at inspection was
`038d253a5ca2fec46f4874f592d9ec67984cb497`; gReLU was
`e6fd1d4c3bec4cb3a864e09320662bc3844d0ea9`. Atlas client docs confirm score
queries. The AlphaGenome README restricts model-training use, subject to specified
permissive downloadable-artifact exceptions; exact artifact eligibility remains
unresolved. Terms/Atlas landing pages were unavailable through the web tool.
Do not confuse code licensing, API use, downloaded artifact terms, or task reuse.

The current Scanpy introduction explicitly uses benchmark-derived inputs and
is excluded from training candidates. gReLU's design tutorial includes test-set
intervals, which must be excluded from training; its random-sequence example is
separate. All other overlap/terms checks remain unresolved, not passed.

### Preparation validation

Locked Ruff, format, ty, pytest (5 tests including distribution), and pre-commit
checks passed. Offline explorer browser checks passed across filters, cards,
export, and desktop/mobile layouts. Environment/browser setup failures and
resource receipts are retained under `validation/`. This is packaging/UI
validation only. No worker runner, replay service, source analysis execution,
independent task acceptance, or prompt comparison has been completed.

### Full original notebook display

Gonzalo requested full original notebook display. Added lazy nbviewer embeds for
10 commit-pinned notebooks, with full original hosted documents for the other
four entries, a return-to-task-ideas control, sandboxed frames, and external
fallback links. This requires no kernel or custom hosting, but the full-source
view depends on external services. Display is distinct from fresh execution.

### User corrections: current tutorials, links, and benchmark scope

Removed Atlas from the notebook shortlist because the identified item was an
API guide. Retained replay-API design notes separately. Removed the legacy
PBMC3k introduction and retained the current Scanpy preprocessing/clustering
notebook; refreshed Scanpy source links to current main
`7ad567d9f7ca52b23b0ffb964e486034ef14283e`. This yields 12 candidates.

Gonzalo clarified that the NeurIPS 2021 single-cell benchmark is not an LLM
benchmark and is no exclusion for this experiment. Corrected the overly broad
training hold. Its origin remains provenance; evaluate overlap against relevant
model evaluations rather than rejecting every dataset used in any benchmark.
This supersedes the earlier bone-marrow exclusion in this logbook.

Added prominent original documentation/GitHub links, including Pearson residuals
and ingest/BBKNN. Replaced nbviewer as the default viewer with authors' rendered
pages; optional nbviewer links remain. The two reported Scanpy URLs returned 200
on our HTTP checks, so the reported 503 failures were not reproduced and their
cause remains unknown. Eleven of twelve author pages passed browser embed checks;
the bedtools host timed out. Added the pinned full bedtools Markdown with its
MIT license as a local rendering fallback. Its explicit puzzles provide candidate
objectives, with independent answer validation still required.
