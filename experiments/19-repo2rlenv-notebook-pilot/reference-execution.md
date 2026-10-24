# Notebook reference workflow

Contract updated 2026-10-23. The run examples below are historical single-case
evidence, not a current panel-wide success claim. Preparation selects existing terminal results and
returns export code for the controller to append to the untouched source.
[Run 010](preparation-runs/010/README.md) passed static preparation review and
confirmed [run 009](preparation-runs/009/README.md) with byte-identical prompt,
input and API request. [Setup run 001](setup-runs/001/README.md) now completes the
full reference offline in 147.5 seconds with the reviewed exports unchanged.
Source/export review and archived-output inspection pass for this notebook;
that recorded stage did not establish independent numerical reproduction or
cross-notebook generality.

## Stages and exact responsibilities

| Stage | Input | Work | Output and status |
| --- | --- | --- | --- |
| Conversion (programmatic) | Pinned original notebook JSON. | Pinned Jupytext `py:nomarker` conversion; preserve Markdown as comments; check source code order and syntax. No notebook execution. | `baseline.py` and conversion receipt. Implemented for the admitted Python profile. |
| Preparation (GLM, no tools) | Complete baseline script, provenance, conversion receipt and intended execution limits. No data contents, stored notebook outputs or images. | Select terminal scientific results already held in original named variables or object fields; add code to save those values. | `export_code` only, one `artifacts` inventory, explanation, excluded outputs and unresolved assumptions. Runs 009 and 010 pass static source/export review; setup run 001 executes the reviewed exports successfully. |
| Preparation checks (programmatic) | Complete worker response and untouched baseline. | Append export code to the untouched baseline; validate JSON Schema, combined Python syntax and unique output-relative paths; save response and compute diff. Execute nothing. | Script and diff ready for inspection. These checks do not prove scientific fidelity. |
| Scientific review (separate GLM call) | Original script/narrative, proposed script, diff and inventory. | Check endpoint eligibility, exclusions, faithful saving and unchanged science against the original source. | Approve, revise or reject with specific findings. This review does not replace executable reproduction or downstream scientific controls. |
| Environment and input setup (tool-enabled execution worker) | Reviewed preparation output, original source/provenance and available environment instructions. | Inspect dependencies, build and test the environment, download original inputs, configure caches and offline paths; preserve recipe, lockfile, hashes and changes. | Recipe, uv lock/environment records, staged-file hashes, failed/successful trial evidence and an outcome requiring scientific review. Implemented; setup run 001 passed its first controller test. |
| Scientific execution (programmatic) | Prepared environment, staged original inputs and reviewed script. | Run the ordinary script offline, CPU-only, with the agreed resource/time limits; record outputs, logs, timing and failures. | Measured reference evidence from the setup worker’s controller-owned test_reference tool. Run 001: 147.5 seconds, 4.94 GiB peak child RSS, all three declared exports produced. |
| Coverage and task specification (GLM, read-only tools) | Source, preparation inventory, executed reference, output audit, task policy and version-pinned package catalog. | Review coverage/fidelity; draft the pinned reference recipe and output schemas with open solver tool choice. Optional package/reference inspection resolves concrete ambiguities. No shell or scientific execution. | Submit a review, public draft and short validation handoff, or a focused evidence request with empty brief. [Recorded input example](specification-inputs/011/README.md); [canonical prompt](../../src/biotasks/prompts/notebook-task-specification.md). Executable validation must establish public comparison rules before solving. |

The current converter admits ordinary Python nbformat-4 sources. Unsupported
kernel-dependent syntax/state is rejected; other languages need separate
profiles. The user-selected newer Scanpy source and untouched conversion are in
`reference-inputs/scanpy/`; source identity and terms are in `source-manifest.json`
and `seeds/current.json`. No seed-specific endpoint rules are in the factory.

## What preparation may save

Select scientific end products, not every object that remains in memory.
Eligible results must already be stored in named variables or fields in the
original script. Save their values and identifiers through native writers or
straightforward format conversion. Select results from the analysis goals before
choosing storage. Exclude mixed analysis-state containers; select their terminal
fields instead. Standalone result tables or embeddings may be exported whole,
preserving meaningful fields and identifiers. Explain any omitted result fields.
Plot display or earlier computation does not automatically make a result intermediate.

