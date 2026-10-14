# Notebook-to-task upstream pilot

## 2026-10-09: source inspection and intake

Baseline: BioTasks main `2a1950d239f1ada467c35393991dac87debe35f7`.
Research branch: `codex/research/19-repo2rlenv-notebook-pilot`.
No generation, solver, cloud provisioning or publication has occurred for this pilot.

Inspect Repo2RLEnv at `55554430cd724efded1f5ad0ff98ebca5d88c0a6`.
Start from SETA Seed2Synth and its shared quality loop, not the earlier factory.
The source already implements direct structured authoring, task emission, bounded
repairs, offline Harbor execution, quality reports and release tooling.

### Endpoint integration finding

`src/repo2rlenv/llm.py` accepts `LLMSpec.endpoint` and an explicit API-key environment
variable. It sends JSON-schema response requests through LiteLLM with zero retries.
Compatibility with the approved GLM service is not yet tested.

`src/repo2rlenv/execution/harbor.py:run_trial` explicitly rejects custom endpoints
for blind trials, permits direct OpenAI/Anthropic providers, and forwards only
provider API keys. This is a controller restriction, not a demonstrated GLM or
Harbor incompatibility. Recommend retaining Terminus-2 and proposing narrow
endpoint forwarding, with regression tests for credential isolation and the
unchanged offline task network. User asked where the patch would live and why it
is needed; adoption is pending. Proposed location: a versioned patch in this
experiment, applied to the pinned dependency. No fork or patch applied yet.

`OfflineDockerEnvironment` pins Harbor 0.22.0, runs only on the remote worker,
requires no-network policies in every phase and uses an isolated Docker network
namespace. Live enforcement remains unverified. Do not substitute a current Pi
integration without verifying the service's tokenizer compatibility.

### Notebook intake

Added a small reusable Jupyter-to-SETA seed converter. Preserve ordered markdown,
code and raw cell source plus revision/hash/license; omit notebook outputs and
metadata. Reject oversized or malformed inputs rather than silently truncate.
It does not author scientific tasks or establish fidelity. Source text is author
input; the complete notebook must not automatically become solver-visible data.

Candidate: Scanpy PBMC3k tutorial at
`8c1463d5d97272d5811ad3f4efb57483e23b4c7e`,
`docs/tutorials/basics/clustering-2017.ipynb`.
Inspected the actual notebook code. Its QC/filtering/normalization section is a
plausible compact analysis; full clustering is outside the proposed pilot scope.
Prefer the full observed input matrix initially, subject to resource measurement,
rather than silently subset cells and change filtering results. Software choice
remains open. Candidate selection is not yet agreed.

The 10x PBMC3k primary dataset page was read live and states 2,700 cells from a
healthy donor, same donor as PBMC6k, Cell Ranger 1.1.0, CC BY 4.0:
https://www.10xgenomics.com/datasets/3-k-pbm-cs-from-a-healthy-donor-1-standard-1-1-0
Retain attribution and donor relationship in provenance. Source repository license
was fetched separately; data permission is not inferred from the code license.

The earlier bedtools intake recorded enhancers extending beyond the supplied
chromosome length. Do not silently fix that source or presume coordinate-assembly
compatibility. This makes it less suitable as the first minimal pilot.

### Remaining pre-execution decisions

Agree notebook and any reductions, solver integration, backend and resource/time/
request budget after inspection. Upstream worker defaults: 2 CPU, 4096 MB, 10 GB,
3600 seconds. These are defaults, not approved ceilings or a wall-clock guarantee.
Daytona worker uses Docker within the sandbox; Docker readiness and model-service
reachability must be checked before generation. Model dollar-cost estimates alone
cannot enforce a request bound for a free/unknown model. Preserve the agreed build,
repair and solver attempt limits with explicit accounting.

Focused intake checks: four tests passed; Ruff formatting/lint passed. Executed
2026-10-09 21:29:53 UTC, peak RSS 33,392 KiB, exit 0, under the shared heavy-work
lock with one worker/thread limits (estimated working set below 100 MiB).
A source-only conversion of the real notebook completed locally; this is intake
inspection, not a model call, task generation or biological execution.

## 2026-10-09: selected notebook and endpoint patch preparation

User approved Scanpy QC/filtering/normalization with the full observed input matrix.
The converted notebook source is 15,666 UTF-8 bytes; original notebook SHA256 is
`1d4e8b1cb3ef8423bb1c4bb6ad6228e4c54b2352b5d9e7f142619737e189f439`.
No generated artifacts or scientific task instructions have been manually authored.

Following discussion and the user's acknowledgment, prepared a versioned endpoint
patch rather than a fork. Pinned Harbor v0.22.0 source confirms Terminus accepts
`api_base` and `model_info`. Ten helper tests passed at 21:32:22 UTC; peak RSS
33,288 KiB, exit 0. Patch application and Python syntax checks passed. Estimated
working set below 100 MiB; shared lock and one-thread limits used. These checks are
not live endpoint or full upstream integration tests.

Read-only infrastructure inspection showed an additional execution-location
constraint. The endpoint patch is insufficient to establish end-to-end access.
Proposed retaining upstream generation/quality/release and adapting its execution
boundary: model-client host on Iris, offline tasks on Harbor's native Daytona
backend. Harbor v0.22.0 `src/harbor/environments/daytona/environment.py` exposes
no-network support. Actual enforcement remains to be tested. Requested agreement
before preparing the broader integration. No services, sandboxes or jobs launched.

The same read-only session confirmed all ten prior panel-005 jobs are terminal
(eight scheduler SUCCEEDED, two FAILED). Scheduler success does not prove task
validation or resource cleanup; collect their evidence separately without reruns.
Session finished before 21:34:28 UTC, elapsed 2.48 s, peak RSS 249,788 KiB, exit 0.
No automatic retries or new model calls occurred. Private routing details remain
outside the repository.

## 2026-10-09: Iris/Daytona integration preparation

User approved preparing the Iris/Daytona integration and requested an ongoing
issue-body decision log. The dated log and current approach were updated and
fetched back exactly; `agent-generated` remains set.

Installed the exact upstream lock in an isolated `/tmp` checkout, with Harbor and
Daytona extras. No live API calls were made. Initial sync peak RSS 55,420 KiB,
1.33 seconds, exit 0; development dependency sync peak RSS 43,432 KiB, 0.24 seconds.
All local substantial commands used the shared lock, one-thread/one-worker limits
and low scheduling priority; available memory remained above 4 GiB.

Prepared patch 0002: an optional execution adapter in the original SETA runner,
plus a native Daytona environment option in the original trial runner. Preserve
upstream defaults for other callers. Reject network expansion in solver/verifier
phases. Apply the five-minute solver bound via Harbor's agent-only timeout
multiplier without changing the emitted task or other phase limits.

The experiment adapter attaches only to an explicitly allocated host, delegates
task execution/evidence to upstream Harbor, and reuses upstream quality evidence
import. Claims consume attempt slots even when the dispatch result is uncertain.
No endpoint deployment, manual candidate patch or custom quality loop was added.

Tests against the installed pinned source: 28 upstream/helper regressions passed;
seven new routing/offline/attempt-control checks and two SETA adapter/repair-bound
checks passed after correcting unit-fixture schema omissions (reward_kinds,
source tag, executable flag, minimum reference length). These failures involved
synthetic unit fixtures, not a generated biological task. Maximum test RSS was
61,236 KiB. The final two synthesis checks passed in 0.30 seconds, peak RSS
52,420 KiB. No network enforcement or scientific execution claim follows from
mocked control-plane tests.

A concrete execution budget proposal is in `execution-proposal.md`. Agreement,
request-gate implementation, reproducible launcher and live preflight remain
pending. No pilot jobs, task sandboxes, model requests or releases yet.

The user approved the execution proposal: one 2-CPU/4-GiB Iris host on existing
reserved capacity; one active 1-CPU/2-GiB/10-GiB Daytona task; two hours plus cleanup;
USD 1 Daytona ceiling; and 80 maximum outgoing inference requests allocated as
4 compatibility, 4 design/build, 24 quality and 24 per solver attempt. Each solver
has at most 12 turns and 300 seconds. No repeated permission is needed for these
bounds once implementation/preflight checks pass. The user's subsequent question
about Daytona being free was answered as a distinction between account credits
(not verified) and gross metered usage; it did not revoke authorization.

Implemented a loopback-only inference gate to enforce raw request limits even
when an upstream harness retries. It forwards to the already approved service;
no new model or shared service is deployed. Request counts include provider errors
and uncertain outcomes; budgets cannot silently increase on resume. The ledger
contains hashes/states rather than credentials or prompts. Two tests passed,
including concurrent quota claims and an HTTP 503 followed by a blocked retry;
peak RSS 40,788 KiB, 1.26 seconds. Type checks passed after narrowing validated URL
hosts and matching the standard HTTP handler method signature. Integration of
this gate into the launcher remains pending.

Final local integration checkpoint: ten adapter tests pass against the pinned
upstream installation, including separate per-attempt inference endpoints. Ruff
lint/format and project type checks pass. The project suite had ten passing tests
and an offline distribution-build failure when invoked directly; rerunning the
distribution test with the required `uv run --locked` invocation passed without
changing the test or source (0.65 seconds, peak RSS 32,144 KiB). Preserve this
invocation distinction; do not claim the first full-suite command passed.

The approved budget was added to the issue's dated decision log and read back
exactly. Integration remains preparation-only: launcher, live preflight, scientific
generation/validation and publication are outstanding.

### 2026-10-09 — bounded scientific review and campaign assembly

Added reusable notebook-grounding and scientific-fidelity review prompts. The
upstream design patch appends optional guidance without changing the original
schema or call settings. The draft campaign runner connects original SETA and
quality-loop calls to the existing inference quotas and execution adapter. After
the quality loop, GLM assesses observed inputs, methodology, the public contract,
scientific grading and software alternatives within the same quality allowance.
Exact quotations are checked against the supplied evidence; missing dimensions,
unknown outcomes and blocking findings cannot produce a supported assessment.
This remains advisory review, not a reward or independent scientific execution.
The runner explicitly leaves execution-evidence auditing and release incomplete.

