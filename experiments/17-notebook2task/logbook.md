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

### 2026-10-06: published comparison pairs and released-prompt baseline

Gonzalo requested concrete published notebook/task pairs from SETA and BixBench,
then proposed starting prompt v1 from released SETA prompts. Added two reference
cases, distinct from the source shortlist: SETA cytopathology classification and
BixBench v1.5 ASXL1 RNA-seq question bix-1-q1. Source release hashes and retrieved
artifact hashes are under explorer/comparisons/. Only static inspection occurred.

The BixBench capsule's ZIP tail contains the complete 17-cell notebook. Extracted
that member with CRC verification, retaining original source and saved outputs;
no count matrix or other biological input was extracted. The explorer displays
all cells and text representations of saved outputs offline. Its question,
reference answer (collapsed), release links and proposed recipe are visible.
The SETA case displays the full released instruction and links to tests,
solution and environment. The Kaggle source currently returns R Markdown v96;
the generation-time version is unresolved. It is a partial source pair, labeled
as such, with a source link rather than a falsely pinned or mirrored notebook.

SETA's verifier computes ensemble AUC using solver-supplied labels and checks
reported CV summaries; this is a static grading concern, not an executed exploit.
BixBench's source specifies covariates and GO-analysis details beyond its short
question; its revised ideal answer differs from the capsule-level narrative.
These motivate possible recipe changes but establish no execution outcome.

Preserved SETA's unchanged notebook adapter, shared idea prompt and builder
under baselines/seta-v1/, with license, hashes and upstream paths. This supersedes
the earlier bespoke v0 as the planned baseline. Baseline should preserve SETA's
ML-specific filters, record rejected biology sources, and keep harness/input
porting separate. A biology adaptation must be a separate explicit diff. The
original BioTasks draft remains an untested candidate. AutoSDT releases actual
adaptation and instruction templates and is a plausible second baseline;
a comparable BixBench authoring prompt and the specific LongDS authoring skill
were not established in the inspected trees. No authoring/model/scientific run
has been launched; runtime porting, fixed inputs and budgets remain outstanding.

### 2026-10-06: first requested baseline pilot

Executed SETA idea prompts through authenticated Codex CLI, requested
`gpt-6-astra`, medium reasoning. Preserved the initial confounded cytopathology
rejection and retried with the stage boundary clarified. Corrected trial wrote
a frozen-model evaluation draft; the RNA-seq trial rejected its single DESeq2
model under the adapter's multi-model gate. Shared idea and builder prompts ban
model training, in tension with the notebook adapter. The generated draft moves
training to artifact preparation and changes the original task boundary.

A bounded builder continuation timed out after five minutes with partial task
artifacts. Parent static checks passed but no frozen models, reference execution,
or grading validation exists. Exact rendered prompts, real input hashes, traces,
usage and resource receipts are under runs/20261006-seta-v1-pilot/. First monitor
undercounted descendants; corrected monitoring is explicitly recorded.

User authorized Iris CPU or Daytona execution; no remote job submitted before
an intervening billing question. Existing ChatGPT auth was used, no API key;
plan/credit charges are not observable. No new inference or compute is active.

Gonzalo then requested GLM-5.3 through the existing bulk service, superseding
Codex for subsequent trials. Submitted one bounded Iris CPU job (no accelerator,
no inference deployment) for two sequential idea-stage runs with the same real
comparison inputs. Runtime service configuration remains private. The service's
billing terms are not observable in this session. GLM uses a small recorded
read/list/write tool loop, so this is not a controlled model-only comparison.

The GLM dispatch remained pending on peer acceptance and produced no worker
logs or model output. Requested cancellation at 21:34 UTC; confirmed terminal
KILLED at 21:35 UTC. Read-only direct checks did not establish a reachable
service route. No inference deployment or accelerator was provisioned. Saved
the sanitized outcome in runs/20261006-glm53-seta-v1/README.md; this is an
infrastructure-blocked attempt, not a GLM task-generation result. Resuming
requires a working approved route to the existing bulk service.


### 2026-10-06: GLM access recovered using Marin #9775

The successful recent collection used the same bulk service. Its launch snapshot
and the service owner's detailed guide exposed the required published package
pins, HTTPX pin and region-local relay mapping. The original region stayed queued;
confirmed cancellation before moving the sequential one-CPU pilot. Preserved
three setup failures before obtaining 12 successful GLM responses on the alternate
route. No inference deployment or GPU allocation was made.

The first live idea-stage pilot produced no draft: cytopathology exceeded the
serialized context ceiling; ASXL1 exhausted its final output budget in reasoning.
The runner mislabeled the latter completed; original evidence is retained and
the interpretation corrected in the run README. A separate retry keeps source
prompts identical and records increased bounded context/output budgets plus
explicit medium reasoning. Scientific execution and acceptance remain separate.

The bounded GLM retry completed authoring for cytopathology (8 responses,
85.53 seconds) and hit the output limit for ASXL1 (9 responses, 71.87 seconds).
Retrieved and hash-verified both cases. Cytopathology retains training despite
the shared prompt prohibition and proposes weak held-out integrity checks;
these static concerns are documented separately from the verbatim draft.
The explorer displays both GLM outcomes; offline browser interaction checks
passed. No GLM builder or scientific validation was run.