Intermediate matrices, diagnostic counts, checkpoints and full-state snapshots
are outside the exported targets. Do not add computation for exporting results:
no new filtering, ranking, aggregation, scaling or reconstruction of plotting
internals. Do not turn a previously unnamed expression into a new variable.

These constraints apply to preparation's terminal-result exports. The later
specification/construction stages may explicitly supply a notebook-derived
intermediate as a task input, with source identities, derivation and stable
alignment, when substantial unchanged downstream analysis remains and its
requested answers are withheld. GLM owns this reviewed scope decision and its
input construction. It does not permit changing the original scientific source,
hiding an unrunnable reference, silently omitting a branch or adding test/repair
allowances.

Construction may also recover an unnamed or overwritten scientific endpoint by
faithfully rerunning its original source computation on the same original inputs
and required state. Preserve methods and arguments, record the source location
and recovery provenance separately, and require independent execution and
meaningful controls before release. This does not permit guessing missing state,
repairing broken scientific source or adding a new analysis. Preparation itself
remains append-only and saves results already accessible at script completion.

Cover independent scientific outcomes in one task, not every tutorial section
or processing step. Classify results from the source narrative and interpretation:
preparatory statistics and diagnostics supporting other results are not extra
targets merely because they survive or are displayed. Apply selection within
annotation tables as well as within outer objects; preserve endpoint fields and
necessary identifiers/context. Explain independent outcomes lacking an eligible
stored result in `excluded_outputs`. Their original computation remains intact. Reject if there
are no eligible terminal results. The preparation worker leaves input-loading
code unchanged and does not generate dependency manifests or staging scripts.

The canonical [preparation prompt](../../src/biotasks/prompts/notebook-reference-prepare.md)
and [review prompt](../../src/biotasks/prompts/notebook-reference-review.md) state
these rules. Scientific eligibility and preservation need review; the schema
and syntax validator alone cannot enforce them.

## Preparation interface and run boundary

`run_preparation.py` uses GLM-5.3 with native `high` reasoning requested and
strict JSON-schema responses. The served effective reasoning level is
unverified. The autonomous runner allows one initial call and at most one
correction shared between programmatic schema/syntax validation and a runtime
failure in the appended export code. A valid first response uses one call. If
execution exposes an export failure and that correction remains unused, the
worker can receive the executor's error and observed data layout. The original
source, selected endpoints and inputs stay fixed; a corrected export must be
retested using an existing unused reference-test slot. A correction already used
for static validation cannot be reused at runtime. Preserve both responses,
the failed trial and exact feedback when a correction is needed. Empty, truncated or
transport-failed responses do not receive this repair. There are no extra client
token/byte limits; the per-request timeout remains 600 seconds. A standalone
configuration may retain a one-call allowance. It creates no task sandbox and
executes no generated code.
The worker returns `export_code` instead of a full script. The controller saves
that response as `exports.py` and constructs `reference.py` as the untouched
baseline, two newlines, then that code. Original text is preserved by
construction. Artifact paths are relative to `/work/outputs`. No separate branch
map or duplicated environment inventory is requested.