Regenerated patch 0002 with explicit resource overrides and recorded patch 0003
in the pin manifest. Sequential application to clean archived upstream sources
reproduces the inspected modified files exactly. Eleven adapter/design tests
passed in 0.58 seconds, peak RSS 54,920 KiB. Three fidelity tests passed in
0.34 seconds, peak RSS 48,144 KiB. The first fidelity invocation failed collection
because the experiment directory was absent from PYTHONPATH; the corrected
invocation uses the same experiment/source paths as the other integration tests.
All execution was local and mocked; no model or sandbox calls occurred. The
launcher, live offline/resource/cleanup preflight, provider-cost accounting and
release orchestration remain unfinished and must precede campaign execution.

### 2026-10-09 — owned infrastructure preflight

Implemented the one-sandbox preflight against the installed Daytona SDK. It
requests the approved 1 CPU / 2 GiB / 10 GiB profile, a ten-minute provider TTL,
private visibility and blocked network access. It checks provider-reported
resources and network settings, then compares sandbox outbound TCP probes with
reachable host controls. This is representative isolation evidence, not an
exhaustive network attestation or a substitute for checking actual task trials.
The fixture contains no biological task, reference or grader authored by the
operator. A persisted claim prevents retrying the preflight automatically.

Cleanup runs on success and failure. In particular, an uncertain create followed
by an immediate not-found observation remains unresolved because provider-side
creation may still finish later. The preflight cannot authorize a following
sandbox without verified cleanup. Three mocked tests passed in 0.44 seconds,
peak RSS 52,892 KiB, covering successful deletion, leaked outbound access and
uncertain creation. The campaign runner now invokes this preflight after its
structured model compatibility check. Nothing has been executed remotely;
campaign cost/cleanup accounting and the Iris submission/export launcher still
need completion before launch.

### 2026-10-09 — supervisor cleanup and frozen Iris launcher

Source inspection found that the original remote supervisor unconditionally
executes Docker cleanup. On an Iris host dispatching Daytona tasks, that would
incorrectly fail even a successful trial. Extended the execution-boundary patch
to label Daytona sandboxes with the supervisor's job identity, delete only those
resources, and verify cleanup. Failed/interrupted creation remains uncertain;
the adapter blocks later trials rather than accumulating possible live resources.
The default Docker path is retained. Sixteen cleanup/adapter/upstream supervisor
tests passed (4.15 seconds, peak RSS 127,168 KiB); after adding explicit supervisor
backend tests, all five focused cleanup tests passed. An initial invocation used
a nonexistent test filename and ran no tests before the corrected invocation.

Added a separate USD 1 reservation ledger: USD 0.058 for image/storage overhead,
USD 0.030 for the preflight and USD 0.057 per scientific trial (16 maximum).
Reservations are retained conservatively rather than treating missing provider
billing as zero. These are internal allowances, not a provider billing cap or an
account charge. Provider usage and cleanup evidence still require reconciliation.
The adapter rejects generated phase timeouts beyond the agreed ceilings.

The Iris submitter packages committed source, the pinned upstream archive and
the single source-bound seed, records input hashes and claims the submission
before contacting Iris. It sets the agreed host resources and disables failure
and preemption restarts. The bootstrap verifies source and patch hashes, installs
the locked upstream environment, builds its matching wheel, resolves the approved
model route and runs the bounded campaign. It exports credential-checked evidence
to private artifact storage and verifies downloads. No credentials are in source
or submission receipts. One mocked campaign-wiring test passed with the real
schemas and loopback gate; sandboxed execution first failed to bind the socket,
then the elevated local-only invocation passed (2.93 seconds, 117,812 KiB).
Live submission and provider behavior remain unverified.

### 2026-10-09 — first approved launch failed; preserve and diagnose

Submitted the single approved campaign from cf222dba3eab6216209aad14427f7ac072fe6255.
The local submitter used 344,212 KiB peak RSS and completed in 15.61 seconds,
holding the shared lock; no submitter process remains. Iris first reported RUNNING,
then FAILED with one failure and no preemptions. The outer traceback reached
run_pilot.py after bootstrap setup and reported subprocess exit status 1; it does
not identify the failing pipeline stage. No replacement campaign was submitted.

Direct access to the private S3 evidence returned HTTP 403 from this VM. Asked for
one separate read-only recovery job on reserved Iris capacity, limited to 1 CPU,
1 GiB and five minutes, because the approved campaign allowed only one host job.
Prepared a bounded diagnostic reader that verifies the original export hashes
and returns selected records through the existing job log. It creates no tasks,
model calls or sandboxes. Approval is pending. Model-request counts and sandbox
creation/cleanup are unverified until the saved evidence is inspected. Updated
the issue decision log with the terminal status and evidence-access limitation.

A read-only Daytona query found zero sandboxes bearing this pilot's preflight
ownership labels. This is current preflight-resource evidence only: it does not
establish whether the preflight ran or whether scientific trials created other
resources. Those questions remain tied to the unrecovered campaign records.

### 2026-10-09 — prior panel outcome recovery from existing logs

While approval for the issue-19 diagnostic recovery job remains pending, read
the ten already-existing issue-18 panel-five job logs. All jobs are terminal:
eight scheduler successes and two failures. Their final emitted pipeline states
are four validation_incomplete, two review_incomplete, two budget_exhausted and
two incomplete. None reports acceptance. The qfeatures traceback reports a
candidate/native-evidence identity mismatch; pyradiomics reports a stage-launcher
failure. Neither establishes a scientific failure in the generated biology task.

Saved the source-bound stage summaries and original log hashes in
prior-issue18-panel5.json. The native artifacts and cleanup records are still
uninspected, so this closes the scheduler/outcome-summary question only, not the
resource audit or scientific validation. No new issue-18 jobs, model calls or
sandboxes were launched. The issue-19 recovery approval remains pending.

### 2026-10-09 America/New_York — recovery and overnight authorization

The user approved the read-only recovery job, then up to ten sequential replacement
campaigns with the existing per-campaign model, time, resource and repair limits.
They separately approved USD 5 Daytona usage per replacement and USD 50 aggregate,
before credits. This allows at most 800 additional inference requests and 20
campaign hours plus cleanup. Stop earlier on success. Recorded these decisions
in the issue body and verified the published text. No additional approval is
needed within these bounds; the original failed campaign remains separate.

The recovery job succeeded. Reassembled diagnostic files from its existing Iris
logs and verified each against the original S3 export hash. Campaign 001 made
exactly one compatibility request, HTTP 200, and parsed its response successfully.
It then failed saving compatibility.json because a nested LiteLLM token-details
object was not JSON serializable. Execution never reached the Daytona preflight,
task authoring or scientific trials. This is an infrastructure serialization
failure, not a GLM or scientific-task failure. Sanitized evidence is recorded in
campaign-001-result.json; original logs and the request ledger remain private.

Patch 0004 uses JSON-mode serialization for LiteLLM usage models. A regression
with the actual installed Usage class and nested reasoning-token details passed
(5.02 seconds, peak RSS 234,644 KiB). New launches render a separately hashed
campaign configuration with one of ten distinct replacement IDs. The bootstrap
will return bounded, hash-bound diagnostics through its own job log after export,
avoiding another recovery job solely because local S3 access is unavailable.
Oversized diagnostic files remain in S3 and are explicitly listed as skipped.

Verified the existing Hugging Face login identifies gonzalobenegas with a write
role. No dataset has been created or published. Credentials were not printed or
copied into source. Scientific validation and release integrity remain required.

Replacement 1 of 10 (campaign 002) was submitted once from commit 5ff327c, after
confirming that campaign 001 and the read-only recovery were terminal. Its rendered
configuration and all shipped inputs are hash-bound. The private submitter checks
prior job states before allowing each next campaign and rejects campaign numbers
outside 002–011. The local submitter peaked at 345,284 KiB while holding the shared
lock; it exited normally. A subsequent live observation reports campaign 002
RUNNING. No scientific validation or publication is claimed from that state.
The current authorization and consumed replacement slot are recorded in
campaign-registry.json; live job observations remain authoritative.


## 2026-10-10 UTC: first replacement rejected at design schema

Campaign `notebook-pilot-002` is terminal SUCCEEDED at the host level but
`generation_failed` scientifically: no task emitted, one `design_schema` skip.
The ledger records two HTTP-200 calls (compatibility and generation), not 80 used.
The real Daytona preflight passed both outbound-TCP negative controls against
positive host controls, confirmed the configured resources, and verified deletion.
There were no reference, verifier, probe or solver trials.

The export retained the model/error/request receipts, but bounded diagnostics
omitted candidate receipts. Expand the reusable diagnostic selector to include
those receipts, final quality revisions and task archives. Preserve file modes
in future export manifests so release integrity does not require guessing modes.
A short read-only recovery is charged as replacement slot 2 of 10 (campaign 003):
1 CPU, 1 GiB, at most five minutes, no models or Daytona creation. This uses less
than the approved per-campaign bounds and leaves eight replacement slots.


### Recovered diagnosis and bounded reasoning setting

The read-only replacement slot completed successfully; all selected bytes match
original export hashes. The model response has empty content, 9,000 completion
tokens, all 9,000 attributed to reasoning, and 8,937 prompt tokens. The saved
Pydantic error is EOF parsing empty JSON. This is output exhaustion, not evidence
against the seed's scientific suitability. No task has been manually repaired.

Set the approved service's documented `chat_template_kwargs.reasoning_effort`
to `low` at the inference adapter, recorded in frozen campaign configuration.
Apply consistently across the campaign's direct and solver calls. Keep output,
request, turn, runtime and resource ceilings unchanged. The generic adapter
rejects conflicting caller settings, records the digest of the actual forwarded
body, preserves messages, and defaults to unchanged forwarding when no template
settings are configured. This is an empirically motivated model configuration
change, not evidence that the service will guarantee nonempty output.

Three adapter regression cases passed (including unchanged behavior, provider
setting propagation, conflicting settings rejected without consuming requests,
and provider errors consuming their allowance); peak RSS 41,560 KiB, 2.35 s,
exit 0. Estimated working set <100 MiB; shared lock, one-worker and thread limits
used. Changed-file Ruff lint/format and diff whitespace checks passed. The
recovery submitter exited 0 with peak RSS 304,712 KiB and left no local worker.


### Replacement slot 3 submitted

