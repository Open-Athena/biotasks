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