The former combined runner is retired. `run_reference.py` and its packaging path
refuse execution before submitting a job. This prevents the old text-only
setup workflow from running against the new preparation schema. Its historical
implementation is preserved at
[2e1fb63](https://github.com/Open-Athena/biotasks/blob/2e1fb637ed0a8dad48e4e8ef9017e49e765d9575/experiments/19-repo2rlenv-notebook-pilot/run_reference.py).
The separate `run_reference_setup.py` consumes a reviewed preparation directory.
It reuses the Tasksmith artifact-stage tool loop, GLM adapter, uv helpers,
DaytonaWorker, network checks and owned-resource cleanup. It does not regenerate
preparation or invoke task construction, a solver or publication. The retired
entry point remains disabled.

## Tool-enabled setup and offline test

The canonical [setup prompt](../../src/biotasks/prompts/notebook-reference-setup.md)
is the actual worker prompt. The worker receives preparation provenance,
inventory/exclusions/uncertainties, sandbox file paths and explicit allowances.
The full original script and frozen exports are files it can inspect with tools.
It produces five editable files under `/work/setup`: `analysis.py`,
`pyproject.toml`, `system-packages.json`, `stage-inputs.sh` and `inputs.json`.
The final model report is small: tested/blocked, explanation, source-adaptation
rationale and unresolved assumptions. The report does not contain a new script,
export selection or hand-authored evidence.

| Responsibility | Worker | Controller |
| --- | --- | --- |
| Dependencies and data | Inspect source/docs and actual errors; declare dependencies and original input/cache sources; write the staging recipe. | Build a fresh uv virtual environment, generate a lockfile, record installed packages, execute staging and hash the declared files. |
| Source adaptation | Make only necessary offline input/path/cache changes to an editable analysis copy, explaining them. | Preserve the original and compute every diff; append reviewed exports unchanged. Semantic faithfulness still requires review. |
| Testing | Call `test_reference`; diagnose failures within agreed bounds; report a blocker when the science or exports would need changing. | Clear working/output directories, enforce offline network policy, run the complete reference for up to 600 seconds, verify input hashes, inventory and download outputs with checksum verification. |
| Completion | Submit the brief outcome. | Reject a success claim without a passing test or if files changed since that test; preserve every failed trial and clean up the owned sandbox. |

Shell exploration has network access; full scientific computation belongs only
in `test_reference`. A test allowance is consumed before validation/build, even
if setup fails. The controller records raw logs; it does not interpret a model's
success claim as execution evidence. Transport uncertainty ends the session
rather than launching a possibly duplicate command. Provider policy readback
and representative network probes are recorded, not described as exhaustive
network attestation.

A passing outcome is `reference_executed_requires_review`. Syntax, file hashes
and process success cannot establish that a source adaptation preserved science.
The input receipt covers declared files, not a proven complete dependency graph.
The virtual environment is rebuilt for each test; OS packages and caches share
the disposable sandbox, so this is not a fresh-image reproducibility proof.
All such limitations stay distinct from a validated task or grader.

`reference-setup.json` points to reviewed preparation run 010. It carries the
existing 30-minute cumulative setup-tool allowance, 600-second reference tests,
2-hour campaign/5-minute cleanup and $5 reservation as proposed execution values.
The model-request count is explicitly `null`: there is no request-count cap.
Requests remain recorded, with time and spending limits active. The reference-test
allowance for session 001 is two combined invocations; one was used.
Each actual reference dispatch counts even if setup or validation then fails;
a controller refusal before dispatch does not consume a reference test.
Historical preparation/45-request budgets are not inherited. Subsequent runs
request GLM's native `high` effort with no extra client token/input/response caps;
this does not retroactively change session 001's recorded settings or prove the
served template's effective effort. Each individual model request retains the 600-second timeout.
Upstream's final-report tool schema/size limits still apply; scripts and logs
are files rather than fields in that report. Session 001 made 93 model calls and
one complete reference test; its owned sandbox was cleaned up.

### Next-version timing notice

The tool-enabled authoring controller now has a candidate informational
[timing notice](../../src/biotasks/prompts/worker-runtime-budget.md). Each request
includes the time remaining before its existing controller deadline and the
existing per-request timeout. The notice is recorded with the exact model input;
older countdowns do not accumulate in the conversation. Pure text-only
preparation retains its existing input interface. No deadline, call allowance,
validation requirement or retry is added or reset.

This is an offline-tested candidate. The ten-case cohort remains frozen on
`501fbc2f` without this notice; its effect on live worker behavior is unverified.

## Historical single-case preparation/setup evidence

Runs 009 and 010 select explicit cell-result fields, UMAP and full ranked marker
results, excluding the unwanted supporting diagnostics/intermediates. Run 010
also saves stored test parameters as context. Both passed static source/export
review, structural checks and exact source preservation. Their different file
layouts are acceptable; the prompt does not prescribe package names, field names
or a seed-specific output list. The same scientific-role test must be evaluated
on other seeds before claiming generality.

Earlier outputs remain unchanged: run 007 exported a mixed-state object; run 008
avoided that dump but still copied broad diagnostic tables. Run 006 used the
preceding full-script response contract. The
[historical execution record](https://github.com/Open-Athena/biotasks/blob/2e1fb637ed0a8dad48e4e8ef9017e49e765d9575/experiments/19-repo2rlenv-notebook-pilot/reference-execution.md)
describes scientific runs under a superseded workflow.

That preparation remained unchanged. The first setup/reference session
passed, and source/export review plus output integrity/structure checks are
satisfactory for this notebook. No further setup prompt changes or replacement
session were needed for that iteration. Those records alone do not establish task
construction, scientific comparisons, Harbor validation, solving or publication.
No viewer update or downstream execution accompanied that iteration. Cold-image
reconstruction and repeat-run stability were not established by the setup session;
consult the run review before interpreting its evidence.

## Reference repeatability before grading

The [programmatic replay step](reference-replay.md) reuses the successful setup
snapshot, saved uv lock and unchanged source/exports. It runs two fresh offline
processes and records byte comparisons, without model calls or scientific edits.
This supplies initial repeatability evidence for the later acceptance-rule worker;
it does not itself validate a grader. See [configuration](reference-replay.json).

[Replay 001](replay-runs/001/README.md) completed both offline runs in 223.60 s and
178.18 s. Every output file matched the original reference byte-for-byte. Zero
model calls and verified cleanup. This establishes observed repeatability for
these runs; the replay records alone do not validate grading rules or wrong-output controls.

The [autonomous controller](run_autonomous.py) subsequently implements the
reference stages followed by task construction, scientific controls and native
Harbor trials. Its run-specific manifests and validation records establish how
far each candidate actually progressed. The historical examples above must not
be substituted for those candidate-specific gates.


## Coherent quality revisions

A source-approved question defect may use the existing one quality-repair iteration
to correct both the base question and related generated grader/addendum defects.
The GLM worker returns complete revised fields through the versioned comparison
repair prompt. The controller binds check identities and output coverage, preserves
original mutation scripts, and reruns them with fresh independent execution and
source-aware review. Annotation corrections use the existing evidence requirements;
no failed scientific challenge is silently replaced. Source, data, reference and
scientific computations remain fixed. A remaining defect is a rejection; no second
quality iteration or deadline reset is implied. Original candidates and failures
remain separate from the derived revision.

### Failure evidence transport

The scientific worker normally exports each original file and writes its final
manifest only after download verification. Case129 reached its campaign deadline
while uploading thousands of files, so its surviving objects and three earlier
stage manifests were recoverable but the whole scientific archive had no final
seal. That remains an incomplete archival outcome, despite independently verified
resource cleanup.

The outer Iris launcher now has a failure-only backup: after its child has
stopped, it packages the unchanged autonomous working directory, preserving file
bytes and modes in a gzip tar plus a per-file manifest. It reuses the normal
credential scan, streaming upload, complete download hash check and transport
seal. Files containing a configured credential, symlinks or concurrent changes
prevent a sealed backup. This runs only inside the existing cleanup allowance,
reserving its last fifth for the smaller original diagnostic export. It does not
extend model/scientific time, repeat any analysis or change the scientific result.
A transport failure is recorded separately from the original pipeline error.

For the remaining frozen cohort payloads, apply this **only to the outer
`bootstrap.py`** and record a separate launcher freeze. Preserve the original
payload and all198scientific-worker files/prompts, configuration and seed bytes.
Do not claim whole-launcher identity across this variation. The offline transport
check over2,272recovered files is a scale check of the backup mechanism, not a
recovery of absent originals or live proof of remote storage reliability.

### Direct analysis execution in the setup shell

The existing setup prompt requires full scientific computation to use
`test_reference`. A live worker nevertheless attempted an ad-hoc `analysis.py`
launch in the setup shell; that attempt failed during an input-package import and
provides no valid scientific result. Preserve such attempts in the final audit,
separately from controlled tests and source-quality conclusions.

A next-version candidate now refuses literal launches of the controller-owned
`analysis.py`, `original.py`, `reference.py` and `exports.py` roles at the shell-tool
boundary. It records the command hash and returns corrective feedback without
remote dispatch, consuming no reference test or setup tool time. Package imports,
file inspection and static compilation remain available. This is a conservative
accident guard, not an exhaustive shell/Python interpreter or security sandbox;
renamed scripts, dynamic execution and other scientific computations are still
forbidden by the existing contract. The frozen ten-case scientific workers do not
include this candidate. No new stage, model call or execution allowance is added.