Campaign `notebook-pilot-004` was submitted once from
`d485dba13fac34f53775d21d7e0ae7055c87b915`. Live status at 00:40:27 UTC is RUNNING;
no scientific outcome or request usage is available yet. Seven replacement slots
remain, after counting the read-only recovery as slot 2. The launcher verified
all previous handles terminal. Peak local submitter RSS 345,284 KiB, exit 0,
10.46 seconds; estimated <400 MiB, adequate headroom and shared lock held.
No local worker remains. Issue body and agent-generated label verified after
publishing the diagnosis and launch decision.


## 2026-10-10 UTC: multiline structured-output compatibility

Campaign 004 is terminal with `generation_failed`: the design passed, but the
initial builder and two repairs failed materialization. Five model requests were
used (one compatibility, four generation); no scientific trial was dispatched.
The first two builder replies contain placeholder Python. The final reply has no
linefeeds or escaped newlines, flattens Python and shell source into one line,
and contains a raw tab inside a JSON string. The design text also has `n` in
place of paragraph boundaries. Preserve those raw replies; do not infer or repair
missing source characters. The preflight passed and deletion was verified.

Hypothesis: JSON-schema constrained decoding is not reliable for code strings on
this service. Test JSON-object mode with the original schema retained verbatim in
an additional system message, followed by the same upstream Pydantic validation.
The optional inference adapter setting defaults to unchanged JSON-schema mode.
No output is rewritten, no scientific task patched, and no provider/model changed.
A second small compatibility request checks exact newline/tab/quote/backslash/
Unicode preservation before any Daytona call; both checks use the existing
four-request compatibility allowance. All other ceilings are unchanged.

Six adapter/pipeline cases passed, peak RSS 121,768 KiB, exit 0, 6.97 seconds.
The additional lost-newline case checks that evidence is saved and execution
stops before constructing the Daytona client. No cloud/model calls in tests.

A read-only full Daytona inventory at 00:42:17 UTC had no labels matching the
BioTasks/notebook name patterns. This is not proof of #18 cleanup: original
sandbox IDs are still required. Nothing was deleted or changed. The bounded local
reader peaked at 109,980 KiB, exit 0. Prepared a private recovery plan identifying
ten old seeds and twelve recorded native stage slots; no #18 job was launched.


### Replacement slot 4 submitted

Campaign `notebook-pilot-005` was submitted once from
`76b280fb053446763ff23a72b1d818c0a89a400a` after verifying all earlier handles
terminal. Six replacement slots remain. Local submission peak RSS 344,500 KiB,
exit 0, 10.79 seconds, shared lock/thread/priority limits applied; estimated
<400 MiB with adequate headroom. No local worker remains. Issue body and label
were fetched and verified after recording the evidence and new hypothesis.
The lost-newline stop-before-sandbox regression passed independently (peak RSS
117,980 KiB, 3.35 seconds, exit 0); changed-file Ruff checks passed.


## 2026-10-10 UTC: release provenance preparation

Saved the Scanpy LICENSE from the exact selected source revision, SHA256
`fb02749e4f251401f2c4023b7a30e71f40a21e138b87025036f74c980cfa63b2`.
The primary 10x PBMC3k dataset page still explicitly states CC BY 4.0.
`source-license-evidence.json` preserves the notice and attribution source for
future release evidence; no generated task file was modified and nothing has
been published to Hugging Face. A separate bounded read-only script and plan for
#18's old native manifests are prepared privately, not launched. Campaign 005
was confirmed RUNNING at 00:49:37 UTC on its existing handle.


## 2026-10-10 UTC: structured compatibility passed; verifier wrapper budget fixed

Campaign 005 is terminal FAILED due to factory configuration. Both compatibility
checks passed, including exact preservation of code-significant characters.
The second construction response materialized into an upstream task package;
no scientific trial was dispatched. `emit_draft` adds 30 seconds of wrapper time
to `test_timeout_sec`. Passing 120 therefore emitted a 150-second verifier,
correctly rejected by the adapter's 120-second ceiling. This was our configuration
error, not a biological defect and not a reason to alter a GLM-authored grader.

Set inner tests to 90 seconds so upstream emits the approved 120-second total.
Keep the guard, all resource limits and the 300-second solver limit unchanged.
Two wiring tests passed, including an actual upstream `emit_draft` fixture that
checks all emitted phase limits; peak RSS 118,520 KiB, 3.33 seconds, exit 0.
Changed-file Ruff lint/format checks passed. No task-specific artifact was edited.
Five raw requests were used (two compatibility, three generation), and the real
preflight sandbox was deleted with verification. No native trial claim exists.


### Replacement slot 5 submitted

Campaign `notebook-pilot-006` was submitted once from
`5eb1e505d4d189cf0e4ef246e2f303eb103fe2aa`; all prior handles were verified terminal.
Five replacement slots remain. Submission peak RSS 345,820 KiB, exit 0,
11.25 seconds, under the shared lock and one-thread/priority limits; estimated
<400 MiB with adequate headroom. No local worker remains. The updated issue body
and label were fetched and verified. No scientific result is available yet.


## 2026-10-10 UTC: native execution observed and old-evidence recovery prepared

At 01:01:34 UTC the read-only provider inventory contained a started sandbox for
the pilot task identity with a `repo2rlenv.job` ownership label. By 01:02:01 UTC,
read-back of that specific ID returned NotFound. This establishes native sandbox
activity and subsequent absence, not a scientific score or complete cleanup
proof. The host was confirmed RUNNING at 01:04:35 UTC; do not resubmit it.
The inventory/read-back used bounded local processes (peak RSS 109,888/104,732 KiB);
read-back exited 1 on NotFound, with no mutation attempted.

Added an experiment-only, plan-driven reader for existing native stage manifests
needed to close out #18. It reads selected diagnostics, checks original size/hash,
limits individual files and aggregate bytes, rejects unsafe paths, and returns
hash-bound chunks through job logs. It cannot generate tasks, call models or
mutate sandboxes. The private plan names ten existing seeds and twelve native
stage slots. No recovery job has been submitted for this helper.

Two recovery fixtures passed: unchanged original bytes recover and equal-length
tampering fails its original hash. Tests made no cloud calls; peak RSS 36,232 KiB,
0.48 seconds, exit 0, under shared-node lock/thread/priority limits with estimated
working set <100 MiB. Ruff lint/format and diff whitespace checks passed.


## 2026-10-10 UTC: quality rejection with working native execution

Campaign 006 reached generation controls and the shared quality loop. Its final
quality record is `needs_repair` after one repair, with baseline 0, oracle 1,
valid-alternative 1 and wrong-solution 1 reported. No solver attempt ran. The
wrong probe changed strict to non-strict bounds without changing observed outputs;
the installed wrong probe remains immutable under upstream policy. The quality
worker diagnosed equivalence; it did not authorize relaxing the verifier. The
valid NumPy alternative required a worker-authored parsing correction and then
passed. This is promising native evidence, not completion.

The separate fidelity response supplied abbreviated quotes, correctly rejected
by exact citation validation. The factory now records an unsupported review as
`supported=false` with validation error and preserved raw response rather than
losing the campaign outcome to an exception. Versioned generic quality guidance
asks GLM to select scientifically discriminating controls on actual fixed data;
it is appended to the original upstream system prompt through a small delegate
that retains upstream calls, schemas, budgets and receipts. Fidelity guidance
explicitly forbids ellipses/reconstructed JSON and requires meaningful wrong-answer
rejection evidence. No task, solution, grader or probe was manually edited.

Seven fidelity/wiring tests passed, including malformed JSON and unsupported
citations remaining unaccepted and saved without task changes; peak RSS
118,544 KiB, 3.39 seconds, exit 0. Shared lock and thread/priority limits applied,
estimated working set <200 MiB. Upstream installed-probe immutability is unchanged.

The old 1 MB diagnostic transport filled with generation records before final
results/ledgers. Prioritize final outcomes and cleanup/request receipts, and allow
4 MB of selected diagnostics. The original quality-result bytes were recovered
from the embedded JSON with their exact original SHA256 verified. Plan one
read-only combined recovery as replacement slot 6 (campaign 007), 1 CPU/1 GiB,
at most five minutes, no model calls/Daytona creation, leaving four slots.


## 2026-10-10 UTC: recovery and prior-resource audit complete

Read-only recovery 007 succeeded without model calls or sandbox creation. It
recovered the request ledger for campaign 006 (13 requests: compatibility 2,
generation 3, quality 8), all ten native cleanup-verified claims, and final native
result files whose hashes match the four quality TrialRecords. The quality
rejection is unchanged. Four replacement slots remain.

The prior #18 panel recovery verified all twelve native stage manifests: four
infrastructure failures and eight stages not runnable due to missing/unsafe
validation assets. Failed-build traces exposed four sandbox IDs not present in
the old ownership journals; one successful creation had an explicit deletion
receipt. Provider read-back at 01:19:19 UTC confirmed all five IDs absent. No
cleanup mutation or new #18 generation was needed. These failures are preserved
as infrastructure/unrunnable outcomes, not failed biological answers.

Campaign 008 submitted once from `1873ddde0a7099623ebf4cbdf8d88d9d9ded148b`,
using replacement slot 7. Three slots remain. The launcher checked all prior job
handles terminal. Local launch peak RSS 345,992 KiB, 10.87 seconds, exit 0;
shared lock, thread/priority limits and <400 MiB estimate applied.

## 2026-10-10 UTC: public-download verification prepared

Added a bounded download verifier around upstream `verify_release` and
`inspect_bundle`. It requires a publication commit, downloads release metadata
and the mode-preserving archive into a fresh directory, checks original hashes,
restores executable modes, and verifies each task's original bundle identity.
No upload or model execution is performed by this helper. Local transport
fixtures confirm that Hub-style loss of executable bits is repaired by the
archive and that corrupted archive bytes fail before extraction. Two tests
passed, peak RSS 57,620 KiB, 0.52 seconds, exit 0, shared lock and one-thread/
priority limits; estimated working set <100 MiB. The first invocation lacked
the experiment import path and failed test collection; rerun used explicit
PYTHONPATH. Lint and format checks passed after import sorting.


## 2026-10-10 UTC: campaign 008 cleanup race

Campaign 008 generated a task on its first build, using four requests total
(compatibility 2, generation 2). Generation nop/oracle controls completed with
cleanup verified. The first quality baseline then exited Harbor with code zero
but cleanup raised DaytonaNotFoundError, so the supervisor correctly left it
unaccepted and the pipeline stopped. At 01:27:05 UTC a fresh provider query of
that exact ownership label returned no resources. No deletion was needed.

A narrow reusable patch catches NotFound specifically during owned deletion,
then still checks the exact ID and the complete ownership listing. It does not
accept other errors, wrong ownership, remaining resources or uncertain creation.
The original failed receipt is preserved separately from later reconciliation.
Recovery now also selects root-level native trial files, so interrupted imports
do not hide their raw diagnostics. No task artifact has been manually changed.

Seven cleanup tests passed (peak RSS 111,952 KiB, 2.42 seconds, exit 0), including
NotFound followed by absent and still-present observations. Tests used the shared
lock and thread/priority limits, estimated working set <200 MiB. All five pinned
patches apply sequentially to original source and match the tested checkout;
the first minimal patch-check fixture omitted an affected file and was corrected
to derive the source list from all patch headers. Lint/format checks passed.

Campaign 009 submitted once from `7f93dea27d9c110a38686c7e69e65b7918561144`,
replacement slot 8, leaving two slots. Launcher peak RSS 344,808 KiB, 10.16
seconds, exit 0, shared lock/thread/priority restrictions applied.

## 2026-10-10 UTC: repository validation

Updated the CLI prompt-list regression for the three packaged notebook prompts;
legacy repository placeholders remain required for the two original templates.
All 14 repository tests pass, including installed distribution checks, using the
pinned uv through `uv run --locked`. The first invocation selected global uv and
lacked the build backend in its offline cache; it also found the stale two-prompt
expectation. Corrected run: peak RSS 46,136 KiB, 5.68 seconds, exit 0.

The experiment suite passed 31 checks; its two loopback-server tests were blocked
by the local socket sandbox and passed when rerun with that restriction removed.
No model/cloud calls occurred. Full experiment peak RSS 275,612 KiB; focused
rerun peak 118,376 KiB, 3.44 seconds, exit 0. All commands were serialized with
the shared lock, one-thread/priority limits and sufficient headroom. Required
pre-commit Ruff lint/format and ty checks passed (64,892 KiB, 0.37 seconds).


## 2026-10-10 UTC: valid solver evidence; bounded quality continuation

Campaign 009 used 11 requests and nine native trials. Quality controls were
no-op 0, oracle 1, wrong-solution 0 (skipped gene filtering), and independent
alternative 1. A blind GLM Terminus-2 attempt then earned reward 1 with no
exception, four API requests and the configured 300-second bound. The supervisor
subsequently failed cleanup because its final listing contained an ID whose
read-back was absent. A later exact-ID query and ownership listing both confirm
absence. Original failure and reconciliation are separately preserved.

Cleanup now independently re-reads IDs from the final listing, retaining stale
entries as evidence and rejecting any actually remaining resource. Tests cover
stale and live listings and unchanged ownership guards. Rather than discard
a working task, use upstream QualityLoop's existing baseline/oracle/rollout
imports and known-probe manifest. Local upstream import verifies all three
original Harbor checksums against the unchanged task. No scientific artifact
has been edited; old GLM probe definitions are preserved.

A hash-bound continuation archive contains 43 original/evidence files (31,292
compressed bytes). Prior requests, trials and solver/quality repair use reduce
the next allocation: seven native trials, one remaining solve, 22 quality
requests. Existing wrong probes remain immutable. The quality loop may rerun
probes and use its still-unused repair; it never regenerates the initial task.
This uses replacement slot 9 when launched, leaving one.

Thirteen focused continuation/cleanup/wiring tests passed (121,664 KiB peak,
3.55 seconds); the additional full continuation-branch fixture also passed with
the other two wiring tests (121,364 KiB, 4.25 seconds). Shared lock, single-thread
and priority limits applied, estimated working set <300 MiB. No live model or
cloud call occurred in tests. Pinned upstream Task.checksum emits a deprecation
warning; native imports still use that supported pinned interface.

Continuation 010 submitted once from `22b714178b392937b05157a2d42f5a5d156070c7`,
replacement slot 9. One remains. Iris observed PENDING at 01:49:18 UTC; no
resubmission. Launcher peak RSS 345,644 KiB, 11.89 seconds, exit 0, shared lock
and thread/priority limits. The task/evidence archive is included by SHA256 in
the frozen input manifest.


## 2026-10-10 UTC: quality usable; final bounded review/repair preparation

Continuation 010 finished with upstream `usable`, no quality repair, and five
requests (compatibility 2, quality 3). Both repeated probes passed their intended
controls (wrong 0, alternative 1), with verified cleanup. All five final native
result hashes match the report. The imported blind solver remains reward 1.
Fidelity was not supported: GLM again supplied a reconstructed JSON quote with
ellipses. Original failures remain failures.

The upstream review also noticed an undocumented ordering restriction but
waived it because one alternative passed. Operator inspection additionally
found root solver execution with a shared verifier and reference inputs protected
only by mode bits; this is not a demonstrated immutable reference boundary.
Generic versioned review guidance now treats these contract/integrity defects
explicitly, leaving actual fixes to the GLM quality worker. No task was edited.

Fidelity now requests numbered document ranges; the controller validates bounds
and resolves quotations itself from original lines. This eliminates paraphrased
quotations without turning model judgment into an executable reward. Invalid
ranges, missing documents and unsupported findings still fail.

The final continuation carries total prior use of 16 requests, 11 native trials,
one solver and zero quality repairs. Compatibility quota is exhausted and stays
disabled; no extra compatibility calls are authorized. Five native trials and
one solve remain. Existing completed probe receipts are restored unchanged and
checked through upstream `_read`, avoiding redundant controls before the one
remaining GLM repair. A dry import of the actual variants confirmed wrong 0 and
alternative 1 with installed probes and matching identities (41,108 KiB peak,
0.36 seconds). The 83-file continuation archive is 69,545 bytes.

Nineteen focused fidelity, budget, import and wiring tests passed, peak RSS
124,576 KiB, 8.29 seconds, exit 0, under the shared lock/thread/priority limits
and estimated <300 MiB. No cloud/model calls in tests.

The zero-compatibility continuation branch also passed with the three existing
wiring cases: four passed, peak RSS 121,340 KiB, 4.61 seconds, exit 0. Ruff lint/
format, ty and diff checks passed. Final input/probe receipts were checked with
actual pinned upstream import logic without executing scientific code locally.

Final continuation 011 submitted once from
`c0fdb34c159ababa9068a7c46bf810da17660a45`, replacement slot 10. No replacement
slots remain. Launcher peak RSS 346,644 KiB, 12.01 seconds, exit 0, shared lock
and thread/priority limits. No further campaign or retry is authorized.

Final repository validation after the citation and quota changes: all 15 tests
passed using pinned `uv run --locked` (peak RSS 47,392 KiB, 5.70 seconds, exit 0).
Required pre-commit Ruff lint/format and ty hooks passed (65,324 KiB, 0.40 seconds).
Shared lock, one-thread and priority limits applied; no owned local worker
remained. GitHub returned no CI runs for this research branch, so these are local
checks only. The issue text and agent-generated label were fetched and verified.
At 02:05:38 UTC continuation 011 was still RUNNING; no further submission.

### 2026-10-10 — Final approved continuation completed; release withheld

Campaign 011 finished SUCCEEDED. Its GLM-authored repair ran five fresh native
trials: no-op 0, oracle 1, wrong probe 0, valid alternative 1 and blind solver 1.
All five raw result hashes match their receipts; all trial and preflight cleanup
checks passed. Solver execution took 156.552134 seconds with eight API requests.
Sixteen new requests (quality 8, solver 8) bring the continuation chain to 32
requests and 16 native trials, including two solver attempts.

Upstream quality labels the task usable, but release remains withheld. The
repair compares two data copies that are both writable by the root solver;
there is no independent runtime input identity check. This is a static defect,
not a demonstrated exploit. Fidelity review identifies that failure, and its
line citations also exceed the validator's allowed spans. Its assessment is
therefore unsupported. Package/base-image pinning remains a reproducibility
limitation. No task was manually repaired and nothing was uploaded to the Hub.

All ten replacement slots are exhausted. No further remote/model execution is
authorized; issue 19 remains incomplete pending a decision on additional work.
See campaign-011-result.json for the final bundle identity and accounting.

### 2026-10-13 — Additional campaign authorized

The user approved the proposed single additional repair campaign. Campaign 012
has 40 new requests, five native trials plus one infrastructure preflight, one
five-minute/12-turn solve, one quality repair, two hours plus cleanup and a $5
Daytona ceiling. No further replacement is authorized. Cumulative ceilings minus
verified historical usage enforce those additional bounds; mismatched history
is rejected. The original task archive and five native results were imported
without task edits; both cached semantic controls pass upstream identity checks.

Five continuation tests passed. Four wiring tests initially hit sandbox loopback
socket restrictions; rerun with local socket access is recorded separately.
Preparation and cache verification used the shared lock, one-thread/priority
limits and <150 MiB peak working sets (41,684/40,420 KiB measured peaks).

All four wiring tests passed with loopback access (121,576 KiB peak RSS,
4.93 seconds, exit 0); no real model or sandbox calls. GitHub approval text and
agent-generated label were fetched and verified.

Campaign 012 submitted exactly once from `11cb1f0`. The launcher verified all
previous owned jobs terminal and discovered the approved model relay at launch.
Launcher exit 0, 23.74 seconds, peak RSS 345,720 KiB; shared lock and thread/
priority limits applied. Local Ruff/format/ty hooks passed before checkpoint.
No further campaign is authorized. Submission is not validation or publication.

Campaign 012 ended FAILED after seven quality calls and three native trials.
GLM retained the checksum-pinned archive and added a private verifier identity
check before reference computation. Fresh no-op 0, oracle 1 and wrong-analysis
probe 0 have native results without exceptions. Cleanup of the third trial raised
DaytonaConflictError after Harbor returned 0, preventing further steps. The
original failed receipt is preserved. A fresh exact ownership-label listing
at 2026-10-13 14:48:24 UTC was empty; an exact sandbox ID was not recorded by
the failed cleanup, so no exact-ID reconciliation is claimed.

A sixth narrow adapter patch catches deletion conflict and requires independent
ID and label absence checks; live or unknown resources still fail cleanup.
No new remote worker or model call has been launched. Remaining allowance is
33 calls (quality 9, solver 24), two native trials, one solve and zero repairs.
A recovery worker would require approval under the single-submission policy.

All ten cleanup tests passed, including conflict with both absent and live
resources (112,244 KiB peak RSS, 2.14 seconds, exit 0). All six hash-pinned
patches apply in sequence to the original source; patched cleanup matches the
tested implementation. No generated task changed during this diagnosis.

### 2026-10-13 — Recovery and aggregate budget approved

The user approved one recovery worker within the remaining campaign limits,
then set an aggregate $100 budget for issue completion and authorized routine
recovery/retries without repeated approval. Preserve per-run request/time, CPU,
GLM-only and factory-only constraints. Historical campaign ceilings conservatively
bound original plus replacements plus campaign 012 at $56 before credits; this
is an upper bound, not an invoice. Recovery is charged within campaign 012's
existing $5 ceiling, carrying all prior reservations. Future runs must keep the
aggregate ceiling and record distinct reservations before launch.

Recovery inputs preserve the original generated task and raw native results.
Upstream imports the completed wrong probe with checksum and installed-marker
checks, using separate cleanup reconciliation; no failed receipt is rewritten.
Baseline/oracle are imported, rollout is absent and must run fresh. The recovery
configuration leaves 33 calls, two native trials and zero repairs, and retains
the original campaign absolute deadline. Original results stay archived.

Nineteen focused continuation/wiring/cleanup checks passed (121,696 KiB peak,
4.72 seconds); the added raw-probe regression also passed in the six-case
continuation suite (54,000 KiB peak). Actual saved-evidence import verified the
wrong probe without execution and rejected changed task content. Imports used
42 checksum/mode-bound files, with no generated task edits.

Recovery worker 013 submitted once from `80c6350`, after verifying prior jobs
terminal. Launcher peak RSS 345,952 KiB, 14.21 seconds, exit 0, with shared lock
and one-thread/priority controls. It continues campaign 012, not a fresh repair
or generation campaign. The original two-hour deadline remains enforced.

Recovery 013 completed SUCCEEDED: new alternative and solver both reward 1,
with all completed controls (no-op 0/reference 1/wrong 0/alternative 1/solver 1)
hash verified. It used seven calls: quality 4 and solver 3. Cleanup passed.
Fidelity again exceeded the nine-line citation limit; original response remains
unsupported. Operator audit also found an example annotation field treated as
mandatory and unspecified ordering asserted by the grader. These are remaining
public-contract defects despite upstream review passing.

The citation schema now selects individual numbered lines, making overlong
ranges unrepresentable; it still rejects unknown documents/lines and retains
raw responses. General quality/fidelity guidance explicitly distinguishes
example fields from mandatory schemas and reference order from public contract.
No task was manually edited. Twelve fidelity/import tests passed (54,096 KiB
peak, 0.66 seconds, exit 0).

Campaign 014 reserves $5 within the aggregate $100 (conservative total reserved
$61). It has 40 new calls, one GLM repair, five native trials, one five-minute
solve and two hours plus cleanup. Historical usage stays recorded; completed
controls import without rerun until GLM changes the task.

Campaign 014 submitted once from `2e0bd6e`; prior jobs verified terminal.
Launcher exit 0, 22.09 seconds, 346,720 KiB peak RSS, with lock/thread/priority
controls. Issue decision log fetched and verified after update.

Final ordinary repository suite: 15 passed (5.73 seconds, 46,860 KiB peak RSS,
exit 0). Local validation only; no CI claim or model/cloud calls in tests.

Campaign 014 completed its quality/review path with five quality calls and no
new native trials or repairs. Single-line citations validated successfully.
Scientific review correctly failed public_contract for unstated identifier
ordering, but upstream quality had classified it as optional and skipped repair.
This exposed a workflow gap: scientific rejection was only a release gate.

A small adapter now carries a validated GLM fail finding into upstream repair
as blocking only for that exact bundle, retaining original assessments and
recording the combined review separately. Quotes are resolved from original
GLM-selected lines and checked against current files. No task text or scientific
judgment is authored by the adapter. On a changed task the old finding does not
apply; a fresh scientific review still decides release eligibility.

Continuation 015 uses campaign 014's remaining 35 requests, five native trials,
one repair and one solve, retaining its deadline and prior cost holds. No extra
$5 reservation. Seven focused feedback/fidelity tests passed (50,620 KiB peak,
0.53 seconds, exit 0).

Continuation 015 submitted once from `9ac75d6`. Launcher peak RSS 346,456 KiB,
16.69 seconds, exit 0; shared lock and thread/priority controls. Issue update
read back and verified. No new monetary reservation for this continuation.

Continuation 015 failed after one quality call and no scientific trials because
the new adapter incorrectly treated upstream _review's (review, context) return
as a review object. Preflight cleanup passed. Raw exports were recovered from
the terminal job log; original evidence remains intact. Corrected tuple handling
and the mocked regression to match the upstream interface. Continuation 016
carries the consumed call and cumulative cost reservations, leaving 34 calls
and the same five trials/one repair/one solve under the original deadline.

Continuation 016 submitted once from `1cc596a`; launcher exit 0, 14.19 seconds,
344,988 KiB peak RSS. Corrected regression passed; local hooks passed.

Continuation 016 completed with all five native rewards as expected, a fresh
successful solve, one GLM repair and nine calls (quality 6, solver 3). Scientific
review validated and passed. Operator release audit nevertheless found the
remaining optional-example versus required-key mismatch; the broad review missed
it. Upstream labeled export also failed to locate probe provenance at its
temporary execution path, despite intact native evidence. Do not conflate
quality status or review acceptance with full release readiness.

Added a focused GLM schema audit over a mechanically extracted inventory of
literal keyed accesses. The model must classify every expression, distinguish
private bookkeeping from submission fields, cite evidence, and propose repairs
for mandatory keys absent or optional publicly. Controller enforces coverage
and exact citations; GLM supplies the scientific judgments and all repairs.
This addresses a general pattern, with no notebook-specific task edits.

Campaign 017 reserves $5 (aggregate conservative reservations $66 of $100),
with 48 new calls (quality 24 including the extra audit stage, solver 24), one
repair, five native trials, one five-minute solve and two hours plus cleanup.
Two focused schema/feedback tests passed, 49,892 KiB peak, 0.51 seconds, exit 0.

### 2026-10-13: preflight timeout and bounded recovery

Campaign 017 failed in the Daytona network probe before any model call or native task trial. Original evidence confirms deletion of its sandbox. Its ledger holds $0.088 conservatively. The 15-second command deadline included daemon startup, DNS resolution and two three-second socket probes. Increase only the command deadline to 60 seconds; timeouts still fail closed with no automatic retry. Four focused preflight tests passed (0.40 seconds, peak 52,520 KiB), including timeout cleanup. An initial test invocation lacked the experiment import path and failed collection; corrected PYTHONPATH passed.

Recovery 018 retains the original absolute deadline, carries the $0.088 hold, and shares the existing $5 reservation. No extra calls, repairs, solves or aggregate spending allowance: still $66 conservatively reserved of $100.

### 2026-10-13: local release-label evidence reconstruction

Recovery 018 submitted from 8a871a9 and observed RUNNING. Separately exercised upstream label_from_quality/write_labeled_copy on a disposable copy of campaign 016 evidence. Reconstructed GLM probes using upstream probe_variant, verified both semantic bundle identities and original Harbor physical checksums, and left raw trial result bytes unchanged. A derived quality report changes only local file paths. Upstream produced a verified label with unchanged executable task identity. This resolves the temporary-worker-path export problem without another scientific run or manual task edits; campaign 016 remains ineligible for publication because of the known contract mismatch. Local check passed in 0.36 seconds, peak 40,180 KiB.

### 2026-10-13: validated release and fresh download

Recovery 018 completed successfully from 8a871a9: 13 model calls (11 quality, 2 solver), one GLM repair, five native trials. Reference/empty/wrong/alternative/solver rewards were 1/0/0/1/1. The solver completed in 77.598634 seconds. All owned preflight/trial cleanup receipts verify deletion. Offline preflight confirmed both host destinations reachable and both sandbox destinations blocked. GLM made the mitochondrial annotation name explicit; identifier alignment, observed-data SHA anchor and software-alternative acceptance remain intact. Scientific review passed with valid evidence citations.

Used upstream release staging, verification and publication. Public destination: https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19 . Immutable upload commit 5231e1ac828101c04707a905a47be7a553f23928; later registry commit 3e9aca9c69260afbc4442ad3b3ecad8eb91e2610. Anonymous metadata confirms public visibility. Fresh forced download verified every released file hash and executable mode plus the final task identity. Receipts are in release-evidence/. Staged 25 files passed exact GLM/HF credential and private-marker checks, including archive contents.

Limitations remain explicit in the release: one notebook is not benchmark/generalization evidence; GLM fidelity review is not independent biological execution; no broad adversarial security audit; dependencies/base image are unpinned; PBMC3k shares a donor with PBMC6k. Upstream recipe metadata names e4715b0 while actual dependency execution used pinned 5555443 plus recorded patches; disclosed rather than changing historical task metadata. Aggregate conservative reservation remains $66 of $100, not an actual invoice. No further campaign is needed.

### 2026-10-13: independent post-release review

An independently requested reviewer confirmed all 24 release-file hashes/modes and five native result hashes, but found a scientific false acceptance: coercing submitted detected-gene counts to integers before comparing can admit fractional metadata. This is a static finding, not a newly executed biological trial. The published native results remain unchanged; acceptance of those controls does not cover this metadata mutation. Additional generic GLM review guidance now requires validation before lossy coercion; any task repair must still come from GLM.

The review also found traversal risk in local label reconstruction and unbounded archive metadata expansion. Local helpers now reject traversal/symlink escapes, use explicit integrity exceptions, bound tar headers/metadata/expansion, validate expected archive directories and stream extraction only after validation. Eight focused tests pass (0.67 seconds, 61,140 KiB peak). These are research-branch fixes, not a promoted PR.

A static explorer now exposes captured notebook text, task files, exact authoring
and quality call prompts/responses, eight selected control/solver records, and
current review caveats. It follows the previous issue's standalone HTML approach
and links Harbor Visualiser. Five tabs and all selectors passed browser checks at
desktop/mobile widths (1.22 seconds, peak process RSS 101,624 KiB). An initial
single-process browser launch failed; a one-renderer launch exposed mobile text
overflow, fixed before the passing check. Private-marker and exact credential
scans passed. Original source licenses are included in the page.

Campaign 019 is a fresh bounded post-review repair: one GLM repair, five native
trials, one five-minute solver attempt, at most 24 quality and 24 solver requests,
two hours plus cleanup. Reserve another $5, bringing conservative aggregate
reservations to $71 of $100. Preserve the original public release and recorded
trials; supersede only after GLM repair and fresh validation. Generic review
prompts now explicitly inspect value-changing coercion in scientific metadata.

The same independent reviewer rechecked infrastructure fixes at 0868488 and found
no actionable residual issue; their independent run also passed all eight focused
tests. Original campaign-018 evidence successfully reconstructed with the hardened
helper, and the saved release passed the hardened downloader in a fresh local
directory (not a second network download). Campaign 019 submitted from 0868488.

Public HTMLPreview testing initially exposed its attempt to execute JSON script
blocks. Store the data in an inert hidden element with escaped HTML-sensitive
characters instead (6efd741). Public desktop/mobile navigation then passed with
no JavaScript errors: 1.81 seconds, peak process RSS 106,336 KiB. The committed
browser check can exercise the local page or an explicit public URL.

Campaign 019 completed operationally but quality remained needs_evidence: GLM
omitted one literal key from the schema inventory, so the review was rejected.
Four quality calls, no task repair, no native trials; preflight cleanup verified.
The broad review also failed to identify the independently reported coercion.
Added a focused GLM audit of generic AST conversion operations, with exact source
lines attached to model findings. Unknown/false-acceptance findings block release.
Schema review gets one bounded retry for structural inventory incompleteness.
Three focused audit/feedback tests pass (0.46 seconds, peak 50,220 KiB).

Recovery 020 retains campaign 019's absolute deadline and $5 reservation, carrying
$0.088 conservative holds and four used requests. Remaining: 20 quality calls,
24 solver calls, one repair, five trials, one solver attempt. No task-specific
manual repair was introduced; the operation inventory and prompts are generic.

### 2026-10-13: fractional metadata repaired; audit classification corrected

Recovery 020 used 16 quality calls and one GLM repair. The new verifier checks
integrality before converting detected-gene counts. Reference, empty baseline,
wrong-output and valid-alternative controls passed (1/0/0/1); no new solver ran.
The factory incorrectly turned two explicitly not_applicable private-verifier
settings into public-schema blockers. Corrected the generic predicate to flag
only optional/absent public fields, with a regression check. Two focused tests
pass (0.44 seconds, 49,332 KiB peak).

Boolean truthiness still does not enforce original Boolean metadata, despite a
positive GLM coercion assessment. Expanded generic audit guidance to distinguish
original-value validation from validation after casting; no task was manually
changed. Campaign 021 reserves a fresh $5 ($76 aggregate conservative reservations
of $100), with one repair, five native trials, one five-minute solver, 24 quality
and 24 solver requests, two hours plus cleanup. The prior corrected counts task
and four native controls are preserved as continuation evidence; no solver result
from an older bundle is imported for the new task.

### 2026-10-13: bounded citation recovery

Campaign 021 identified the Boolean false acceptance through the focused GLM
audit, but a subsequent schema audit quote omitted Markdown formatting and
failed exact citation validation. Seven quality calls, no repairs or new native
trials. Extend the existing single bounded schema retry to citation failures,
without accepting unsupported evidence. Two focused tests pass, including failure
on two invalid citations. Recovery 022 carries the original deadline, $0.088 holds
and seven used calls: 17 quality and 24 solver requests remain; one repair, five
native trials, one five-minute solver. No additional $5 reservation; aggregate $76.

### 2026-10-13: reviewed repairs published; explorer follows issue 17

Recovery 022 completed with 17 quality calls, seven solver calls, one GLM repair
and five fresh native trials. Rewards: baseline 0, reference 1, wrong 0, alternate
1, blind solver 1 (70.24 seconds). Fidelity review is supported with valid
citations. All five sandbox cleanups were verified. Independent static re-review
found the count-integrality and nonbinary-flag defects addressed, with no new
blocking regression. Numeric 0/1 flags remain accepted; this is not strict dtype
enforcement. Dedicated mutation trials for these two defects were not run.

The replacement release is public at immutable HF commit
353e8a296c4101d3c0647e4c50e2b0ed7214d5de; registry head is
474c8fe7aedd35ca3731b7a469de1d5bbd2fa238. A forced fresh download passed file
hashes, executable modes, release validation and bundle identity. The original
release is preserved. Aggregate conservative reservations remain $76 of $100,
not an invoice. No further campaign is needed for this pilot.

At the user's request, reuse issue 17's explorer layout and artifact-card styles,
replacing its generation approaches with this pipeline. Show clickable stages,
recorded prompts, cell-rendered notebook, current task, historical/current attempts
and explicit review/release status. The old immutable HTML remains historical;
a new commit permalink identifies the corrected explorer.

### 2026-10-13: resource-based compute policy

User removed the categorical model-training exclusion: scientific workflows are
allowed when they fit CPU-only execution and the configured resource/time budget.
Patch 0007 removes the inherited SETA prohibition and fixed resource wording from
both authoring prompts. The controller now renders allocations from configuration.
The completed pilot used the deliberately smaller upstream-default allocation
(1 CPU, 2 GiB, 10 GiB), not a measured Daytona provider maximum. No new execution
or changed scientific validation is claimed. Historical calls remain verbatim;
the explorer labels their superseded compute wording.

### 2026-10-13: newer notebook; worker-owned task selection

User selected Scanpy's newer clustering.ipynb and rejected manually specified
task scope. Pin source revision 8c1463d5d97272d5811ad3f4efb57483e23b4c7e,
SHA256 9716c6e512d26225b0c6269b49ee01399211ab60b96d523182d66592021000a6.
The full source-only seed includes marker analysis. Keep notebook/data provenance
separate from task design; no analysis_scope is supplied. The design worker
chooses and justifies its objective and scope within the general budget.
Figshare version 1 metadata identifies two real input files and CC BY 4.0;
provider MD5s are recorded, not claimed as verified downloads. Old pilot
provenance is preserved under seeds/legacy-pbmc3k. No model run or viewer edit.

### 2026-10-13: design-only iterations and upstream intake assessment

Reviews 004–013 contain six design and four critique calls using the unchanged
newer notebook. General prompts, reasoning settings and output budgets were
varied; this adaptive series is not a controlled performance comparison. Higher
budgets resolved some incomplete responses, but scientific-contract errors
persisted. Draft 013 passes JSON validation and fails static design review;
label-permutation controls contradict the public equivalence rule, and a graph
degree bound is unsupported. Original outputs are preserved; no generated task
was manually repaired. No construction, native validation, solver or viewer edit.

At the user's suggestion, inspected Tasksmith and original SETA. The original
SETA notebook adapter consumes prepared data manifests and uses a tool-enabled
idea agent, whereas the selected Repo2RLEnv adaptation makes one tool-free call.
Tasksmith's schema-parametric artifact stage is a promising reuse point already
present in our pinned upstream revision. Its existing runtime paths do not
support the approved GLM endpoint without an adapter; its PR-specific bootstrap
and oracle cannot simply be applied to notebooks.

Further text-only iterations stop pending the design discussion. The proposed
minimal change is factual intake plus bounded inspection within one GLM design
stage, keeping the existing design output and later SETA/quality/release path.
Measured facts must not prescribe the task. [Reuse assessment and alternatives](design-intake-reuse.md)
record exact sources, integration gaps and proposed evaluation criteria. This is
static research, not an implemented architecture or new model/sandbox run.

### 2026-10-13: prepared factual intake and tool-enabled design stage

After the user's agreement, prepared the adapter, intake and actual canonical
prompt for review. Reuse Tasksmith's artifact controller through patch 0009,
injecting a GLM Chat Completions runtime while retaining SETA's TaskDesign schema.
GLM owns task selection, inspection commands and revisions. Deterministic intake
records source hashes and bounded structural facts, not task-specific methods.
Unknown formats and unmeasured biological semantics remain unknown. No new
biological data were downloaded and no live model or remote workspace ran.

The old direct-call campaign refuses the new tool-enabled prompt before model
or sandbox activity. The standalone integration only saves a design for review.
It preserves complete requests/responses and incomplete-operation evidence,
counts uncertain requests, disables transport retries, and reserves the final
two calls for submission/revision. Tool commands execute through a prepared
remote worker with cumulative and per-command time bounds. Workspace isolation,
real-data staging, remote accounting/cleanup and live tool-call compatibility
remain launch prerequisites; this preparation does not claim to implement them.

Validation used the locked root and pinned upstream environments, serialized
under the shared-node resource guard. The first integration check exposed the
upstream monetary ledger's rejection of a zero reservation; the adapter now
reserves its smallest unit and settles to zero on a completed free-service
response. Sixteen upstream artifact-stage regressions passed. The five final
design-stage integration tests passed (1.02 seconds, 86,956 KiB peak RSS),
including invalid-submit/revision, committed-artifact reuse, SDK mock transport,
remote-only commands, uncertain-tool accounting and incomplete-response retention.
Five campaign-wiring checks passed in the affected nine-test run (4.79 seconds,
140,920 KiB peak). Two native HDF5 checks passed on tiny synthetic fixtures
(0.27 seconds, 67,400 KiB peak); no full matrix was loaded. Root tests had 25
passes plus an offline build-backend cache failure; after populating that pinned
cache, the remaining distribution test passed (2.15 seconds, 32,024 KiB peak).
Ruff lint/format and ty passed. These are software checks, not scientific evidence
or live endpoint validation.

The [updated assessment](design-intake-reuse.md) records the concrete reuse,
prepared boundaries, proposed finite design budget and remaining launch work.
Stop before execution for prompt review. Construction, solver, release and viewer
remain untouched; the prior published task and original model outputs are preserved.

### 2026-10-14: artifact-reproduction proposal and issue reconciliation

The user agreed to a source-execution approach: one notebook becomes one task
covering every scientific branch, using its original inputs and deterministically
converted plain scripts. The complete reference may take ten minutes; total
solver time remains a separate decision. Added input reductions and new starting
checkpoints are deferred. Plot endpoints use their underlying scientific data;
variable results need executable checks that accept valid variation and reject
meaningful errors. Unusable sources may be rejected with the reason preserved.

The [full proposal](artifact-reproduction-draft.md) records programmatic versus
GLM responsibilities, setup/repair boundaries, grading controls and proposed
finite budgets. An [independent review and author response](artifact-reproduction-review-001.md)
records design findings and subsequent decisions; this is not implementation or
execution validation.

The user clarified that issue #19 had been closed prematurely and authorized
integrating the agreed draft into that same issue. It has been reopened. The
[previous issue body and decision log](issue-19-history-2026-10-14.md) are preserved
verbatim before replacing the published plan. Snapshot SHA-256:
`d27bf3e9dc1646fef89363c2817d62e63c6f9cad0fe84b239b0c75808107c812`.
Completion and pending statements in that snapshot describe earlier checkpoints.
The current update preserves the previous release as evidence and keeps the
revised workflow open. No new model, sandbox, solver or viewer work ran.

### 2026-10-14: first artifact-reference implementation checkpoint

Implemented the initial reference gate described in
[reference-execution.md](reference-execution.md). The reusable converter uses
Jupytext 1.19.6, rejects unsupported execution features, and verifies the ordered
Python syntax tree. The selected newer Scanpy source exported all 35 code cells
without changing their statements. The source's MyST documentation execution
setting is preserved in the receipt; no notebook kernel or cell markers are
required. Other source languages remain explicitly unsupported by this first
conversion profile.

Preparation and independent review use version-controlled GLM prompts and the
existing upstream Tasksmith artifact controller, request accounting and protected
Iris model client. Task-specific setup, offline input substitutions and exports
must come from GLM. The controller stages/checksums the original data, preserves
the untouched conversion and generated diff, enforces offline reference execution,
records artifacts and resource evidence, and uses existing durable export and
owned-resource cleanup. It does not invoke construction, graders, solvers,
publication or the viewer.

The first run configuration has 4 CPUs, 8 GiB RAM, 10 GiB disk, 600 seconds for
the complete computation, 1,800 cumulative setup seconds, two repair passes,
45 maximum GLM requests, and two hours plus cleanup. Reserved $5 within the
standing $100 authorization; aggregate conservative reservations are now $81,
leaving $19 unallocated. This is not a provider invoice. No new paid run had
started at this checkpoint.

Validation: nine conversion regressions and six reference-protocol/upstream
stage tests passed. The full root suite passed 31 cases; four loopback tests
were blocked by the local filesystem/network sandbox and passed when rerun with
loopback access (six cases in that file). Ruff, formatting, ty and pre-commit
passed. Tests used synthetic fixtures and scripted model responses; the source
conversion is static evidence, not scientific execution. The largest measured
local test peak was 130,800 KiB under the shared-node guard.

### 2026-10-14: first reference run and bounded infrastructure recovery

Campaign `artifact-reference-001` used checkpoint `9ff57fb9a9cf181ab18868a18b3c957a14650010`.
Both original data files downloaded and passed the source checksums in five
seconds. The sandbox reported the requested 4 CPUs, 8 GiB RAM and 10 GiB disk.
The first GLM preparation response ended at 24,000 output tokens, including
21,453 reasoning tokens. No partial tool was executed, so no generated setup
or scientific computation ran. This does not show that the source is broken.

Early durable export selected the upstream environment, which lacks the host's
S3 client. Final export in the host environment succeeded, then diagnostic
printing exposed a missing helper in the frozen payload. A read-only recovery
worker restored the original hash-verified records. Owned sandbox deletion was
verified. [Selected records and the original archive manifest](reference-runs/001/summary.json)
preserve this outcome; full model evidence remains in the private campaign archive.

The replacement uses the provisioned host Python for storage export, freezes the
diagnostic helper, and records commands before dispatch and their returned
outputs. It checks the complete expected network-probe result. GLM receives a
32,000-token output allowance with medium reasoning. Only definite received
token-limit responses enter upstream's one bounded recovery; partial tools never
execute, and transport uncertainty remains terminal. The source and scientific
prompts are unchanged. Seventeen focused adapter/reference regressions passed
with a 132,472 KiB peak. Campaign `artifact-reference-002` reserves another $5;
conservative reservations total $86, with $14 unallocated and actual charges
unknown. This stays within the standing $100 authorization without a new request.

### 2026-10-14: review protocol clarification and current reasoning field

Campaign `artifact-reference-002` at `2b08f2742b6f4631c6720b151598e30bbe160206`
made twelve GLM requests. The first preparation exhausted its output limit;
upstream's bounded recovery then produced a plan after structural revisions.
Independent review identified an online registry lookup left in the offline
script. GLM repaired input staging in a second preparation pass. The next review
repeatedly submitted approval with positive statements in `scientific_changes`,
which the schema treats as a defect list, and exhausted its three-call allowance.
No setup or scientific computation ran. The corrected durable export and owned
sandbox cleanup both succeeded. [Plans, diffs, reviews and request counts](reference-runs/002/summary.json)
are retained as unedited, unexecuted worker outputs.

The next factory revision names the field `prohibited_scientific_changes`,
describes all defect lists explicitly, and returns an actionable validation
error. It does not clear entries or accept a failed review programmatically.
Preparation instructions clarify fresh-stage submission and JSON arrays. Both
prompts distinguish scientific endpoint data from rendered images, repeated
displays and intermediate objects. Source plots and all analysis calls remain
preserved; only added figure-capture infrastructure is excluded.

The saved provider responses use `reasoning`, which the adapter did not carry
forward. [Current vLLM documentation](https://docs.vllm.ai/en/stable/features/reasoning_outputs/)
documents the field rename. The adapter now retains either provider field name
with regression coverage. Replaying request assembly on the saved records shows
one three-turn review would grow to 280,254 bytes when reasoning is preserved,
so the explicit input-byte bound increases from 256,000 to 512,000 without silent
truncation. This does not claim a model context size or increase request counts.

Campaign `artifact-reference-003` retains the resource, time, repair and
45-request ceilings and reserves $5. Conservative aggregate reservations are
$91, with $9 unallocated and actual provider charges unverified. No generated
plan, source method or review result was manually repaired.

Validation of this replacement: nineteen focused adapter/reference regressions
passed, with a 133,028 KiB peak. Ruff, formatting and type checks passed.

### 2026-10-14: complete offline source execution

Campaign `artifact-reference-003` ran checkpoint
`f7b3c3aa2410f189b19929947967c5045037fae7`. Its final reviewed script completed
in 136.55 seconds on 4 CPUs and 8 GiB RAM, from the two original count matrices.
All source analysis calls, including clustering, annotation and marker-gene
analysis, remained in the executed script. The initial setup used Bash
`pipefail` under the configured POSIX shell; GLM repaired that mismatch. The
first scientific execution then stopped after 17.50 seconds because an optional
Scrublet dependency was missing. GLM added it in the second permitted repair.
These were setup failures, not evidence of a broken source analysis. Each plan
received a separate GLM review before execution. Seven raw requests were used,
including one bounded recovery from an output-token limit. The running
scientific process made no model calls.

[Unedited plans, scripts, diffs, reviews and execution records](reference-runs/003/summary.json)
preserve all three passes. The final eight artifacts were nonempty and totaled
526,734,122 bytes, including a 476,434,974-byte full AnnData state. All outputs
were downloaded, hashed, durably archived and downloaded again for verification
before sandbox deletion. Original input hashes remained unchanged. The final
cleanup check found no owned sandboxes. No further campaign was launched.

The 5,022,300 KiB maximum child RSS is not aggregate sandbox memory. Successful
computation started in a new process and empty working/output directories, but
reused the environment and caches from the failed attempts. The 136.55-second
measurement therefore does not establish cold-environment reproducibility.
Semantic artifact fidelity, observed schemas, plot-statistic coverage and
portable comparisons remain unvalidated. The full AnnData export is evidence;
it does not freeze a solver-facing format or require reproducing every
intermediate matrix. Task construction, grading, blind solving, release and
viewer changes remain outside this milestone. Issue #19 stays open.

The user asked which stages require a model. Conversion, declared-input staging,
dependency installation, bounded execution and evidence collection are
programmatic. GLM prepares setup and exports, reviews them separately and makes
permitted repairs when necessary. Later task construction and blind solving
will use GLM; deterministic code will still supply the reward. Standing
reservations remain $91 of the authorized $100, not measured charges. Remaining
Daytona credits and actual billing have not been verified.

### 2026-10-14: saved-artifact inspection and endpoint coverage checkpoint

The user authorized proceeding to the next step. Added a bounded structural
inspection stage over the successful reference archive, followed by a GLM
endpoint proposal and separate GLM completeness/evidence review. The factory
does not manually choose task-specific endpoints, write comparisons, alter
reference files or rerun the analysis. The two prompts are version-controlled
and distinguish observed facts from prior claims and unverified derivations.

The inspection preserves source hashes and streams tables instead of loading
the full scientific dataset. HDF5 inspection records shapes and encodings with
bounded previews; it does not follow external links or load analysis matrices.
Reference storage and eventual solver-facing representations are separate
decisions. A large retained state need not become a mandatory submission format.
Scientific endpoint omissions still block approval.

[Execution scope and limits](coverage-execution.md) allocate nine additional
GLM requests, keeping the successful reference's seven in the eighty-request
pipeline total. One reserved Iris CPU worker performs retrieval, inspection and
model calls. No Daytona sandbox or additional Daytona budget is used. The stage
ends at an endpoint proposal/review or a documented request for further work;
it cannot claim grader readiness. Thirty-one focused inspection, provenance,
coverage, reference and adapter tests passed with a 159,236 KiB peak RSS.

The five prompt/installed-distribution checks also passed, as did repository
quality hooks. Subsequent changes require exact observed evidence locations in
worker citations and preserve cumulative request-slot accounting in the result.
Their final targeted check was prevented by another task holding the shared
heavy-work lock. The command aborted without starting tests; no remote coverage
job has been submitted. The prepared checkpoint remains unexecuted until that
check and resource gates can pass. Other tasks were not interrupted.

The user then explicitly authorized proceeding without the shared lock for this
light work. The final twelve coverage tests and targeted Ruff lint/format checks
passed in 1.02 seconds, peaking at 103,588 KiB. Load and memory gates, single-worker
execution, thread limits and low priority remain in force; the exception is
limited to these light checks and the remote submission/status client. Biological
artifact inspection stays on the reserved Iris worker. No source or generated
artifact was changed, and the nine-request coverage allowance is unchanged.

### 2026-10-14: structural inspection succeeded; bounded coverage continuation

Coverage pass 001 at `8ab7966` inspected all eight saved artifacts in 11.10 seconds
and verified their original hashes before and after inspection. Both GLM responses
reached the 32,000-token limit. The controller correctly rejected them; no endpoint
proposal was accepted and the independent review did not run. Original profiles
and outcomes are preserved in `coverage-runs/001/`; full requests and responses
remain in the private campaign archive. This is a model-output failure, not a
failed reference computation or an endpoint-quality conclusion.

The continuation retains the same evidence and requirements, asks for concise
structured output, and uses low reasoning effort. It carries both consumed request
slots forward and permits only four proposal plus three review requests, keeping
the combined coverage maximum at nine and reference-plus-coverage maximum at
sixteen. No truncated action is accepted, no scientific output is manually repaired,
and no source rerun, construction, solver or Daytona work is added.

### 2026-10-14: reviewable map of the early pipeline

Added `pipeline-map/index.html`, a standalone diagram with one selected stage
at a time, explicit inputs/outputs, and verbatim expandable prompt templates.
It covers reference conversion, preparation, review and execution, then structural
inspection, endpoint creation, checks, optional repair and independent review.
The map distinguishes current input wiring from the agreed but unapplied simplified
call sequence. The user agreed to medium reasoning, no extra per-response token
cap beyond context capacity, and removal of the extra request/response byte caps.
Word-count guidance is still awaiting review. No pipeline execution was launched
and the earlier explorer was not changed. Browser checks exercised all nine steps,
verbatim prompt display, hash navigation and mobile width without JavaScript errors.

The user requested actual per-stage input/output artifacts for the specific
notebook. The map now opens on the rendered original cells beside the complete
converted Python script. It embeds the final reference preparation/review inputs,
plans, setup/script/diff, execution records, observed file profiles and incomplete
coverage outcome. Newly included input records were byte-verified against original
archive manifests. The recorded endpoint prompt is distinguished from the current
template. No accepted endpoint proposal, validation, new repair or coverage-review
output is invented. Full biological files remain remote; per-column examples are
not represented as aligned table rows. Browser checks exercised every file selector,
all nine stages, exact converted script/prompt display and mobile layout.

Added offline syntax highlighting for Python, shell, JSON, diffs, notebook cells
and prompt Markdown using the already locked Pygments dependency at HTML build
time. Nested code fields retain their language highlighting. Browser checks
confirmed converted source, notebook text and prompts remain text-identical.

Corrected step 01 to display the exact original `clustering.ipynb` JSON as
the converter input. Its bytes match the original conversion receipt's SHA-256.
The HTML now names and links `biotasks.notebook_script.export_python(path)` and
Jupytext 1.19.6 (`py:nomarker`), explains the ordered code-cell/syntax-tree checks,
and presents `notebook_seed()` as a separate derived-text operation. The original
file is preserved with the existing upstream license. Browser checks verified
verbatim original input, separate derived text, converted output and mobile layout.

### 2026-10-14: one documented script and a current-version viewer

The user approved retaining Markdown in the Python export and requested that
the HTML show only the updated version. The converter now preserves Markdown
cells in source order as line comments. The Scanpy conversion contains 35 code
cells and 40 Markdown cells; its executable syntax tree is unchanged. Original
notebook bytes remain the input. Model contexts use the documented baseline and
source metadata without the duplicate `question_text` rendering; prompts name
that representation explicitly. Coverage refuses a reference produced from a
different script revision. No model calls or scientific execution were launched.

The HTML now contains only the current input, documented script, conversion
receipt and provenance. Later actual outputs are empty until the updated version
is run. Converter regressions passed, including narrative containing executable-looking
text, source ordering, future imports, exclusion of stored outputs/raw cells and
determinism. Reference/coverage checks and type/lint checks also passed.

### 2026-10-14: isolated preparation output for user inspection

The user approved running only reference preparation after reviewing its clarified
input contract. Added an isolated entry point with no shell tool, Daytona
credentials, staging, reference execution or model review. It uses the current
documented script plus provenance, conversion receipt and future execution limits.
The approved policy is one creation call and at most one repair following a
structural rejection; output-limit and uncertain-transport retries are disabled.
Client output-token, input/response-byte and tool-feedback truncation caps are
omitted for this entry point. Provider limits still apply; medium reasoning and
the existing 600-second request timeout remain explicit.

Run `artifact-preparation-001` used checkpoint
`0313972bc56078355738fcb75961602621c7ce39`. GLM returned an accepted plan in one call,
without repair, in roughly 498 seconds. Reported usage: 7,973 prompt tokens and
100,751 completion tokens (including 86,359 reasoning tokens). These are provider
usage reports, not an independently verified reasoning-budget guarantee. The plan
proposes 21 artifacts mapped to 17 branch records. Schema, mapping, exact-anchor
and Python-syntax checks passed; science and execution have not been reviewed.
No generated commands ran and no Daytona sandbox was created. The reserved host
terminated successfully. A separate read-only reserved host retrieved the raw
response omitted by the older diagnostic transport's 256-KB per-file limit; it
made no model calls. All original preparation files match the archive hashes.

The plan, setup script, proposed reference, diff, exact prompt/input, raw response
and receipts are in `preparation-runs/001/`. `plan.md` is a mechanical rendering of
the unchanged structured model output. The current HTML exposes these inputs and
outputs in step 02; later steps remain unrun. Ten chat-adapter tests, six inference
gate tests, four isolated-preparation/controller tests and type/lint checks passed.
Loopback tests required socket access; the first sandboxed run could not bind.

### 2026-10-14: endpoint-focused preparation, with retained setup defects

The user approved general clarifications of branch identity, sufficient endpoint
exports, native result extraction and evidence-backed feasibility claims. Added
`capture` edits restricted to binding an unchanged standalone call to a fresh
name, with AST checks for arguments, statements, target freshness and actual
source anchoring. No seed-specific methods, desired artifacts or prior outputs
were added to the worker's input. Twenty-three focused checks passed before the
run; a subsequent check/fix keeps malformed earlier edits repairable when capture
validation encounters them (24 checks passed). This does not change the run's
checkpoint or its generated plan, which uses no capture edits.

Preparation run 002 used checkpoint `b71991b45245ec6cfb3427cf2ebb13c24527521a`.
One creation and one structural repair used the entire two-request allowance.
The first submission omitted required fields and supplied changes as a string;
the final submission passed schema, mapping, source-anchor and reference-Python
syntax checks. The worker completed in roughly 449 seconds, reporting 25,168
prompt and 86,467 completion tokens across both requests (72,448 reasoning
tokens). The new plan has six artifacts across seven branch records and removes
the custom dotplot aggregation helper. It still relies on a full-state snapshot
and makes unsupported environment assertions.

Static inspection found execution blockers in the generated setup: it makes an
empty /work/venv directory but never creates the virtual environment before
using its Python; it contains a placeholder import and an invalid Python check;
and it uses Bash despite the POSIX-shell contract. These were outside the
implemented schema/source checks. The files remain unchanged in
`preparation-runs/002/`, with separate inspection annotations. This is a completed
preparation attempt, not a runnable or scientifically validated reference.
No setup, scientific execution, independent model review or downstream stage ran.
The host terminated successfully; every archived preparation file was downloaded
and hash-verified. The diagnostic transfer now includes preparation responses
above the old per-file limit, within its existing total transport allowance.

The user asked whether uv is used. The factory environment uses uv sync --locked;
the current preparation prompt assumes Python/pip in the reference base image,
and the generated setup uses pip. No packaging-tool policy was changed in
response to that question.

### 2026-10-14: declarative dependencies and controller-owned uv setup

The user approved replacing worker-generated environment setup with a Python
project manifest and programmatic creation. Preparation now returns
`pyproject_toml`, declarative Debian `system_packages`, and `stage_inputs_sh`
restricted to original-input/cache staging. The controller writes setup commands,
bootstraps pinned uv 0.12.21, locks dependencies, syncs `/work/venv` using the base
image Python, and records the lockfile and installed package inventory before
offline computation. Pip only bootstraps uv in the minimal base image; it does
not install the scientific environment. Dependency declarations remain worker
outputs; installation/compatibility are not established by schema validation.

The preparation schema, materializer, execution adapter, Markdown renderer and
review prompt reflect this split. Existing generated run evidence is unchanged.
Thirty-two focused tests passed (2.70 seconds; peak RSS 131,716 KiB), including
invalid declaration rejection, inert preparation, no execution after review
rejection, and a real offline uv lock/sync of an empty synthetic project. This
checks environment creation without installing biological dependencies. No
model, sandbox, source analysis or subsequent pipeline stage ran. The revised
canonical prompt is ready for user review; the HTML still represents run 002,
not a new output from this dependency-manifest contract.

### 2026-10-14: independent review before preparation run 003

The user requested independent review, fixes and an actual model run. A separate
reviewer found two implementation gaps: non-table project metadata bypassed
repair handling, and the later runner discarded worker-staged input receipts.
Both were addressed generically; details are in `reviews/uv-preparation.md`.
Thirty-five focused checks passed. Prepare run 003 with the unchanged newer
notebook and revised canonical prompt: GLM-5.3, medium, one creation plus at most
one structural repair, no client token/byte caps. This authorization is for
preparation only. Generated environment setup, data staging, reference execution,
model review and downstream task stages remain unrun.
