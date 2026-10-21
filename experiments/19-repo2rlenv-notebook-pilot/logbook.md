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

Preparation run 003 from checkpoint `8ed5220519ab864421e263157d32bba4f05f83cc`
returned two model responses but exhausted its allowance without an accepted
plan. Creation omitted changes/artifacts/branches; repair still omitted changes
and added an unexpected branch field. Both completions ended with tool_calls,
not length. The last draft additionally contains mismatched branch/artifact
inventories. The required fields were in the supplied tool schema; this is a
structured-output compliance failure, not evidence of a notebook or uv failure.
The 436-second stage used 20,971 prompt and 78,322 completion tokens (72,527
reported reasoning tokens). All 15 evidence files were recovered and hash-verified.
`preparation-runs/003/` preserves the rejected draft and readable rendering,
validation feedback, exact input/prompt and responses. No task-specific repair
was made by us, no replacement run launched, and no generated code executed.
Both the remote host and local monitoring/collection clients are terminal.

### 2026-10-14: schema-enforcement compatibility investigation

The user approved a tiny compatibility test before any further notebook run.
Run 003 supplied a required-field schema but neither strict tools nor a JSON-schema
response format. The repair used an unrestricted merge patch. Its complete
feedback and prior response were retained; both returned arguments were valid
JSON and ended with tool_calls. These facts establish failed schema compliance,
not whether generation or the server parser lost fields.

Checkpoint a two-request probe using the actual ReferencePlan schema with a tiny
synthetic fixture, deliberately asking to omit changes and add an extra nested
field. Compare strict tool calling and JSON-schema response format at medium
reasoning, without client token/byte caps. Retain the 600-second per-request
transport timeout and disable automatic retries. No scientific analysis,
notebook generation or sandbox work is part of this probe. Both local fixture
checks passed; server support remains to be measured.

The two-call probe at checkpoint `93e3a8722379c63bac9c571a57698e280c357d47`
completed: strict tool arguments returned both deliberately requested schema
violations (missing changes and an extra nested field), while JSON-schema
response format passed the actual ReferencePlan schema. Calls took 2.48 and
2.13 seconds, using 1,393 prompt / 1,103 completion tokens (754 reasoning).
Evidence is in `schema-probes/001/`; all eight original files were hash-verified.
The remote host and local clients are terminal. This is a narrow compatibility
result, not a proof of all schema behavior or scientific correctness.

Preparation now uses JSON-schema response format for both creation and repair.
The same complete schema is sent each time; responses pass through the existing
upstream submission validator, never its merge-patch handler. Missing fields
are not filled in by the factory. Retain one creation and one repair, medium
reasoning and the existing no-client-token/byte-cap policy. The canonical prompt
now requests complete JSON objects. Fifty-one focused tests passed, including
complete-object replacement, schema feedback, refusal/truncation rejection and
the preparation-only boundary; type and targeted lint checks passed. No notebook
preparation rerun was launched after this change.

### 2026-10-14: preparation run 004 with JSON-schema responses

The user authorized another preparation-only run to inspect its output before
moving on. Use the unchanged newer Scanpy source and the current canonical
preparation prompt, JSON-schema responses, GLM-5.3 at medium reasoning, one
creation and at most one complete-object repair. No extra client token/byte
caps; retain the 600-second per-request timeout. Do not execute generated
setup, analysis, independent model review or downstream task stages.

### 2026-10-14 — Preparation-only run 004: schema-valid, inadmissible drafts

Ran only the preparation worker from checkpoint `8355040f54a39f4bd6acb8dbde6eb89336c21de0`, as requested, using strict JSON-schema responses. Both creation and the single complete-object repair passed the exact supplied JSON Schema. Creation failed exact source-anchor validation (four of six anchors absent); repair returned empty artifact/branch inventories and five nonmatching anchors. The controller rejected both. Preserved all 15 original evidence files after hash verification and rendered both rejected drafts separately under `preparation-runs/004/`. Two calls, 711 seconds; remote job terminal. No setup, reference execution, later stage or new run. Schema conformance improved relative to run 003; faithful usable preparation did not. Cause of corrupted source quotations remains undetermined.

The user proposed returning an edited script instead of exact anchored edits. This would let the controller compute the diff and remove the fragile source-quotation protocol. It remains a proposal for discussion; no prompt/protocol change or further model call has been made.

### 2026-10-14 — Simplified preparation contract and run 005 authorization

The user approved returning the complete edited script instead of exact anchored edits, then also approved a single endpoint inventory, brief nonduplicated explanations and programmatically derived file facts. Removed the edit-list protocol and separate branch map. The controller now checks script syntax and computes the diff; it does not mechanically enforce the former capture/export edit categories. Scientific preservation remains a prompt requirement and a later review responsibility, not a claim established by syntax checks. No seed-specific rules were added. All scientific branches must still be covered by the endpoint descriptions.

The final contract passed 49 focused tests, including inert script materialization, syntax-error repair, artifact-path/inventory validation, the two-request ceiling and no setup/analysis/review/sandbox execution. Python/schema fixture changes passed targeted lint after import sorting. Run 005 is authorized for preparation only, using the same newer notebook, GLM-5.3 medium, strict JSON-schema responses, one creation and at most one repair, no extra client token/byte caps and the existing 600-second per-request timeout. No viewer update or downstream stage is included. Exact checkpoint and result will be recorded with the output.

### 2026-10-14 — Preparation run 005 ready for inspection

Run 005 from `67c3dbc4e07513f704dd498349a9f155d97458b5` returned a complete script and single endpoint inventory on its first call; no repair was needed. JSON Schema, environment declaration, unique normalized artifact-path and Python syntax checks passed. The controller produced the exact diff without executing the script. Preserved and hash-verified all 19 original evidence files in `preparation-runs/005/`; readable output links are in that directory's README. One call, 392 seconds, 7,991 prompt tokens and 60,528 completion tokens (52,078 reasoning). Remote job terminal; no task sandbox or generated setup/analysis, separate review, construction, solver or viewer update.

The worker selected a full final AnnData object plus the notebook's cluster-7 top-five table. Scientific coverage/representation still needs review. Static inspection also found an incorrect rationale that pre-filter sample counts can be recomputed from the final filtered object; preserved the original output and recorded the observation separately. No additional model call or manual task fix.


### 2026-10-14 — Terminal-result preparation; execution owns setup

The user narrowed preparation to terminal scientific results already stored in original named variables or object fields. Preparation adds code to save those values, returning a complete script, one endpoint inventory and brief explanations/exclusions/uncertainties. No intermediate or diagnostic exports, full-state fallback snapshots, newly captured unnamed expressions, new scientific computations or reconstruction of plotting internals. Every branch is considered; branches without eligible stored outputs are explicitly excluded from the target inventory while retaining all original computation. Reject if there are no eligible endpoints. The user separately confirmed that input downloads, caches and offline path setup move to execution along with dependencies.

Updated the canonical preparation/review prompts, response schema, inert materialization and Markdown renderer. The schema no longer accepts environment rationale, Python project, system-package or staging-script fields. The controller no longer writes environment files during preparation. Reusable uv/environment helpers remain independently tested for later reuse. Retired the old combined reference runner and blocked its payload construction before job submission: its text-only setup contract is incompatible with the new boundary. The tool-enabled execution worker is not integrated yet; the historical implementation remains in Git at `2e1fb637ed0a8dad48e4e8ef9017e49e765d9575`.

Fifty-two focused tests passed (chat adapter, preparation, reference protocol, environment helpers and schema probe), including rejection of obsolete environment fields, one creation/one repair, inert script storage and refusal of the retired launcher. A subsequent preparation-only rerun of six local tests passed after adding coverage for rendering the environment-free plan. Targeted Ruff checks and whitespace checks passed. Tests used fake model responses and dependency-free local fixtures; no model call, generated scientific execution, biological data download, sandbox, downstream stage or viewer update. The original run 005 output remains unchanged and does not validate this revised contract. Next is inspection of a new preparation result before execution-stage work.

### 2026-10-14 — Preparation run 006 authorization

The user requested only a new preparation-worker run with the updated terminal-result prompt, to inspect the output before advancing. Use the unchanged newer Scanpy conversion, GLM-5.3 medium reasoning and strict JSON-schema responses, one creation and at most one complete-object structural repair, no extra client token/byte caps and the existing 600-second per-request timeout. No scientific data staging, task sandbox, generated-code execution, independent model review, construction, solver or viewer update. Preserve the exact checkpoint, original response, computed diff and endpoint inventory.

### 2026-10-14 — Preparation run 006 ready for inspection

Checkpoint `8f901f4937bf1f46da68d7b1591f808cb956bbe0` completed the updated terminal-result preparation in one GLM-5.3 call (348 seconds), with no repair. The worker proposed per-cell cluster/annotation CSV, per-cluster marker results and the already named cluster-7 top-five marker list. No environment/staging artifacts or full-object export. Preserved all 16 original preparation files after SHA-256 verification; exact response/schema, script identity, syntax and computed diff checks passed. This is structural admission, not scientific approval. Recorded three narrative-comment edits and an inventory path-base ambiguity separately from the unchanged output. No further call or manual fix.

Two local launcher invocations stopped at imports before submission (obsolete client dependency; incomplete workspace import path). The existing dedicated client with the full Iris/rigging/finelog path submitted exactly one remote job. Remote job and local submission/monitoring clients are terminal. No sandbox, biological input staging, generated-code execution, independent model review, construction, solver or viewer update. Output is in `preparation-runs/006/` for user inspection.

### 2026-10-15 — Append-only preparation

The user agreed that preparation should return only export code, with the controller appending it to the untouched original script. Replaced `reference_script` in the response schema with `export_code`; save it separately as `exports.py`, then assemble `reference.py` as baseline + two newlines + export code. Combined syntax checks and a controller-computed diff remain; the original source text is preserved by construction. Endpoints must still be accessible in their intended state at script completion. Explain exclusions for overwritten/deleted/out-of-scope results rather than adding earlier capture or insertion machinery. Artifact paths are now explicitly relative to `/work/outputs`.

Updated preparation/review prompts, controller, schema probe fixture, renderer and current workflow/proposal. Original run 006 and all other worker evidence remain unchanged. Fifty-five focused tests passed, including exact source preservation with and without trailing newlines, rejection of obsolete full-script/patch responses, combined-script syntax failures, one structural repair and inert materialization/rendering. Targeted lint and whitespace checks passed. Added code still needs scientific review; append-only construction does not prove correct exports or prevent arbitrary behavior inside generated code. No model rerun, execution or viewer update. The earlier scientific questions about endpoint completeness and plot-displayed results are not claimed resolved by this interface change.

### 2026-10-15 — Append-only preparation run 007 authorization

The user requested just the preparation worker with the append-only prompt, for inspection before advancing. Keep the unchanged newer Scanpy conversion, GLM-5.3 medium reasoning, strict JSON-schema responses, one creation and at most one structural repair, no extra client token/byte caps and the existing 600-second request timeout. Preserve worker-returned `export_code` separately from the controller-assembled reference and computed diff. No scientific setup/execution, task sandbox, separate model review, construction, solver or viewer update.

### 2026-10-15 — Append-only preparation run 007 complete

Checkpoint `b1a0463b6974aa4231d56fadec598e46ebf5bdc9` returned one GLM-5.3 response in 71 seconds; no repair. Preserved all 17 original preparation files after checksum verification. JSON Schema, exact original-source prefix, export-code identity, combined syntax and diff checks passed. Worker returned only export code; the controller assembled the reference. Public input is identical to run 006; candidate evidence was screened for credential/private-service markers before publication.

The worker reintroduced a complete AnnData snapshot plus all per-cell annotations, including QC/doublet diagnostics, alongside the DE table. Static inspection flags this as inconsistent with the intended terminal-only selection, despite the explanation claiming the whole container is the deliverable. Append-only construction prevented source edits but did not establish endpoint quality. Original response remains unchanged. Remote job and local clients terminal; no additional model call, manual task correction, generated-code execution, scientific setup, sandbox, independent review, construction, solver or viewer update. Output is in `preparation-runs/007/`; user inspection remains the next step.

### 2026-10-15 — Scientific endpoint selection and single-call preparation

The user approved tightening the general selection rule after run 007 treated its mixed analysis-state container as a scientific deliverable. Preparation must identify scientific results from source goals before choosing storage; mixed containers are excluded and their terminal fields selected instead. Standalone result tables or embeddings can be saved whole. Preserve meaningful fields and identifiers, justify omissions, and do not infer intermediate status merely from plot display or earlier computation. The existing `source_evidence` field now asks why each result is an endpoint as well as where it is stored. No seed-specific rule was added.

Preparation now makes exactly one GLM call, followed by schema/syntax validation and inspection, with no automatic repair or output-recovery call. Failed responses remain preserved. Updated the canonical preparation/review prompts, schema description, runner, configuration and current workflow/proposal. Append-only assembly remains unchanged; prior generated outputs were not edited. Fifty-five focused tests passed, including single-call failure handling and rejection of the old two-call configuration; targeted lint and whitespace checks passed. Tests used the shared-node lock and resource guard (about 90 MiB peak RSS, 2 seconds). No model run, scientific execution, downstream stage or viewer update. The revised prompt's scientific effectiveness remains untested.

### 2026-10-15 — Preparation run 008 authorization

The user requested a rerun of preparation only after reviewing the general endpoint-selection and single-call changes. Run the unchanged newer Scanpy conversion with GLM-5.3 medium, strict JSON-schema responses and exactly one request, no automatic repair. Preserve the original response, appended code, computed diff and checks for inspection. No scientific setup/execution, sandbox, separate review worker, construction, solver or viewer update.

### 2026-10-15 — Preparation run 008 complete

Checkpoint `c41bc9d9f642dba73b3146af94718b947236e23e` completed one GLM-5.3 medium request in 193 seconds, no repair. JSON Schema, combined syntax, exact original-source prefix, export-code identity, computed diff and all 17 original evidence hashes passed. Input context matches the previously public run 006. Publication files were screened for credential/private-service markers. Reported usage was 7,249 prompt and 27,689 completion tokens, including 25,314 reasoning tokens.

The worker avoids the full AnnData dump and exports UMAP coordinates, DE results and the existing cluster-7 marker list, but also copies all cell/gene annotations including diagnostics and feature-selection intermediates. Static inspection flags these broad exports and their survival-to-completion justification; structural acceptance is not endpoint approval. Original output remains unchanged. Initial log retrieval was incomplete; another read of the same terminal job recovered all records. Remote worker and local clients are terminal. No additional model request, manual fix, scientific execution, sandbox, independent model review, downstream stage or viewer update. Inspect `preparation-runs/008/` before advancing.

### 2026-10-15 — Iterative preparation review authorized

The user asked to continue iterating until satisfied. Scope remains preparation only, general factory prompts, unchanged source, GLM-5.3 medium, one call per checkpoint and no automatic repair; no scientific execution, construction or viewer update. Run 008 suggests that “all branches” was interpreted as every tutorial section and that excluding whole objects did not prevent copying mixed tables. Reworked selection around independent scientific outcomes versus supporting preparation/diagnostics, and applied the same field-selection rule recursively within tables. Endpoint evidence must establish scientific role, not just storage location or survival. No package, field name, method or desired output from this seed is prescribed. Run 009 will test this revision; original generated outputs remain unchanged.

### 2026-10-15 — Run 009 accepted in static review; unchanged-prompt confirmation

Run 009 completed in one call, 163 seconds, with 7,377 prompt and 24,369 completion tokens (22,639 reasoning). All 17 original files, schema, combined syntax, exact prefix, response/code identity and diff verified. Explicit cell-result fields and full ranked DE results replace broad diagnostic tables. Static source/helper inspection finds no preparation blocker. The full DE table covers the cluster-7 excerpt; another duplicate artifact is not required. The native accessor at the source revision reads stored results with no cutoff requested; execution compatibility remains untested. Original output is unchanged.

Prompt and preparation tests passed (4 and 6 respectively); an initial combined test invocation used the upstream environment lacking the CLI's cyclopts dependency, so prompt tests were rerun in the project environment. No code fix was needed. The run 009 submitter peaked at approximately 501 MiB, slightly above the local estimate; subsequent submission will exclude unused Marin docs/experiments/tests from the workspace bundle using the client's documented bundle_exclude option to reduce transient memory. This does not change the frozen BioTasks payload or worker inputs.

Run 010 repeats the same prompt, input, schema and settings as 009, with only the campaign identity changed, to check consistency before stopping iteration. Still one preparation call, no automatic repair and no later stage. This is not cross-notebook validation. All run 009 hosts/clients are terminal.

### 2026-10-15 — Run 010 confirms preparation; stop prompt iteration

Run 010 completed one GLM-5.3 medium call in 208 seconds; no repair. The system prompt, full context and serialized API request are byte-identical to run 009. Both pass static review: selected cell/clustering/lineage/UMAP fields and full ranked DE results, with no broad diagnostic tables. Run 010 adds stored DE parameters as interpretation context and explicitly covers the named cluster-7 excerpt through the full table. Different filenames/serialization implementations are acceptable and no output was manually edited. Native helper/result-storage code was inspected at the notebook's source revision. This is source-level review, not numerical execution or cross-seed validation.

All 17 original files, schema, combined syntax, source prefix, export identity and diff verified. Reported usage: 7,377 prompt and 31,306 completion tokens (29,176 reasoning). Initial log read lacked the archive manifest; a second read of the same completed job recovered everything. The smaller submission bundle reduced peak local RSS to about 459 MiB. Hosts and clients are terminal. Two model calls total for this iteration (009 and 010), zero automatic repairs, no scientific setup/execution, sandbox, separate model review, construction, solver or viewer update. Prompt iteration is satisfactory for this seed and stops here. Inspect run 010 before moving downstream; execution still must establish environment compatibility, schema/value fidelity and resource fit.

### 2026-10-15 — Tool-enabled setup and controlled reference execution

The user requested the next step be updated for the new preparation contract and clarified that it should prepare dependencies/inputs and test the full reference through a controlled offline run. Implemented a separate `run_reference_setup.py` with canonical `notebook-reference-setup.md`, consuming reviewed preparation run 010 without regenerating preparation. Reused Tasksmith's artifact-stage tools, GLM adapter, uv helper, DaytonaWorker, policy/probe checks, evidence transport and owned-resource cleanup. The obsolete combined entry point remains disabled.

The worker writes a dependency-only pyproject, system-package list, staging recipe, input inventory and minimally adapted analysis file; it has a setup shell and controller-owned `test_reference`. The controller reconstructs the virtual environment, records its lock/packages, hashes staged files after the generated setup returns, restores the frozen exports and output inventory, starts in fresh working/output directories offline, and preserves trial logs/results/download hashes. Failed tests remain evidence. A success report requires a passing test on the same candidate files; necessary input-path adaptations are recorded as diffs and must be explained. Their scientific validity remains a review requirement, not a syntax/hash guarantee. Declared-input receipts are not complete dependency-graph proof, and shared OS packages/caches mean this is not fresh-image reproducibility validation.

Seventy-seven focused tests passed, including real offline uv creation with a dependency-free synthetic fixture, frozen export restoration, invalid/stale success claims, failed setup/offline policies, changed inputs, upstream tool dispatch, transport uncertainty and cleanup even after evidence-export failure. Four prompt/CLI tests passed separately. Targeted lint and whitespace checks passed. A test fixture initially omitted the explicit medium reasoning setting; that fixture was corrected. Final verification initially aborted on shared-lock contention, then completed after the lock holder was absent. No model, biological-data, Daytona or downstream run occurred; no viewer update.

The actual `reference-setup.json` deliberately leaves model-request and reference-test counts unset; packaging and runtime reject them. The existing proposed 30-minute cumulative setup, ten-minute reference, two-hour campaign/five-minute cleanup and $5 reservation are visible there. Reconcile the new tool-enabled session's counts before its first launch, rather than inheriting historical 45/80-request allocations or treating preparation's single-call rule as a shell-agent budget. The user's $100 standing spending authorization remains unchanged.

### 2026-10-15 — Remove arbitrary setup request cap and address prompt review

The user approved removing the proposed 20-request cap and asked to address the independent review. The request ledger now supports explicit null allowances while continuing to record every request; the GLM tool loop can run until submission or its existing deadline. A narrow, hash-pinned Repo2RLEnv patch passes the optional allowance through the existing artifact stage instead of substituting a very large integer. Existing bounded stages retain their limits. The setup configuration's null request count now means no count cap; its null test count remains undecided and prevents launch. No new time, spending or test budget was assumed.

Addressed the review's directory/reset timing and test-invocation accounting findings, plus immutable staged inputs and base-image Python clarification. Scientific source/export constraints are unchanged. Forty-two focused adapter, ledger, upstream-dispatch, setup and preparation tests passed, including an uncapped 22-call synthetic session with every call recorded, deadline stopping and existing capped behavior. The first sandboxed test invocation encountered failures and hung; it was stopped, and the same checks passed with elevated local execution. No model, sandbox, biological computation, pipeline relaunch or viewer update occurred.

### 2026-10-15 — First setup/reference session authorized

After reviewing the worker/tool division and confirming that this step includes the actual reference run, the user requested launch. Use preparation 010 unchanged, one GLM-5.3 medium setup session with no request-count cap, up to two combined setup/test invocations, 30 minutes cumulative setup-tool time and ten minutes per complete reference computation. Retain the configured two-hour campaign/five-minute cleanup, CPU-only 4-vCPU/8-GiB/10-GiB sandbox and $5 reservation within the standing $100 authorization. No automatic fresh worker session or downstream task construction. Preserve generated files and failed trials for inspection; no manual seed-specific fixes.

### 2026-10-15 — Setup/reference session 001 submitted

Submitted exactly one remote host from checkpoint `e2da746ec48d48a0fe8445ee6a9b110e3055a1c3`; startup status is RUNNING, one task, zero completed/failed. The initial credential handoff was blocked before submission; the user identified the current approved credential store and requested correction of the private access guide. The guide was updated, then the launcher retrieved credentials directly into memory and submitted successfully. No credential values or private routes enter this record. Local launcher terminated successfully at about 492 MiB peak RSS. Scientific execution and generated output remain unobserved at this checkpoint; no downstream work or duplicate session.

### 2026-10-15 — Setup iteration authorized

The user requested iteration until satisfactory. Scope remains the setup/reference stage: inspect the active session, improve general prompts/controller behavior when evidence justifies it, preserve failures and generated candidates, and run further bounded sessions within the standing budget. Scientific source methods and reviewed preparation-010 exports stay fixed. No seed-specific manual fixes or downstream construction. Reconcile reservations before any replacement session; the current aggregate reserve is $96 of the $100 ceiling, which is conservative and not measured usage.

### 2026-10-15 — Setup/reference 001 satisfactory after execution review

The original session succeeded with 93 GLM-5.3 medium calls, one full offline reference test and no repair test. Worker elapsed time was 725.6 seconds; complete reference execution was 147.5 seconds with 5,175,376 KiB (4.94 GiB) peak child RSS. All three declared exports were produced, three staged input files verified unchanged, and final candidate hashes matched the tested candidate. Source diff inspection found only cache/registry/headless adaptations; frozen preparation-010 exports are exact. Owned-sandbox cleanup was verified and separate readback found none remaining.

A separate one-CPU read-only evidence job streamed the archived outputs, checked their original hashes and inspected CSV schemas, rows, missing/nonfinite values and numeric ranges. It observed 17,041 cell rows and 398,259 gene-ranking rows, no blank fields/nonfinite numbers and valid p-value ranges. Both the original host and evidence reader are terminal; no scientific rerun, model call or sandbox in the evidence reader. Preserved 23 original small evidence files with hashes, the worker's unedited report and a separate review. Corrected the review's interpretation of the report's memory units and staging attribution without editing generated outputs. Private runtime identifiers and credentials were excluded from public files.

No prompt/controller defect requiring a replacement run was found, so iteration stops as satisfactory for the current notebook and setup/execution stage. Cold-image reconstruction, numerical repeatability, independent scientific reproduction and generality are not established. No task construction, grader, solver or viewer update; the conservative $96 reservation remains unchanged and is not measured usage.

### 2026-10-15 — Prepare the coverage/specification step for review

The user requested proceeding after satisfactory setup/reference execution. Prepared the canonical `notebook-task-specification` prompt and exact evidence bundle from setup 001. The previous task-design prompt chooses a new scope and the older coverage runner expects obsolete reference records and request caps, so neither is reused unchanged. The current proposal's single separate GLM pass reviews preparation's endpoint inventory against the whole original source and observed execution, then drafts a public brief and private validation plan. Missing defaults, identity semantics or comparison evidence must be reported rather than invented; blocked responses cannot supply an accepted brief. This is separate from task construction and scientific validation.

The input builder verifies original evidence hashes and agreement between declared, executed and independently audited artifacts. No task-specific methods, endpoints or grading thresholds were manually prescribed. Policy retains the agreed CPU-only sandbox and provisional solver allowance. The prompt/input/schema are reviewable before a new-stage model call; no model, sandbox, reference rerun, construction, solver or viewer update occurred.

Six focused evidence/schema tests and four prompt/CLI tests passed. Targeted lint, formatting and whitespace checks passed. Input generation is deterministic and performs no biological computation.

### 2026-10-15 — Address independent specification review

The user requested an independent review, then asked to address it. The separate reviewer found two substantive omissions from the specification prompt: explicit per-branch controls and independent alternatives from the agreed proposal, and the distinction between instructed methods and what terminal outputs can verify. Restored both requirements in the canonical prompt without adding stages, schema fields or seed-specific requirements. Controls remain prospective until executed; uncheckable required scientific distinctions are blockers rather than grounds for silent scope changes. The exact input bundle is unchanged; optional lockfile summarization is deferred. See `specification-review-001.md` for findings and disposition. Four prompt/CLI checks and whitespace validation passed. No model or downstream run.

### 2026-10-15 — Specification iteration authorized

The user requested iteration until satisfactory. Run the reviewed specification prompt against the successful setup evidence through one GLM-5.3 medium JSON-schema call per recorded iteration, with no automatic repair or extra token/byte caps. Reuse the existing 600-second request timeout and reserved Iris CPU host; no Daytona credentials, sandbox, biological execution, construction or solver. Preserve original responses and improve only general factory prompts/evidence handling where warranted. Ten focused evidence/schema/real-controller tests passed, including blocked, invalid and truncated responses with no second call. An initial test command omitted the source PYTHONPATH; rerunning with the documented source path passed without a code change. The standing spend ceiling remains unchanged.

### 2026-10-15 — Specification 001 rejected; compact non-scientific context

The first call returned a schema-shaped placeholder with `draft_ready` and an empty brief; the validator rejected it. Finish reason was stop, not length or timeout. One request consumed 93,807 prompt tokens and 42,913 completion tokens. The response does not establish the cause. Preserved original evidence and a clearly derived final-content view in specification-runs/001; the remote job is terminal and no downstream work ran. Applied the independent review's optional simplification: retain and hash-check the full uv lock, but provide only its hash/size and the existing exact resolved package/version list to the model. No scientific source, output evidence or resource policy is dropped; no arbitrary byte/token cap is added. Run 002 tests this general evidence-presentation change with the same one-call contract.

### 2026-10-15 — Specification 002 rejected in content review

The compact context reduced prompt tokens from 93,807 to 28,598. Run 002 returned a full schema-valid draft in 497 seconds, but content review rejected guessed tolerances/defaults, copied arguments between distinct invocations, and inconsistent relabeling/annotation semantics. Original outputs remain unchanged in specification-runs/002. Corrected the operator's earlier inference about duplicate cell names: the original source explicitly makes observation names unique after concatenation. Run 003 keeps context/schema identical and strengthens general evidence sufficiency, per-call fidelity, no guessed calibration values, cross-output equivalences and Markdown formatting. No seed-specific method is prescribed. Both earlier hosts are terminal; no downstream work.

### 2026-10-15 — Specification 003 rejected as non-delivery

Run 003 returned nonempty placeholders rather than a task or validation plan. Basic schema acceptance did not imply semantic acceptance. Preserved originals in specification-runs/003. Iteration 004 clarifies the output fields in JSON-schema descriptions and the meaning of factory-private: the plan must be returned to the caller and excluded only from solver-visible files. No source-specific constraint or artificial length threshold is added. A separate static read of the exact hash-verified Scanpy wheel confirmed that the clustering default omitted in later calls is -1, whereas the first source call explicitly requests 2; the current worker input has not been modified with this finding. Corrected the earlier duplicate-name interpretation in the setup review, preserving original execution artifacts.

### 2026-10-15 — Specification 004 preserved; simplify the blocked path

The latest one-call response selected needs_evidence and returned no public brief, correctly identifying absent implementation evidence. Content inspection still rejected contradictory equivalences, unsupported exact-match assumptions and malformed prose present in the raw response. This does not establish a transport or service defect. Preserved all original outputs and receipts. Simplified the canonical prompt so blocked reviews request evidence rather than continue into speculative grading design; full drafting and controls remain conditional on sufficient scientific evidence. Added explicit English and JSON newline guidance. Iteration 005 keeps context, schema, model, medium reasoning and one-call/no-repair behavior unchanged. No seed-specific facts or manual task corrections added; all earlier hosts are terminal.

### 2026-10-15 — Specification 005 non-delivery; diagnose before further prompting

The simplified prompt produced another schema-valid placeholder with garbled text after one 285-second call. Preserved all seven original small evidence files; final content, not file rendering, already contains the defects. No notebook-specific blocker can be inferred from this non-review. Stop adding prompt clauses and use the existing two-case synthetic probe infrastructure to compare identical JSON-copy requests with and without server-side JSON-schema constraints. Keep GLM-5.3 medium, no client token/byte caps, sequential calls, original traces and no automatic retries. This checks basic delivery only; even a passing probe cannot validate long-context specification. No service reconfiguration, task repair or downstream work is authorized by this diagnostic.

### 2026-10-15 — Delivery probe 001 and correction of its copy-target ambiguity

The plain response preserved the fixture text but returned the surrounding schema/object wrapper; the constrained response returned the intended inner object but changed all newlines to HTML tags. The copy instruction was ambiguous because the supplied object was a wrapper. Preserved both original responses and corrected the diagnostic to supply only the actual object in both modes. The two request payloads still differ only in response_format. No notebook conclusion or serving root cause follows from this first probe. Added a tested experimental plain-JSON adapter option retaining all local parsing/schema checks and no automatic retries; the default remains structured JSON. Thirty-six focused adapter/controller tests, five probe checks, lint/format and type checks passed before further remote use.

### 2026-10-15 — Corrected delivery probe motivates a full-input comparison

Probe 002's plain response exactly copied the fixture; the constrained response replaced newlines with literal /n despite passing schema validation. Verified that request payloads differ only by response_format. Each mode has one sample and no fixed sampling seed; the serving-code root cause and relationship to other content defects remain unproven. Run specification 006 with the exact run-005 prompt and context, using the separately recorded diagnostic plain-JSON configuration. The same local validator, one-call limit, model/settings, timeout, artifact preservation and stage boundary remain in effect. Do not treat the mode change as automatic production adoption or repair the generated content manually.

### 2026-10-15 — Full-input comparison 006 and remaining workflow decision

Run 006 returned substantive review text and a needs_evidence decision, but failed JSON parsing because the final text uses a fence and literal newline escapes outside strings. Preserved the exact returned text without repairing or adopting it. Verified that the actual API request differs from run 005 only by response_format; prompt, evidence and sampling settings are identical. One call, 302.9 seconds, finish stop; the host is terminal. This one comparison and the synthetic probe do not identify a serving-code root cause. Content review also finds incomplete DE semantics, unresolved cross-output annotation identity and an unnecessary rerun-first evidence plan. The worker lacks package source/tools needed to resolve consequential defaults. Asked the user to choose read-only inspection tools or a separately collected evidence bundle before changing the one-shot stage. No more calls or downstream work are launched while that decision is pending. All local clients and owned remote jobs from this turn are terminal; no Daytona usage in these iterations.

### 2026-10-15 — Approved read-only inspection in the specification stage

The user accepted package-source inspection after discussing its scope. Replace the one-shot specification mechanism with one tool-enabled session: programmatic catalog from the reference's verified lock and recorded versions; lazy hash-verified distribution reads; list, literal search and line-range tools; no shell, package execution, installation or notebook rerun. Prefer universal Python wheels, otherwise the corresponding release source archive, explicitly distinguishing that from installed native-binary evidence. The worker selects its own inspections. No seed-specific methods or hand-authored scientific answers enter the prompt.

Reuse upstream artifact submission and local validation instead of standalone JSON responses. Correcting an invalid submission stays inside the same session; no automatic relaunch or uncertain transport retry. Keep the existing two-hour deadline and 600-second request timeout, free GLM-5.3 medium and reserved CPU host. Follow the accepted tool-enabled setup pattern without another arbitrary request cap; count all calls and retain original traces. Forty-four focused package-source, specification and adapter tests passed before launch preparation. This does not authorize downstream construction, solver runs or viewer changes.

### 2026-10-15 — Specification 007: source access succeeds, interpretation still fails review

One session at checkpoint 9b16568c995dca363e5883375c8adcb346a8c343 completed in 1,539.97 seconds with 79 calls: 32 searches, 46 reads and one artifact submission. The worker inspected verified Scanpy/AnnData wheels and the igraph source archive, corrected one invalid read range and returned readable, schema-valid English Markdown without a repair submission. Preserved the original generated files unchanged and hash-checked the complete tool-event trace. The bounded local recovery contains 15 raw responses; all originals and source archives remain in durable storage. No aggregate token claim is made from that subset.

Operator review rejects the generated draft_ready disposition: its feature-selection prose combines top-N selection with cutoffs the implementation ignores, despite having read that documentation; its proposed valid label-permutation control reapplies a number-to-lineage dictionary and therefore changes biological annotations. These are interpretation/consistency failures, not missing-source problems. The next general prompt revision should check active argument branches and meaning-preserving transformations across dependent outputs. No seed-specific answer or generated-task repair was added. No new session, construction, scientific rerun, solver or viewer update was launched. The remote host and local clients are terminal. See specification-runs/007/README.md for the review and evidence boundaries.

### 2026-10-15 — General consistency checks for specification 008

The user requested continued iteration until satisfactory. Strengthened the canonical prompt in two general ways: resolve argument precedence through the actually selected implementation branch; work through hypothetical representation changes across all dependent outputs and verify that scientific meanings are preserved. Contradictory semantic rules cannot be deferred to numerical calibration. No notebook-specific methods, thresholds, gene names or corrective answers were added. Keep the exact run-007 evidence bundle, tools, model/settings and time/resource bounds. A supported needs_evidence decision is an acceptable stage result; do not force draft_ready by changing the frozen science or exports. Run only specification; no construction or viewer update.

### 2026-10-15 — Specification 008 startup failure; identical-prompt retry 009

The host failed before invoking the specification worker because its selected cluster had no registered endpoint for the approved model route. Zero model requests; no scientific outcome. Preserved the original bootstrap status separately. A documented alternate route is running; retry the unchanged prompt, run-007 evidence and tools as specification 009 on existing reserved CPU capacity. Same GLM-5.3 medium and time bounds, no automatic relaunch, no new paid capacity, sandbox, reference execution or downstream stage.

### 2026-10-15 — Specification 009 transport failure; fresh session 010

Session 009 received 50 responses (48 successful source-tool actions and two invalid-argument responses), then request 51 failed with APIConnectionError; its slot remains uncertain. Worker elapsed 500.94 seconds. No artifact was submitted, so no scientific disposition can be assessed. Preserved original results, ledger, transport-failure receipt and hash-verified trace navigation; complete originals remain archived. The remote job is terminal. The documented model route still reports running. Under the user's iteration authorization, launch one fresh session 010 with unchanged prompt/evidence/tools/settings/bounds. No automatic retry, manual scientific correction or downstream stage.

### 2026-10-15 — Specification 010 reviewed; simplify scope before more iteration

Session 010 completed with 122 calls (65 reads, 56 searches, one submission), 2787.83 seconds of worker time and no tool/schema repair. It corrects the top-N feature-selection and relabeling mistakes, but operator review rejects unsupported exact partition portability, incomplete independent alternatives, an invalid component-runtime inference and an overclaim about harness enforcement. Original outputs and the complete event trace are hash-verified; 49 raw responses were locally recovered, explicitly a subset. All owned jobs/clients are terminal. No downstream execution or viewer update.

The user asked whether the approach is fundamentally stuck. Identified the combined worker assignment as too broad: translating the analysis and proposing scientifically justified portable grading in one session is producing diminishing returns. Proposed narrowing specification to analysis instructions and output schemas, with tolerances and acceptable variations established through separate executable validation. Software choice remains open. Await the user's answer before changing that stage boundary or launching another session.

### 2026-10-15 — Accepted reference-defined target with open tool choice

The user accepted the middle ground: define the target through the pinned reference workflow while allowing alternative solver software that meets the validated public output contract. Narrow specification to the reference recipe and output schemas, with a short validation handoff. Named versioned operations can define defaults; do not require reverse-engineering every implementation detail or proving universal portability before drafting. Executable validation remains responsible for justified comparison rules, controls and any claimed alternatives before solving. Rename the structured response field to validation_handoff and preserve all historical outputs unchanged. Input 011 differs from 007 only in task policy; source, exports, setup evidence and package catalog are unchanged. Keep the read-only tool session and existing model/time bounds. Rerun only specification; no construction, scientific execution, solver or viewer update.

### 2026-10-15 — Specification handoff tooling and launcher footprint

After checkpointing and launching specification 011, updated the synthetic delivery fixture to the renamed validation_handoff field; all five probe checks passed. Prioritize validation-handoff.md in future bounded diagnostic recovery while retaining compatibility with old plan files. These follow-ups do not change the running worker's frozen inputs.

The local submission client peaked at 513,476 KiB (501.44 MiB), slightly above the 500 MiB node ceiling despite a 498 MiB estimate. It terminated normally. Before any further submission, compress the frozen Git archive in the reference-stage launcher, using the bootstrap's existing compression auto-detection. A streaming comparison verified identical metadata and file hashes for all 938 members: 34,406,400 uncompressed bytes versus 13,692,508 compressed bytes. The check used 32,048 KiB peak RSS. This reduces transport copies without changing archived scientific inputs; a future launch must still pass resource gates and record its actual peak.

### 2026-10-15 — Specification 011 reviewed; keep reference operations as definitions

Session 011 returned a draft in 79 calls and 470.59 seconds. It leaves grading rules pending, but the public brief includes measured result counts and an incorrect duplicate-identifier example. The private handoff also proposes a cross-check between unrelated cell and gene row counts and asserts unmeasured determinism. Preserved all generated text unchanged; the handoff display is extracted from the verified structured response because bounded recovery omitted the standalone file. The complete trace is verified; 70 raw responses are only a subset. All owned jobs and local clients are terminal.

For specification 012, retain exactly input 011 and the same model, tools and bounds. The general prompt now makes named, versioned operations plus explicit source arguments the normative recipe, without expanded internal formulas/default catalogues or invented identity examples. Public cardinalities must be symbolic, with observed counts and label ranges confined to private evidence. The handoff asks comparison questions rather than proposing untested checks. No notebook-specific methods or manual task edits. Only specification runs.

### 2026-10-15 — Specification 012: improved draft, row-unit contradiction remains

Session 012 returned in 18 calls and 250.34 seconds, with all original responses and nine small output files hash-verified. The public recipe removes measured result counts and corrects the earlier duplicate-identifier example. It still equates per-group gene rows with per-group cell counts in a cross-table relationship, contradicting its own output schema; a private static-validation overclaim also remains. The next general revision checks row/axis units and cross-file cardinalities throughout the response and prevents static review from changing recorded validation status. Keep exact input 011, model/tools/bounds and the specification-only boundary. No manual generated-task fixes. Both sessions are terminal. Compressed submission reduced local peak RSS to 366,340 KiB, within the node ceiling.

### 2026-10-15 — Specification 013 accepted as a draft for review and validation work

The third iteration under the narrower contract returned in one GLM-5.3 medium call, 226.75 seconds, with no package-source calls or submission repair. The exact input remains 011. Original request/prompt identity, all nine small output files, the complete trace and the one raw response were verified. Public result sizes are symbolic and the cell-versus-gene row-unit contradiction is resolved. Named reference operations define methods while solver tool choice remains open; grading rules are explicitly pending.

Stop specification iteration for user inspection. Operator assessment is a usable reference-recipe/schema draft, not final task acceptance. The separate review flags nullable-lineage wording, the need to expose the resolved environment at packaging and remaining executable comparison/controls work. All generated content remains unchanged; no manual task repair or seed-specific prompt clause. No construction, scientific execution, solver or viewer update. All owned jobs and local clients are terminal. This one-seed result does not establish generality or guarantee one call on future seeds.


## 2026-10-15 — Next step: frozen reference repeatability

Following the user's instruction to proceed after specification 013, start
executable validation with two programmatic reference repeats. This checks a
prerequisite for grading before asking GLM to choose acceptance rules. Reuse the
existing sandbox lifecycle, offline controls, generated setup and frozen exports;
install from the recorded lock and reject environment/input drift. No model calls,
manual scientific changes, task construction, solver, release or viewer changes.
The initial two repeats are observations, not a portability or calibration claim.
Reserve $2 within the standing $100 ceiling (conservative aggregate holds $98;
actual provider invoices remain unavailable). Details: [reference replay](reference-replay.md).


### Replay 001 result

Both unchanged offline runs succeeded: 223.60 s and 178.18 s, with maximum child
RSS 4.94 GiB and 4.77 GiB. All three exported files matched the original run's
SHA-256 exactly, and matched each other. The saved uv lock, installed package
list and original input hashes also matched. Zero model calls; no repairs.
This supports repeatability of the pinned reference, not byte-hash grading or
universal software equivalence. [Full result and evidence](replay-runs/001/README.md).
The Iris job is terminal, cleanup passed and the full outputs were archived and
download-verified. Forty-four focused offline tests and targeted lint passed;
one stale setup-budget fixture was corrected to explicitly unset the value it
intends to test. Threaded lifecycle tests passed outside the execution sandbox
(the sandboxed attempt stalled at a fake thread call and was stopped).
Stop before task construction/solver; comparison rules and controls are next.


### 2026-10-16 — Grader construction and artifact controls

Proceeding after the successful reference repeats, add a pre-Harbor grading stage
using Tasksmith structured authoring and upstream semantic-probe schemas. Separate
GLM sessions author the grader, propose independent counterexamples and review
actual control results; at most one separate repair uses frozen checks/probes.
Only generated task content changes. Restore saved outputs and the locked reference
environment; no full analysis, solver or viewer update. Unprivileged users and
read-only reference copies separate generated code from controller evidence.

Fifty-five focused offline tests passed, including real synthetic grader execution,
report completeness, independent-probe context isolation, review gating and the
optional repair path. The guarded check peaked at 129 MiB. Reserve the final $2
of the standing aggregate authorization; all $100 is now conservatively reserved,
not measured spent. Details: [grading execution](grading-execution.md).

### Grading 001 result — candidate retained, independent validation incomplete

GLM authoring completed in 75.64 minutes and 112 requests. The generated 16-check
grader passed the five controller cases (reference, empty and three missing-file
submissions). A separate probe worker used 23 requests and 36.72 minutes but did
not submit a suite before the remaining working allowance became insufficient
for its next tool operation. No scientific probe execution, final review or
separate repair occurred. Preserve the candidate unchanged; basic controls do
not establish task acceptance. Operator review records ambiguous CSV/extra-file
wording, a dangling table reference and the need for precise numerical wording.
The author and independent probe worker duplicated substantial inspection;
narrower responsibilities are preferable to increasing budgets blindly.

The first export exhausted its remaining allowance, but the bootstrap's final
export completed: 709 files / 222,623,420 bytes, independently download-verified.
Recovered 540 small diagnostics with original hashes; reconstructed the missing
probe input from verified fields and matched its original hash exactly. The
sandbox was deleted and a separate provider readback found zero owned sandboxes.
The Iris host is terminal. No replacement, solver, release or viewer update.
[Result and original generated artifacts](grading-runs/001/README.md).

After launch, fixed a generic child-process cleanup edge case: outer SIGTERM now
raises through the helper's finally block and reaps its generated process group.
The 12 focused grading tests passed, including a real synthetic interruption;
Ruff passed. This fix is separate from the run checkpoint and from task-specific
GLM work. No generated grading code, instructions or scientific results were edited.

### 2026-10-16 — scientific task scope after user review

The user approved fixed reference-derived groups as supplied inputs and marker/DE outputs, excluding clustering and UMAP reproduction, then authorized proceeding through completion using judgment. The generic specification prompt now requests a scientific question, explicit scope reductions/input derivations, endpoint selection and proposed comparisons rather than named API recipes. Notebook-specific scope is supplied only in the experiment policy. Input 014 retains original setup evidence; previous specifications and grader 001 remain unchanged. Numerical tolerances and the precise derived-input/output projection are unvalidated until downstream executable checks. No manual task-specific edits.

Specification 014 will use the existing read-only tool session, GLM-5.3 medium, reserved Iris CPU host, two-hour campaign boundary and no Daytona sandbox. It requires no new Daytona reservation. Seventeen focused offline specification checks and targeted Ruff checks passed (83,772 KiB peak RSS). Before paid sandbox continuation, reconcile the conservative $100 reservation ledger against lifecycle evidence; reservations are not measured charges. The original grader's exact-recipe contract is not the acceptance baseline for the new task.

Budget reconciliation releases $15 of unused Daytona holds: the original campaign registry explicitly records $0 for read-only recovery slots 003/007 ($10 reserved), and reference campaign 002 never executed setup or scientific computation ($5 reserved). All other historical holds remain conservative and unchanged; actual invoice is still unknown. This leaves $85 held and $15 unallocated within the existing $100 authorization, without assuming free credits or reducing any executed campaign allowance.

Specification 014 completed in 41 requests, 631.8 seconds, with package inspection and no sandbox. Its standalone scientific question is directionally useful but not accepted: contradictory ranks, arbitrary top-k boundary, invented tolerances, auxiliary reference requirements and a mistaken statistical-API equivalence remain. Original outputs are preserved. Revision 015 reuses the proposal/inspection findings and operator critique in one JSON-schema response instead of repeating inspection. Generic prompt corrections address these failure patterns. Eighteen focused specification checks passed after decoupling the read-only-session fixture from the mutable current experiment configuration.

Prepared the generic materialization stage: GLM authors input/reference derivation and a standalone oracle; the controller checks immutable source identities and declared inventories, then hides private answers/author files/original staging paths from the oracle user. Successful execution remains unvalidated scientifically. Twenty-one initial materialization/grader checks passed, then ten materialization checks after additional provenance/path coverage; twenty chat transport tests passed with safe request/response progress events. No materialization model or sandbox has launched yet. Future grader prompts keep the scientific question separate from acceptance rules and avoid duplicating the independent probe worker's work.

Revision 015's sole JSON-schema response was rejected: draft_ready with an empty question and unrelated protein/histone assertions. The response was received normally after 315.08 seconds; this was semantic noncompliance, not transport uncertainty. Preserve the failure. Revision 016 uses a submission-only Tasksmith session (submit/revise tools, no package inspection), reusing input 015 and the same prompt. This allows local validation feedback rather than repeatedly launching one-shot schema responses. No downstream execution has occurred.

Prepared grading continuation for derived artifacts: verified materialization archives supply task inputs, original projected answers and oracle outputs. A fresh independent GLM implementation receives only the public question and task inputs; private answers/code are inaccessible during its session. Execution feedback remains separate from comparison results. The grader must accept both recomputations and the reference, plus independent adversarial/representation controls; this is finite validation, not universal portability. Twenty-four focused grading/materialization checks and twenty-two setup/replay regressions passed. Nineteen specification checks cover the new submission-only correction loop. No new sandbox has launched.


## 2026-10-16 — Scientific specification ready for materialization

Specification 016 produced a usable complete-endpoint draft in one submission after the malformed one-shot response in 015. Stable supplied identities replace incidental naming conventions, and numeric tolerances remain unclaimed until independent computation. Recorded reference replays already establish repeatability; the worker's contrary private statement is stale. Next: GLM materializes supplied metadata, projects existing answers, and executes an isolated oracle. Reserved $2 within the existing $100 ceiling (now $87 held, $13 unallocated; holds are not actual charges).

Generic packaging preserves the exact validated question and grader, keeps answers outside the environment image, and requires reference, recomputation, alternative, empty, missing-output and wrong-answer controls against the same grader bytes. The native runner now supports the agreed 4-CPU/8-GiB/10-GiB, ten-minute profile while preserving historical defaults.

## 2026-10-16 — Native validation handoff

Prepared a native Harbor runner for the exact validated scientific task. It runs oracle and no-op controls before one blind Terminus-2 GLM attempt, uses the agreed 4 CPU / 8 GiB / 10 GiB and 600-second solver profile, and preserves upstream cleanup accounting. The image preinstalls tmux for offline operation. Patch 0011 permits omitting extra Terminus turn/token caps while retaining the wall-clock bound and harness/provider defaults. Fifteen focused packaging, adapter and dispatch-gating tests pass; no native trial has launched yet.

The materialization worker exposed an execution-interface ambiguity: it launched a background calculation and later waited for it, while the controller correctly terminates remaining child processes when a shell call returns. Subsequent worker prompts now explicitly require foreground execution and explain the default 120-second shell timeout versus the allowed 600-second computation timeout. This changes future prompt inputs; the running checkpoint is unchanged. Diagnostic recovery also prioritizes materialization and independent-computation summaries and includes future native-trial evidence.


## 2026-10-16 — Stop materialization 001 and clarify the stage boundary

Sent one SIGINT to the uniquely identified owned authoring process after it repeatedly slept waiting for an already-terminated background computation; no candidate had been submitted. Its controller is exporting evidence and cleaning up. No scientific artifact was edited. Retry 002 keeps specification 016 and makes foreground shell lifecycle explicit both in the prompt and tool replies. The prompt also distinguishes the simple reference-package oracle from the separate independent-implementation stage. The isolated oracle gets a writable private home for ordinary library caches, separate from its declared outputs. Twenty-four materialization/grading controller checks pass. Reserved another $2 within the $100 ceiling ($89 held, $11 unallocated); launch remains gated on verified cleanup of 001.

Further diagnosis found that Tasksmith's shell tool schema itself advertised a maximum of 120 seconds, although our runtime accepted the agreed 600 seconds. Patch 0012 now configures both the advertised ceiling and handler enforcement per stage, retaining upstream's 120-second default for other callers. A regression verifies a 300-second foreground request is accepted, 601 seconds rejected, and the shared default unmodified; all 16 upstream artifact-stage regressions also pass. The complete 12-patch stack applies to the pinned upstream source and matches the tested implementation.

The stopped worker's many request/tool records exposed serial archive-transfer latency. Subsequent Iris exports use four bounded I/O threads, retaining deterministic manifest order and a verified download of every object. They also recheck unchanged local source hashes and handle empty credential lists without an accumulating scan buffer. Three focused export tests cover exact bytes, credentials spanning chunk boundaries, and symlink refusal. Model and sandbox stages remain sequential.

Diagnostic recovery now uses four bounded storage reads while retaining the 4 MB transport bound, original hashes, deterministic output order and completion marker only after every selected file passes. Two focused checks cover exact chunk reassembly and rejection of changed evidence.

Materialization 001 is closed without a candidate after 52 model requests. Its serial exporter stalled; a separately download-verified archive on the same host allowed stopping that owned exporter, after which normal sandbox cleanup passed. The concurrent exporter preserved all 323 final files, selected records were hash-checked on retrieval, and provider inventory found zero owned sandboxes at 17:41:55 UTC. The remaining redundant Iris export was canceled after evidence preservation. Retry 002 will use the corrected frozen factory with the same scientific scope.

Materialization 002 launched at 17:42 UTC from 497a191 on the approved sequential resource profile. Separately prepared native packaging now includes frozen source-license notices before bundle identity and validation are recorded; the packaging regression passes. This changes no generated scientific code.

Materialization 002 ended after 41 calls when the worker requested a 900-second shell timeout and the 600-second boundary raised a terminal ValueError. No command exceeded the limit, and cleanup/archive verification passed. Patch 0013 now returns correctable tool feedback for this invalid argument; transport/deadline errors remain terminal. Four focused timeout/native checks pass. The latest tool turns had no reasoning, prompting a proposed synthetic transport diagnostic. Complete trace inspection instead found 9 of 41 responses with reasoning, including 19,928 tokens in the first response. This disproves a blanket suppression claim; the diagnostic was not launched. No scientific content changed.

Retry 003 narrows materialization inputs to the public scientific proposal, approved policy and source/reference evidence; downstream grading review and validation work plans no longer enter this worker's context. Its private oracle adapts the source packages, while independent primitives remain the next stage's responsibility. Eleven focused checks pass, and the full 13-patch stack applies to the pinned upstream archive and matches tested source. Reserved $2 for retry 003 ($91 conservatively held, $9 unallocated); 002 cleanup is verified. The proposed reasoning diagnostic was removed without making any calls after trace inspection established actual reasoning output.

The native runner now archives its exact pre-trial task package with upstream content identity before validation, allowing later release staging from those same bytes. The packaging/archive fixture and sixteen upstream artifact regressions pass. A read-only transport check retrieved an existing 157-byte reference artifact through an expiring signed storage URL held only in process memory and verified its original hash; no credentials or URLs were persisted.

## 2026-10-16 — Keep grading grounded in the executed task

For tasks that have been materialized, the grading stage now receives the current public question rather than the full earlier specification and operator handoff. It retains source/provenance, actual materialization, repeatability and independent-execution evidence. This prevents outdated proposed work plans or status statements from becoming new requirements after their stage has passed. Four offline orchestration regressions pass, including independent-worker isolation and review/repair paths. The active materialization 003 checkpoint is unchanged; no generated scientific code was edited.

Native solver trajectories now bypass the per-file small-diagnostic cutoff while remaining inside the existing total 4 MB recovery bound, and are prioritized with native receipts. The two recovery regressions pass, including exact reconstruction of a 300 KB synthetic trajectory and refusal of changed evidence. This is an evidence-transfer change, not a model input/output limit or a scientific artifact edit.

## 2026-10-16 — Finalize an existing authored draft instead of continuing exploration

Materialization 003 produced a full 398,259-row exploratory oracle result in 380.5 seconds, with maximum absolute differences of 6.853e-6 for scores and 1.897e-6 for log2 fold changes; its high-level reference-package comparison on the reconstructed matrix matched saved scores exactly. It then continued investigating rounding details and diagnostic-script errors without submitting any candidate. Two identical reads preserved its original `derive.py` and `oracle.py` with hashes before a scoped SIGINT to the owned author process. These remain unsubmitted, unvalidated drafts; the observations are not accepted grading tolerances.

The general recovery path now accepts hash-verified prior worker files and uses the existing JSON-schema response adapter without an exploratory shell. GLM must return a complete artifact; the controller still performs actual derivation and isolated oracle execution, with error feedback for GLM repairs. A version-controlled finalization prompt clarifies direct input-directory semantics and reserves numerical calibration for the later validation stage. No generated scientific program was manually edited. The materialization suite passed eleven checks before the additional provenance check; the three affected submission/provenance cases also passed afterward. Reserved $2 for finalization 004 ($93 conservatively held, $7 unallocated). Launch remains gated on verified cleanup of 003.

Materialization 003 is terminal. Its final archive was download-verified, 770 selected diagnostics recovered with hashes, and archived draft bytes match the preserved capture. Controller cleanup passed and independent provider inventory found zero owned sandboxes. Finalization 004 can now start sequentially.

Materialization 004 ended after its first authoring request hit the 600-second client timeout without a response. All 50 selected diagnostic files were recovered from a download-verified archive, cleanup passed, and no owned sandbox remains. Retry 005 keeps the captured GLM programs and finalization prompt unchanged, extending only authoring request wait to 1800 seconds within the two-hour campaign. This accommodates service/generation latency; the evidence does not identify the provider-side cause. Scientific computation and solver limits remain 600 seconds. Reserved $2 ($95 conservatively held, $5 unallocated).

Reviewing earlier evidence found prior content-fidelity failures with strict JSON-schema decoding (including specification 015), followed by a usable submission-only tool result in specification 016. Prepared finalization to use the existing submit/revise tools without a shell, retaining local schema and executable validation. Three focused submission/provenance tests pass. This is a fallback factory correction; active session 005 retains its frozen checkpoint and has not been altered.

Stopped the pending first request of 005 after revisiting the saved format-comparison evidence; this is an operator protocol correction, not a demonstrated provider failure. Finalization 006 uses submit/revise only, retaining schema validation and controlled execution. It is gated on 005 cleanup. Reserved $1 using the published Linux CPU/RAM/disk rates: 4 CPU, 8 GiB, all 10 GiB charged for 7500 seconds is $0.69225, plus $0.10 storage margin, below $1. No credits or actual invoice are assumed. Aggregate holds are $96 with $4 unallocated.

Session 005 is terminal with one canceled request and no candidate. The final archive and selected diagnostics were hash-verified; controller cleanup passed and independent provider inventory returned zero sandboxes. Finalization 006 is clear to launch.

Finalization 006 returned its first complete candidate after 664.46 seconds. Controlled derivation rejected an inventory mismatch and returned it to GLM for repair. The submitted declarations include directory prefixes while derivation roots already provide them. Future schema descriptions and the finalization prompt now clarify the root-relative convention, and runtime mismatch feedback lists missing/unexpected paths. These are generic interface improvements; active checkpoint 006 and its generated artifacts are unchanged.

All twelve focused materialization regressions pass after the path-contract clarification. The running session remains frozen at 0698fbc.

## 2026-10-16 — Fixed-group task materialization passes

Finalization 006 completed with three GLM submissions. It repaired declared-path prefixes and a sparse-matrix dimension check through controlled feedback. Final derivation plus isolated oracle execution took 24.16 seconds; the oracle itself reported 14.4 seconds and produced the full 398,259-row endpoint. Four public inputs and one private answer artifact passed identity/inventory checks. No data-reconciliation warnings occurred on the fixed provider files. The archive and downloaded evidence hashes are verified, cleanup passed, and no owned sandbox remains. Numerical fidelity is still pending.

Prepared grading 002 against unchanged materialization 006: a fresh answer-isolated implementation precedes numerical calibration, deterministic grader construction, separate probes, review and optional repair. Authoring request wait is 1800 seconds; science/solver remain 600 seconds and verification 120 seconds. Reserved $1 using the recorded profile bound, bringing conservative holds to $97 with $3 unallocated.

Release staging and publication helpers are now preserved alongside the experiment. They bind the exact native package to scientific-control and Harbor receipts before staging, use the upstream release verifier, replace only prior manifest-managed Hub paths with optimistic concurrency, and retain a separate fresh-download verification step. The standard upstream quality-loop label remains unverified because this revised scientific-content workflow is different; its actual executed checks will be reported explicitly. These helpers have not yet staged or uploaded a release.

Publication now guards both the release commit and its subsequent registry update against concurrent Hub changes. Two focused regressions pass for the expected revision chain and rejection of a changed parent; obsolete-path removal is limited to literal prior-manifest paths. No upload has occurred.

The Harbor packager now appends the actual runtime input/output directories to the unchanged GLM-authored scientific contract. Previously the question referred to the run's directories without locating them. The release gate checks this deterministic composition. Three focused packaging/native-dispatch regressions pass, including agreement between the public paths, Docker input location and verifier output location. Grading 002 is unchanged and has completed its independent answer-isolated execution; numerical calibration is active.

## 2026-10-16 — Resume submitted grading artifacts instead of reauthoring

Grading 002 submitted a candidate and passed five initial controller cases, including the answer-isolated independent implementation. Separate probe generation exhausted the remaining operation allowance after 315 model calls overall. The final archive was download-verified; selected recovery records match its hashes despite a truncated diagnostic stream. Controller cleanup and independent provider inventory both confirm no owned sandbox remains. Scientific probe validation and final review remain incomplete.

Recovery verifies saved artifact hashes and exact scientific context, reexecutes the unchanged independent program, and reruns the submitted grader controls before continuing with separate probes and review. No scientific code or acceptance rule is manually patched. The review prompt now explicitly separates measured evidence from candidate prose and challenges arbitrary margins and unsupported method-detection claims. Reserved $1 for grading 003, bringing conservative holds to $98 and leaving $2 within the existing ceiling; these are not actual billed charges.

The full 18-test grading/recovery suite passes. Replaced a stale three-output fixture assumption with synthetic replay identity checks, including rejection of changed bytes, and isolated orchestration cases from the active campaign recovery setting. These test-only corrections do not alter the running checkpoint.

## 2026-10-16 — Narrow the probe-author boundary

The active probe worker reconstructed raw-analysis helpers instead of limiting itself to result mutations. Inspection found that its context unnecessarily inherited the original notebook, oracle and independent-solution code, and raw-input paths. Future probe sessions receive only the combined public question/acceptance rules, named checks, output paths and execution limits. Raw task inputs are made inaccessible during probe authoring, checked under the probe user, then restored for later stages. Six orchestration regressions pass, including isolation and review/repair flows. This is a general stage-boundary correction; the active grading 003 checkpoint remains unchanged, and efficiency improvement has not yet been measured in a new model run.

Grading 003 was stopped after 38 probe calls without a submitted suite. Its fresh independent result matched the prior hash exactly and all five initial controls passed again. The complete archive and selected records are verified; controller cleanup and provider inventory both show no remaining sandbox. Prepared grading 004 from the narrower probe interface, reusing the same verified submitted programs. Reserved $1 ($99 conservatively held, $1 left for native validation); no scientific artifact was manually changed.

A further workspace-hygiene correction clears independent-worker scratch files before a future probe author starts, after the controller has preserved the submitted program and outputs. The first restricted run's trace showed its prior `solution-case` directory remained visible, although raw inputs were inaccessible. Six affected orchestration tests pass. This correction does not change the active grading 004 checkpoint.

## 2026-10-16 — Finish the current run, then stop for the day

The user asked to finish the current work and wrap up for today. Grading 004 may complete within its existing allowance, including its already configured review/repair path. No replacement campaign, native Harbor trial, blind solver attempt, publication or viewer update will be launched tonight. Preserve the outcome, verify archive downloads and cleanup, then leave issue 19 open with the remaining work recorded.

The user subsequently requested an immediate pause. Grading 004 stopped during GLM repair: 14 probes were submitted, 12 passed and two failed because the grader duplicated a check ID; review requested repairs and documented coverage/claim limitations. Recovered 29 original small records before canceling the host (partial recovery, not complete-archive verification). Deleted the remaining Daytona sandbox; provider inventory found zero issue-19 sandboxes. Iris confirmed the host KILLED at 23:52:26 UTC. No replacement or downstream run was launched.

## 2026-10-19 — Resume with the submitted probe suite

The user resumed work. Added hash-checked recovery of submitted probes from the partial pause snapshot, bound to the unchanged grader contract and recorded host/provider teardown. Grader recovery still verifies the complete scientific context against the earlier verified archive. The independent program and every grader/probe control execute again; no previous acceptance is reused. The new path skips probe authoring, retains the original 14 probes, and proceeds to fresh review and GLM repair. All 21 focused grading/recovery tests pass; Ruff checks pass. Reserved the remaining $1 for grading 005, bringing conservative holds to $100. Holds are not actual provider invoices; subsequent native trials require reconciliation of documented unused reservations before launch.

Reconciled materialization 005 against its verified one-sandbox cleanup and provider absence record: at most 556.48 seconds at 4 CPU/8 GiB/10 GiB. Published rates rechecked October 19 give a $0.05137 running-resource bound, ignoring free disk/credits. Retained $1 of its original $2 reservation rather than claiming an invoice, releasing $1 for later native validation. Aggregate holds are again $99, with $1 unallocated. Detailed evidence and arithmetic are in budget-reconciliation-20261019.json.

The active repair worker repeatedly reconstructed and reran the frozen suite before submitting. Added general repair-stage guidance for future runs: fix reported defects, preserve frozen checks/probes, use targeted local checks and submit for controller execution rather than repeatedly rebuilding the suite. The public addendum states observable acceptance limits, not universal wrong-method detection guarantees; calibration history stays private. Active grading 005 remains frozen at 8265bb8.

Grading 005 completed: all 19 final controller controls passed and GLM review accepted the repaired candidate. The archive is download-verified and a fresh provider query found zero owned sandboxes. Operator review nevertheless identified unsupported universal method-detection claims in the public prose. Added a constrained GLM text-only correction stage that cannot change grader code or checks, followed by fresh controls and review; it cannot launch open-ended scientific repair. All 25 focused tests pass. Reserved $1 for grading 006, bringing conservative holds to $100 pending further evidence-based reconciliation. Native validation and publication remain outstanding.

Reconciled materialization 004: its verified single sandbox existed for at most 729.24 seconds from campaign start through provider absence, bounding running resource usage at $0.06731 with no credits assumed. Retained $1 of the prior $2 hold, releasing $1 for native validation; aggregate holds return to $99. This is a conservative reservation reconciliation, not an invoice. Grading 006 is submitted at 7a758e4.

Grading 006 completed with 19/19 fresh controls passing and review accepting packaging. GLM used one prose-correction request and two review calls; grader code and check inventory are byte-for-byte unchanged from 005. Independent output hash is unchanged. Archive download and separate provider cleanup are verified. Operator review accepts native validation with the documented coverage/calibration caveats. Reserved the remaining $1 for three sequential native trials: oracle, no-op and one ten-minute blind GLM solver. Publication is still gated on their evidence and fresh-download verification.

Native 001 exposed a runtime dispatch bug before sandbox creation: the upstream supervisor used default host Python, which could not import Repo2RLEnv and had no Harbor executable. No supervisor receipt or model request was produced. Stopped only its native process; the bootstrap archived the failure and the host terminated. The launcher now passes sys.executable explicitly, preserving the pinned environment; both focused native dispatch tests pass. Native 002 reuses the unused $1 reservation and unchanged scientific artifacts.

Native 002 passed Harbor oracle (1) and no-op (0), but the first solver request failed at the local inference gate: it required max_tokens even when the output allowance was None. Zero provider calls were recorded, so this is not a solver performance result. Archive and all three provider ownership labels are verified clean. Fixed the generic gateway to permit omitted/null output limits only for uncapped scopes, retaining bounded-scope validation. Seven tests pass, including the actual pinned Harbor LiteLLM client against a local fake provider with no output cap. Native 003 is prepared with unchanged task science. Its $1 reservation comes from reconciling materialization 003's verified lifetime (running-resource bound $0.38025, retaining $1 of its prior $2 hold); aggregate remains $100.

Native 003 succeeded: oracle 1, no-op 0, blind GLM solver 1, no exceptions. The blind trial took about 523 seconds overall, used 18 successful model requests and passed all nine checks. Trajectory review found computation from supplied inputs/package sources, without private-answer access or network retrieval. Native and scientific evidence bind to bundle sha256:e016fae75540a542a8395d9acb137953dcea4454a372f5c93dd83c9e5e481312. Archive/package downloads and all three provider cleanup labels are verified. The release gate passes. Staging corrections wrap the controls list in the upstream dictionary schema and retain the stable task basename; neither changes scientific content.

Scientific release 001 was published publicly at immutable HF commit 9eeabefd3761655a5f01ac3f46df1b060610355a. A forced fresh download verified all release files and matched the exact native bundle hash. Publication used optimistic parent guards and removed only obsolete prior-manifest paths. Final evidence: 19 scientific controls pass; Harbor oracle 1, no-op 0, blind GLM 1 without exceptions. Provider queries confirm zero remaining trial sandboxes and Iris is terminal. No further runs or viewer changes are scheduled; issue 19 stays open for user review.

### 2026-10-19 — Current published-task explorer

Replaced the legacy campaign explorer with the current notebook, exact published
solver question, successful native-003 trajectory, and nine pipeline stages.
Recorded prompts, inputs and outputs are separated; raw documents are collapsed
and code is highlighted. The viewer now builds entirely from versioned small
artifacts, including recovered specification/materialization inputs and the
setup worker's initial message/tool payload. Large data remains in the release.

Validation: all five views and nine stage links work in Chromium; the solver
commands expand correctly, no JavaScript errors or 390-pixel layout overflow.
All 69 repository links resolve locally; the displayed instruction matches the
freshly downloaded published file byte-for-byte. Ruff passed for the two viewer
scripts. No new scientific, model or sandbox execution was performed.

### 2026-10-19 — Bioframe transfer candidate selected

Hold pipeline PR extraction pending a second-notebook transfer check. The user
selected bioframe's motifs-to-peaks tutorial after excluding IL6 and single-cell
analysis. Pinned source and initial access evidence are in `transfer/bioframe/`.
Existing prompts remain unchanged. Syntax parses; ENCODE metadata confirms two
released GRCh38 files. Conversion was not started because the shared heavy-work
lock was held. No model or paid execution was launched.

### 2026-10-19 — Bioframe conversion and frozen preparation inputs

The user explicitly authorized proceeding without the shared lock for this
lightweight work. Load was below 0.1 and available memory above 4 GiB.
Unchanged conversion first rejected Jupytext's file-pairing `formats` metadata.
A general converter change admits and records that string while retaining
explicit exporter options and rejecting other unknown/malformed Jupytext
metadata. Fourteen conversion tests passed. The pinned notebook now converts
with all 14 code cells and 12 Markdown cells preserved; its source is unchanged.
The failure record is retained beside the conversion receipt.

JASPAR's official About page explicitly states CC BY 4.0. Preparation is
configured for one GLM-5.3 medium call, using the unchanged packaged prompt and
existing CPU/memory/disk/time settings. The seed supplies provenance only;
scientific task design and exports remain the worker's responsibility.

### 2026-10-19 — Bioframe preparation 001

The existing preparation worker completed one GLM-5.3 medium call in 39.79
seconds; all 21 canonical prompt hashes still match the frozen baseline.
Recovered artifacts were verified against the remote export hashes. Its
append-only code serializes `df_peaks_maxmotif_clean` to CSV and introduces no
scientific computation. The original analysis remains an exact prefix.

Inspection flags two generated prose claims for later validation: subtracting
blacklist intervals can trim/split peaks, despite the response's wording about
removing entire peaks; the added HFF attribution was not established by the
supplied intake metadata. Original worker output is preserved without edits.
No scientific execution has occurred. The next setup session uses the existing
prompt, two reference-test allowances, a 600-second offline reference limit and
$5 Daytona reservation ceiling; only campaign/input paths differ from setup 001.

### 2026-10-19 — Bioframe setup 001 and archive verification

The existing setup worker completed in 312.39 seconds (40 GLM requests). Its
one controlled reference test passed offline in 4.796 seconds, with 0.537 GiB
maximum child RSS. The source changes are only three input-path substitutions;
the worker selected pandas 2.3.3 after observing pandas 3 copy-on-write behavior.
Independent download verified the 2.48 MB endpoint CSV: 40,557 rows, nine columns.
Provider lookup found zero owned sandboxes; the setup/audit/recovery hosts are
terminal. No source science or generated outputs were manually repaired.

The trace exposes a general compliance gap: the worker ran full analyses through
its setup shell despite the prompt's `test_reference` rule. Thus the controller's
one test is not a count of all scientific computation. Original operation
records are retained. Same-worker exploratory agreement is not independent
scientific reproduction. Also, the earlier operator HFF concern was mistaken:
the original source narrative explicitly identifies HFF. The inspection was
corrected; the worker output remains unchanged.

Archive recovery skipped the 401 KB uv lockfile under its former 256 KB
per-file diagnostic threshold. A general fix prioritizes reference replay
prerequisites and permits reference lockfiles within the existing 4 MB total
transport bound. Three regression tests passed. A read-only recovery job
retrieved the original hash-verified bytes without models or sandboxes.
The next programmatic replay uses the same two-repeat profile as the first
notebook, with only seed/campaign/evidence paths changed.

### 2026-10-19 — Bioframe repeatability and fresh specification context

The programmatic replay completed in 47.01 seconds: two fresh-process repeats
were byte-identical to the original CSV, with zero model calls and verified
worker cleanup. This is finite repeatability in one locked environment, not
independent scientific reproduction or software portability.

The next specification context is generated by the existing hash-checking
builder from the verified bioframe evidence. Shared scientific/resource policy
is retained; the previous task's manually agreed expression/cell-group scope and
historical revision feedback are omitted. No replacement notebook-specific
scientific scope is supplied. The existing read-only package-inspection option
is enabled so the worker can check current tool semantics/defaults. Canonical
prompts remain unchanged, and task instructions/comparison proposals remain GLM
output. This input/configuration selection is recorded as operator orchestration.

### 2026-10-19 — Bioframe specification 001

GLM returned a draft in 548.25 seconds across 20 read-only inspection/submission
requests. The question contains two scientific analysis steps, not an API-call
recipe. It correctly describes blacklist trimming/splitting, assignment before
subtraction, and motif-score ties. Its private handoff explicitly leaves
precision, duplicate keys, missing scores and negative controls to executable
validation. Original output is preserved; no manual scientific repair was made.
The next existing materialization stage receives this fresh proposal, with no
historical Scanpy author draft or revision feedback. All canonical prompt hashes
remain those of the transfer baseline.

### 2026-10-19 — Bioframe materialization 001

Construction completed in 763.07 seconds (67 model requests); the first
controlled submission passed. It copies the three original inputs byte-for-byte
and projects the reference's header to the public schema. The separately
executed oracle passed answer-access isolation and its output SHA-256 equals
the projected reference's SHA-256. The controller call took 2.07 seconds.

The worker authored a plain-Python interval implementation rather than calling
the source library. Same-author self-testing does not replace the separate blind
implementation/controls still required. No scientific output was manually
repaired. The next existing grading profile starts fresh, with no historical
grader/probes or task-specific feedback from the first notebook.

### 2026-10-19 — Generic native directory aliases

The fresh task instruction uses the conventional absolute `/inputs` role path,
while native packaging mounts files under `/workspace/inputs`. Add generic
`/inputs` and `/outputs` symlinks to the native image and describe them in the
controller-owned runtime note. This preserves authored scientific text and
supports both conventions for every task. The existing bundle test passes;
the forthcoming native trials will exercise the resulting image. The current
grading job remains bound to its original checkpoint and scientific artifacts.

### 2026-10-19 — Explicit release provenance

The operator release stager still had the first task's dataset ID, description,
methodology, source-license path and seed path embedded in code. Replace those
with required `release_metadata` configuration. Missing metadata cannot silently
fall back to the prior task. The selected seed must be unambiguous, license
text hashes are checked, and release attribution must equal the native bundle's
record. Optional bundled source provenance must match the selected seed too.
Seven focused release/packaging tests pass, including cross-wired source and
license failures. This changes publication metadata handling, not task science.
Bioframe source/data attribution is recorded separately from the Scanpy case.

### 2026-10-19 — Owned release destinations

The publication wrapper also assumed the original dataset already existed.
It now accepts the explicit staged destination in the authenticated personal
namespace, supports a new public repository, and retains optimistic concurrency
for existing managed releases. It refuses private or unrelated destinations and
only removes obsolete paths listed in the previous release manifest. Seven
focused metadata/publication checks pass. No upload has been performed for the
Bioframe transfer; independent grading remains active.

### 2026-10-19 — Identity semantics and independent-output failures

The first Bioframe quality campaign is still frozen at `4b03cba`. Its blind
program executed but produced 40,572 rows, against 40,557 reference rows. The
GLM grader's live inspection attributed the difference to 15 duplicate input
coordinate keys with conflicting fold-change annotations. The shared rows agree
numerically. The first submitted grader rejected the extra rows and therefore
failed the controller's mandatory independent-output control. The worker then
changed its local comparator to accept multiple fold-change records per key;
that change still requires probes/review and is not accepted for publication.
Original scientific artifacts remain untouched.

Prepare a general next-version change: materialization must inspect actual entity
keys and state multiplicity/conflicting-annotation rules in the public question.
Grader guidance and failed-control feedback now distinguish independently executed
code from independently established correctness. They explicitly allow a blocker
instead of weakening the scientific question to force the comparison attempt to
pass, and reject unsupported supersets as a claimed representation equivalence.
The internal flag is renamed from `alternative_validated` to
`alternative_executed` to describe its actual evidence. No notebook, field name,
scientific method or expected answer is embedded in these changes. Twenty existing
grading tests pass; these advisory prompt changes have not yet been tested by a
new model run and do not alter the active campaign.

Before the next construction run, the same general guidance also requires checking
claimed input formats/headers against the staged bytes, rather than treating the
source's reader arguments or a proposal's description as evidence of the file
layout. No data-format claim about this seed is changed by the operator.

Construction replacement 002 is prepared with the same seed, specification,
reference, replay and resource settings as 001. It will exercise the general
next-version materialization prompt; there is no task-specific scientific repair
in its configuration. Do not launch it until the original grading campaign has
terminated and provider absence is independently verified. Its status is prepared,
not submitted. The original transfer campaign still supplies the unchanged-prompt
baseline, including its unsuccessful and broadened grader candidates.

### 2026-10-19 — Stop unresolved independent comparisons before grader repair

The frozen campaign's review requested cosmetic/schema-attribution changes, but
its rationale explicitly excused unverifiable extra annotations as an accommodation
forced by the mandatory independent-output control. That accommodation is not an
acceptable reason to publish. The current generated artifacts remain unchanged;
passing this suite would not resolve the known public-question conflict.

Add a mechanical next-version boundary: when reference/oracle and other basic
controls pass but only the independent comparison fails, preserve the original
candidate and controls and return `independent_comparison_unresolved`. Stop before
probes, review or further grader repair can turn that output into a required answer.
Apply the boundary to fresh, resumed, contract and post-review-repair paths. Other
basic grader failures remain repairable. This classifies an unresolved comparison;
it does not decide whether the reference, question or independent program is wrong.
No generated scientific artifact is rewritten and no reward is supplied by this
controller decision. Existing native packaging requires validated grading and thus
cannot package this status.

Generic reviewer/probe guidance now also says that disclosing an unsupported
superset is not evidence of validity, and asks for plausible unsupported additions
when a claimed equivalence accepts multiple values per entity. No source-specific
field or method is encoded. Thirty-three offline grading tests pass, including
unaltered candidate preservation and early stops on all orchestration paths. New
model behavior remains untested. Native configuration selects the prepared 002
replacement artifacts, which do not exist yet, so the known 001 candidate is not a
publication target even if its old review profile later accepts it.

### 2026-10-19 — Original Bioframe quality run ended incomplete

Grading 001 timed out in repair after 6,889.51 recorded stage seconds and 244
requests (82 independent, 32 grader, 124 probes, 1 review, 5 repair). No final
candidate/review, native attempt or release exists. Nineteen probes passed the
broadened candidate, but the contract conflict remains; review excused rather
than resolved the unsupported additions. This is a factory/control-assumption
failure, not a broken-notebook result. Preserve the original statuses and the
operator hold separately.

The full 1,316-file archive passed download verification; selected evidence and
hashes are retained under `transfer/bioframe/grading-runs/001`. Three omitted
input payloads were reconstructed losslessly from recorded components and matched
their original archive hashes exactly. The diagnostic transfer was partial; full
traces remain in the configured archive. Unsubmitted workspace files are gone,
so do not claim a completed repair artifact. Provider absence was independently
verified and the Iris job is terminal. Construction replacement 002 can now be
submitted using the checkpointed general guidance and unchanged earlier evidence.

### 2026-10-19 — Construction 002 provider rejection and diagnosis plan

The replacement ran from `095a3f1` and independently inspected the duplicate entity
keys before generating a candidate. It ended incomplete after 460.90 stage seconds:
12 responses and a thirteenth `BadRequestError`, before any submission. A debugging
command emitted 1,235,651 log bytes and the next saved request is 1,594,921 bytes.
This suggests context overflow; the discarded error body prevents confirmation.
Preserve the original failure/uncertain receipt, not a retroactive diagnosis.
Cleanup and independent provider absence are verified; no model/sandbox worker
from this campaign remains active.

Add general safe rejection metadata to the Chat adapter: definite HTTP errors get
an explicit status/category and retained `http_error_received` request state,
without logging private endpoint/error text or retrying. Twenty-one adapter tests,
Ruff and its type check pass. Prepare one hash-verified recorded-request diagnostic
through the existing schema-probe launcher. It executes no returned tools, receives
no Daytona credential, and makes at most one completion request with a two-minute
client timeout. Nine diagnostic/schema tests pass, including private-value
redaction and exact request forwarding. Tool-output preview restoration is an
unresolved user preference because earlier extra size limits were removed; no
preview/token/input/response cap has been re-enabled.

Prepare the existing optional tool-preview path without enabling it in the active
scientific profiles: preserve the full tool result in a separate original trace
record before applying a configured preview, and use the upstream one-third-head /
two-thirds-tail presentation (8,000 + 16,000 characters at its 24,000 default).
The preview has an explicit truncation marker and a linkable full-result record;
model token/input/response settings are unaffected. All active scientific profiles
still set `tool_output_chars=None` pending the user's clarification. Twenty-two
adapter tests and its type check pass, including full-result retention and unchanged
unbounded generation settings. The diagnostic is submitted but awaiting reserved
Iris capacity; no diagnostic model call or Daytona sandbox has run yet.

### 2026-10-19 — Rejected-request replay confirms context overflow

The diagnostic completed with one completion request and a read-only metadata
query, no task tools and no Daytona credential or sandbox. The original request's
SHA-256/bytes were verified first. The endpoint reproduced HTTP 400 and reported
its 262,144-token context window versus at least 262,145 prompt tokens. This is
an input-context rejection; the provider's zero-output allowance is a consequence
of the oversized prompt, not an output-token cap supplied by the client. Preserve
the stated lower bound rather than reporting an exact token count.

The diagnostic host is terminal and its archive passed full download verification.
Small original records are retained in `transfer/bioframe/request-rejection-runs/001`.
Its archived execution timestamps show that it had already run while the earlier
client observation still said PENDING; the prior inference that no call had run
was stale. Use the durable request ledger and archive for execution claims.

### 2026-10-19 — Reuse recorded worker code and keep diagnostics concise

With the preview-policy clarification unanswered, retain the existing unbounded
setting; do not infer approval for a new limit. Add general printing guidance to
tool-worker prompts: aggregate checks/representative examples, full listings in
scratch files, targeted inspection. Construction also distinguishes scientific
content from incidental ordering/serialization when the public question frees
those choices, and prioritizes reuse of supplied prior worker work over rebuilding
an independent implementation in the authoring stage.

Prepare construction 003 through the factory's existing `prior_author_files`
input. Its draft consists of unchanged original GLM-authored scripts/instructions and
the original controller execution record from construction 001; hashes and provenance are
recorded, and the generic loader verified both. The earlier oracle matched the
recorded reference, but its public contract still needs GLM review/repair. No
scientific code or annotation-selection rule was manually changed or supplied as
new task-specific feedback. Scientific validation remains a separate later stage.
The native configuration selects 003 plus a future fresh grading 002; neither is
validated or launched yet. Printing guidance is advisory, not a byte/token cap.

### 2026-10-19 — Explicit construction mode for reused worker drafts

Construction 003 was submitted at `dad9f99`, then cancellation was requested after
checking the routing: `prior_author_files` automatically selects the legacy
shell-free finalization prompt, so the updated construction prompt was bypassed.
The parent reported PENDING with no tasks while Daytona already showed one owned
sandbox. Do not infer no execution from that mirror. Reconcile cancellation and
cleanup before launching another worker; preserve any available original outputs.

Separate the choice of prior input from the authoring mode: explicit
`authoring_mode: construct` keeps the current construction prompt and inspection
shell while admitting hash-verified prior GLM work. Legacy configurations retain
their finalizer behavior. Thirteen focused materialization checks pass, covering
fresh construction, legacy finalization, and construction with prior files.
Prepare 004 using this mode; no manual scientific artifact changes or new caps.

Cancellation 003 converged to KILLED. No recovery manifest was available. The
remaining owned Daytona sandbox was explicitly deleted; a fresh provider query
at 23:03:13 UTC confirmed zero. Model-request count is unavailable; do not count
this as an unexecuted campaign merely because the parent mirror was PENDING.

### 2026-10-19 — Stop exploratory reimplementation; prepare shell-free handoff

The live construction 004 trace confirmed the intended construction prompt and
prior-file context, but after 22 successful model responses it still had no
submission and had repeatedly launched complete alternative implementations.
Diagnostic output stayed below 10 KB per result rather than overflowing context,
but concise-output guidance did not prevent unnecessary recomputation. Sent
SIGINT only to the verified stage process in this campaign, allowing its existing
archive and cleanup finalizers to run. This is an operator stop, not a scientific
rejection or an exhausted campaign budget. Original scientific files are unchanged.
Provider readback at 23:31:17 UTC confirmed zero campaign sandboxes; final archive
recovery/host termination still needs confirmation.

Update the existing shell-free finalization prompt generically: prior code may
be exploratory or executed, scientific entity/multiplicity/conflict rules must be
explicit, input format claims need parsing/evidence support, and unfinished
inspection commands prove no findings. A proposed next pass reuses the original
GLM code and complete recorded inspection trace rather than adding hand-authored
scientific corrections. Controlled execution and separate blind comparison remain
required; this changes tool availability, not model/context/output limits.

Archive recovery confirmed terminal FAILED with the stage's original incomplete /
CancelledError result, cleanup true, and 22 successful responses over 1,464.28 s.
The full archive passed download verification. Retain the complete unedited
92,232-byte inspection trace as handoff evidence alongside unchanged prior code;
completed inspections did establish useful findings, while the last computation
was interrupted. Earlier completed computations did not time out; distinguish
those results from the final unfinished command. Do not characterize all
exploration as unsuccessful or claim a validated candidate.

### 2026-10-19 — Shell-free finalization 005 executes in one response

The finalizer returned one complete candidate and passed its first controlled
derivation/isolated-oracle submission. Stage elapsed 391.43 s; the controller
process took 2.12 s. Three inputs remain byte-unchanged and the 2,484,423-byte
oracle output matches the projected reference hash. GLM clarified multiplicity
and the retained input annotation, corrected the unsupported input-header claim,
and revised only the oracle documentation. Executable oracle/derivation logic
is unchanged; no generated science was
manually patched. The full unedited transcript handoff retained both successful
observations and failed/unfinished commands rather than operator-written rules.

The response used 48,726 prompt tokens and 52,277 completion tokens, including
45,800 reasoning tokens, at medium effort with token/context/output caps unset.
This is a single observed recovery pass, not a fresh end-to-end timing estimate.
Archive/download and provider cleanup are verified. The archived bootstrap
completed, but terminal scheduler state still needs confirmation before fresh
grading 002. Scientific acceptance, native controls, blind solving and publication
remain pending.

Scheduler readback at 23:48 UTC confirmed finalization 005 and its task SUCCEEDED.
Proceed to fresh grading 002 with no resumed grader/probes/independent code from
the earlier inconsistent campaign.

### 2026-10-20 — Prepare source-driven explorer profiles

Separate notebook/task/run selections and narrative metadata from the shared
HTML renderer so the same layout can show the transfer case. The currently
published index remains unchanged while the new renderer is checked against
the existing release and the pending Bioframe profile. Grading 002 remains
frozen at `7fd3398`; viewer work changes no active scientific artifact or prompt.

Preserve three additional original model-input records for the viewer against
their original archive hashes, including the exact setup input and initial
specification/draft requests. Do not substitute a description or hand-assembled
subset for the recorded input. The reading view distinguishes prompts, inputs
and outputs, keeps raw documents collapsed, and derives control/reward displays
from selected evidence rather than hardcoded case outcomes. Browser checks use
the selected trajectory's metadata rather than a fixed turn count.

The shared renderer built both selected profiles locally. All 59 previously
recorded common source hashes stayed unchanged for the existing release. Ruff
checks pass. Headless browser checks passed all five views and nine selected
stages for each profile, without mobile overflow or JavaScript errors. The
Bioframe reading view correctly has no solver trajectory yet. Browser launch
needed normal IPC access outside the execution sandbox; no model or scientific
run was involved. The published index was not rewritten.

### 2026-10-20 — Recover an unfinished grader without repeating model development

Add an explicit `resume_grader_draft_directory` recovery mode for a campaign
that submitted an independent program but not a complete grader. It requires a
download-verified archive, verified cleanup, unchanged worker bytes and the same
scientific context. Reexecute the saved independent program without answer
access; do not reuse its acceptance or old output files as new execution proof.
Supply the complete verified grader transcript only to a shell-free grading
worker, which submits/repairs the full candidate under the existing typed schema.
The probe author does not receive that transcript or grader code. No prior
candidate or acceptance is fabricated. Normal fresh/full-resume paths retain
their behavior, and unresolved independent comparisons still stop.

This is a generic optional recovery path, not a change to the active campaign
(frozen at `7fd3398`) or any generated scientific artifact. The canonical grader
prompt distinguishes shell-free recovery and incomplete observations. Forty-three
focused offline grading/recovery tests and Ruff pass, including context/byte
rejection, independent reexecution, shell absence, probe isolation and comparison
stops. No model or sandbox was launched for these tests. Model caps remain unset.

The explorer default now links to its single canonical case profile. A checked
rebuild reproduced the earlier reading view exactly apart from pinned Git
revision links; the published index remains unchanged until case validation.

### 2026-10-20 — Match native solver metadata to endpoint capacity

A preflight of the pending native solver found stale `max_input_tokens=120000`
metadata. The installed Harbor client uses that field as its context capacity
for proactive summarization and message unwinding, rather than as a generation
length parameter. Correct it to 262,144, the endpoint capacity recorded in the
original diagnostic provider rejection (request-rejection run 001). This removes
an artificial smaller context assumption; it does not increase the provider's
window or impose a completion-token allowance. No change reaches the active
scientific-validation campaign.

Three focused offline tests passed, including the real pinned Harbor client's
capacity lookup and observed outbound request with neither `max_tokens` nor
`max_completion_tokens`. Native oracle gating and solver-failure acceptance
remain covered. The synthetic local endpoint made no real model or sandbox
calls. Local peak RSS was 231,120 KiB. Recheck this metadata if the provider's
capacity changes; the recorded value is service-specific, not a universal GLM
or Harbor default.

### 2026-10-20 — Validate probe execution before freezing the suite

Fresh grading 002 passed its five initial controls, including the independently
executed program. The probe worker used 105 responses but submitted only two
controls. Its sole wrong-result script failed an assertion before modifying the
CSV, so no executed wrong-result control exists for that suite. The independent
review correctly requested probe repair and identified inconsistent explanatory
counts/precision claims. The orchestration instead routed this to a grader-only
repair while keeping the invalid probe frozen, making that route unresolvable.
At 01:28 UTC, interrupt only the verified stage process so its existing archive
and cleanup path runs. Preserve the original result/review and mark it incomplete;
no generated scientific artifact was changed manually.

Add a general execution-only preflight to probe submission. Run each mutation
on a fresh reference copy without loading or invoking the grader, preserve
execution/mutation receipts, and return recoverable script errors to the probe
worker. Freeze only a successfully executing suite, then evaluate it against the
grader. Require actual changed files; assertion failures and no-ops are not
scientific counterexamples. The canonical prompt also asks for a wrong-value or
wrong-association probe preserving entity identities/counts where applicable,
rather than relying only on extra/missing records.

An optional recovery mode supplies the original hash/context-verified probe
suite and sanitized execution failures to a shell-free GLM probe worker. It
excludes grader reports/results and does not reuse prior acceptance. Reexecute
the independent program and grader controls; let GLM author all probe fixes and
subsequent grader/prose corrections. Fifty-three focused synthetic tests pass,
covering no-op/assertion rejection, absence of grader execution/feedback, byte
and context checks, recovery orchestration and existing control gates. No new
model or sandbox was launched for the tests. The current campaign remains frozen
at its original revision; recovery has not launched yet.

### 2026-10-20 — Launch verified probe recovery 003

Grading 002's complete 1,150-file archive passed download verification. The
bounded log transport restored 301 files; these are a subset, not the complete
archive. Preserve 37 original small files against their hashes, including the
unchanged candidate, independent program, probe suite, review and all seven
control records. The ledger has 182 received responses and one uncertain repair
request. Recorded elapsed time is 5,991.98 seconds. Cleanup and independent
zero-sandbox readback passed; Iris confirmed host and task FAILED.

Automatic approval initially rejected pushing the broad evidence payload. Audit
the exact small-file set and record eligibility, hashes, source permissions and
exclusions. All original hashes match; the model-input source components exactly
match already-public setup files, no credential/private-service endpoint patterns
were found, and SQLite contains digests/states and allowances only. Full traces,
host logs and biological files remain outside this Git payload. The reviewed push
then succeeded at `6435ed748b59293ffb58bf96463652246d979464`.

Recovery 003 was submitted at 01:39 UTC from that committed revision, with the
recorded `grading-config-003.json`. It reruns the independent program and grader
controls, reauthors probes through GLM with execution-only feedback, freezes the
executable suite, and repeats scientific review/any needed grader repair. No
prior acceptance is reused. Reserved CPU, sequential execution, offline science,
existing time/spend ceilings and unset extra model caps remain unchanged. A
stale temporary packing config was caught before submission; discard that
unlaunched payload and assert the target campaign/config identity when repacking.

### 2026-10-20 — Fifteen controls accepted; align wording before packaging

Recovery 003 completed in 1,164.28 seconds with six received responses (three
probe, three review). The unchanged independent program was reexecuted without
answer access. All 15 final controls passed: five initial cases, two valid
representations and eight wrong-result probes. All ten submitted scripts passed
execution-only preflight. The complete 231-file archive passed download/readback
verification; bounded transport restored 201 files. Provider absence and terminal
SUCCEEDED host/task state were independently checked.

The review accepted packaging but its narrative says 16 controls and cites some
author-side local mutations as though separately executed. Actual receipts show
15; preserve the review unchanged and do not amplify those claims. It also notes
an undisclosed parser bound and a misleading equivalence explanation. Prepare a
small GLM prose-only correction with the existing contract-repair stage: keep
code/checks/probes fixed, disclose implemented restrictions, align explanations,
then rerun all controls and review. This does not require scientific redesign or
manual generated-artifact edits. The accepted reference/oracle evidence is
instance-specific; it does not prove the generated oracle correct on arbitrary
future inputs.

Allow the existing probe-resume loader to read a complete verified campaign
archive as well as the earlier partial snapshot layout. It binds original bytes,
cleanup and the identical grader candidate; probe acceptance is never reused.
Original program context remains bound through grading 002, while the accepted
probe suite and final controls come from 003. Fifty-four focused offline tests
pass, and the exact real handoff passes hash/context/code/check identity checks.
The new generic prompt guidance requires record-based counts, disclosure of
acceptance-affecting bounds and preservation of original evidence when a corrected
version is validated. Follow-up configuration is `grading-config-004.json`; it
has not launched yet.

### 2026-10-20 — Corrected contract accepted; prepare native execution

The prose-only pass 004 completed in 709.08 seconds with three responses (one
contract, two review). Code/check/probe identity comparisons confirm no executable
change. GLM disclosed the existing 64 MiB parser bounds, clarified exact-decimal
and grouped/full-row comparisons, and separated executed controls from earlier
narrative claims. All 15 controls passed afresh after the independent program
reran without answer access. The final review correctly inventories 15 and
accepts packaging; no further wording or scientific repair is pending.

Original archive/download verification passed, as did cleanup, independent
zero-sandbox lookup and terminal SUCCEEDED host/task readback. Preserve the exact
worker inputs/prompts/outputs with their hashes; the small public payload has a
recorded eligibility/credential audit. Native configuration now selects grading
004 and unchanged materialization 005. Native oracle/no-op controls, one blind
GLM attempt, publication and independent release download remain required.

### 2026-10-20 — Native controls and blind solver passed; stage release

Native 001 completed from `de7c881b585380b2a415e4fc1ea9b24e4877a540`:
oracle 1, no-op 0, blind GLM-5.3 Terminus-2 solver 1, without exceptions.
The gate records seven successful solver requests. Full archive download/readback,
three exact ownership-label provider absence checks and terminal SUCCEEDED host/
task readback are verified. The pre-trial task archive was retrieved through the
supported Iris CLI plus normal signed object reads, with URLs kept in memory;
local bounded extraction and upstream bundle inspection match
`sha256:44e68b961e2d5dee6b0ea445f34f5803eabb6198c6aa09d0d6a3420673ad0fa6`.

The locally staged release passes the full acceptance gate, including trial
result hashes, final control/candidate binding, exact public instructions,
source-attribution equality and all three original input hashes. It targets the
approved public personal namespace as `biotasks-notebook-pilot-issue-19-bioframe`.
Credential/private-endpoint pattern checks on the staged text artifacts are clear.
No upload has happened yet.

Force the publisher's supported upload thread count to one for the shared node.
The two existing parent-chain tests were not invoking guarded `main`; correct
the runpy entrypoint and patch the real lazy Hub module rather than replacing it
with an incomplete stand-in. Five focused offline ownership/parent-chain tests
now pass, exercising actual guarded entry, race rejection and one-worker upload.
This changes publication/test infrastructure only; the staged executable bundle
and native source identity are unchanged.

### 2026-10-20 — Reconcile publication interface failure before retry

The first publication attempt created the approved public repository, then failed
before any file upload because this installed Hub SDK's `upload_folder` does not
accept `num_threads`. The earlier signature lookup had matched another API.
Preserve its `upload_dispatched` receipt unchanged. Direct readback confirms the
repository contains only its initial `.gitattributes`, with no release files.
No native/task artifact changed and no dataset was replaced.

Remove the unsupported argument. Keep one upload command; this SDK method exposes
no thread-count parameter. Bind offline wrapper calls against the real installed
method signature so such an invalid argument is caught before network writes.
Permit an owned public repository containing only initial `.gitattributes`, while
continuing to reject unrelated data without a managed manifest and retaining
parent-commit guards. Six focused offline checks pass. The next upload uses a new
receipt, preserving the failed attempt and the explicit zero-upload readback.

### 2026-10-20 — Bioframe release published and independently downloaded

Publication completed at immutable Hub commit
`1dd40a82a3bfc8741162ff37c4726ea84dd58405` in
`gonzalobenegas/biotasks-notebook-pilot-issue-19-bioframe`.
A forced fresh download verified every file/mode and native-tested bundle hash
`sha256:44e68b961e2d5dee6b0ea445f34f5803eabb6198c6aa09d0d6a3420673ad0fa6`.
Keep the first failed upload receipt and explicit empty-repository readback;
the successful retry uses its own receipt. No prior result was overwritten.

Preserve 26 original native records against their archive hashes, including all
three trial/result/cleanup receipts, the solver trajectory and verifier reports.
The blind trial took 210.205947 seconds overall and passed all five checks in
seven successful model requests. Separate eligibility scans cover the exact
small public evidence; no credentials/private service endpoint values are found.
All three native ownership labels are absent and host/task SUCCEEDED.

The explorer's canonical selection now points at Bioframe. Its nine reading
stages fold construction/validation subworkers into their actual pipeline steps,
with separate recorded prompts, inputs and outputs. Presentation copies of the
question/config/oracle come from the freshly downloaded immutable release;
the actual first solver message is an exact field extraction from its original
trajectory, with provenance and hashes recorded. The HTML is an evidence reading
view, not a campaign log. Rendering/browser checks remain to be performed before
publishing the updated index. Issue 19 stays open for user review.

The final Bioframe HTML renders 72 source files into a 3.51 MB standalone page,
with nine pipeline stages and the actual eight-step solver trajectory. All five
views and nine stage routes passed the existing browser checks; 390px layout
has no horizontal overflow and no JavaScript errors. One browser was used with
a single renderer; measured maximum child RSS was 106,640 KiB. Notebook,
validation-pipeline and attempt screenshots were inspected: code uses legible
light text on the matching dark syntax background, and Prompt/Input/Output
sections are distinct with raw artifacts collapsed by default. No campaign-log
banner or historical run selector was added. The source manifest pins the exact
public release and all embedded inputs.

### 2026-10-20 — Focused promotion draft, separate from research history

Opened draft PR [#23](https://github.com/Open-Athena/biotasks/pull/23) from
current main `2a1950d239f1ada467c35393991dac87debe35f7` on a fresh
`codex/pipeline/notebook-factory-primitives-19` branch. Four reusable helpers,
ten active prompts and their documentation/tests are extracted; no research
branch merge, experiment drivers, evidence or provider provisioning is included.
The complete workflow remains research-only and still required operator recovery.
This promotion does not establish unattended end-to-end generation.

All 58 locked-environment local tests, lint/format/type and pre-commit checks
passed. GitHub CI independently passed Code quality and Tests for promotion
commit `4940e992dd9255095b917336d3933662a6721ab3`. Deterministic conversion
of the two original pinned notebooks produced byte-identical scripts to their
executed baselines with preserved ordered code; no analysis/model/cloud run
was launched for promotion. Small receipts are in `promotion/001/`. Issue 19
remains open for user review.

### 2026-10-20 — Review fixes and autonomous-pipeline merge requirement

User explicitly requires an autonomous pipeline before merging into main. Keep
PR 23 draft; the two operator-assisted published examples do not meet this gate.
A fresh seed must complete or be rejected explicitly without operator intervention
between stages. No autonomous-run success is claimed by the helper extraction.

Independent review found two reusable API bugs: forwarding could outlive the
gateway deadline/shutdown, and shortened tool output could hide a successful
artifact commit. The fixes interrupt tracked sockets during reads, TCP/TLS
establishment and response forwarding, join handlers on shutdown, and inspect
commitment before shortening the tool response. DNS resolves synchronously during
construction before accepting work, with that resolver limitation documented.
35 focused worker/gateway tests pass, including continuous-stream and stalled-TLS
deadline/shutdown reproductions and both artifact submission methods with tiny
previews. Lint, formatting and types pass. Tests use only local fake services;
no biological data, model calls or cloud workers were launched. The shared fixes
are applied to both promotion and research branches.

### 2026-10-20 — Single-invocation autonomous runner, before live validation

Added a sequential orchestrator over the existing workers, with programmatic
conversion, evidence sealing, output restoration, stage dispatch and terminal
classification. It makes no task-specific scientific edits. Explicit worker or
validation rejection is distinct from controller/provider failure; a failure or
budget timeout cannot count as successful autonomy. Five offline tests exercise
stage order, early rejection, infrastructure errors and tampered output handoffs.
The new seed is Bioframe's pinned peaks-to-genes notebook, without manually
chosen task endpoints. Its syntax-preserving conversion is supported.

Plan one fresh run on the existing reserved Iris host profile: two-hour deadline,
one 4-CPU/8-GiB/10-GiB Daytona sandbox at a time, five $1 stage reservations,
GLM-5.3 medium, existing reference/solver/verifier bounds and worker repairs.
No added model token/input/response caps. This uses existing spending authority.
No public release or merge is part of this autonomy test. A controller fix requires
a fresh run from the original seed; resuming a stage cannot prove autonomy.

## 2026-10-20 — autonomous replay gate refinement

The first fresh-seed campaign ran preparation, setup and two replays without
manual handoffs, but stopped on byte differences. A read-only streaming audit
found identical row multisets in all five outputs. Preserved the original
rejection in `autonomous-runs/001`; this was a false rejection by an overly strict
gate, not established notebook instability. Added general CSV/TSV observations,
with duplicate multiplicity and column order retained, and pass replay evidence
to the specification worker to assess scientific ordering. Preserve the original
reference bytes for construction. No generated task artifact was manually fixed.
The next campaign restarts from the original seed with the new frozen factory.

The second attempt completed reference execution and cleanup but chose compressed
TSVs, which the observation helper did not understand. Preserved that rejection
in `autonomous-runs/002`. Corrected the more general design error: replay byte
comparisons are observations, not a scientific admission gate. Pass successful
replays, including unknown differences, to specification and executable grading;
only those stages can assess semantic acceptability. Added streaming compressed
table profiles and regression tests. Eighteen focused offline tests passed. No
scientific artifact was manually amended; the next campaign starts from the seed.

While campaign 003 runs frozen at `897e24c0`, added a generic payload-building CLI
and explicit `seed_file` selection to the shared launch helper. This removes the
private launcher's seed override from future submissions. Four offline tests
check seed selection, byte identity and path containment. The running campaign
is unchanged; these launch-interface changes are not part of its factory pin.

## 2026-10-20 — preserve scientific uncertainty across automatic handoffs

Campaign 003 reached construction without intervention, but construction spent
more than an hour investigating the proposal. Read-only observation found that
its public draft assumed positive-length intervals and prescribed an incidental
selection convention, while the specification's private review had already
flagged uncertainty. The materialization context was dropping that review and
replay observations. The running frozen campaign was not changed.

For the next version, preserve the scientific review and replay observations in
the construction input, while continuing to omit downstream grader work plans.
Prompts now distinguish a proposal from an approved contract, require measured
support for asserted input properties, and permit transparent clarification of
unsupported incidental conventions without changing the scientific target.
Fourteen materialization/controller tests pass. Live impact is not established
by these offline tests; the next full run must test it.

Added controller regressions for explicit construction rejection, scientific
validation rejection, and native infrastructure failure: eight offline control-flow
and handoff tests pass. These fake-worker tests do not establish live autonomy.
Small final candidate/cleanup diagnostics are now retained alongside the final
receipt, so terminal decisions can be inspected without unpacking large data.

## 2026-10-20 — candidate-first construction

Read-only observation of campaign 004 showed that preserving the private review
alone did not prevent construction from attempting a full independent
implementation before submission. That duplicates the later validation stage.
Prepared a general tool-ordering change: construction must submit a complete
reference-based candidate before exploratory shell access; a failed controlled
execution unlocks shell-assisted repair. An unsupported candidate can instead be
explicitly blocked. This changes no scientific method or seed-specific behavior,
adds no model request cap, and does not modify the running frozen campaign.
Fifteen focused materialization tests pass. Live effectiveness is unproven.

## 2026-10-20 — require reproducible input staging

Campaign 005 passed its setup test but fresh replay failed because the generated
staging recipe expected an input already present in the exploratory cache.
The controlled setup test recreated the Python environment but retained input
files, so it did not establish that staging was self-contained. This is a general
controller defect, not a scientific rejection or a reason to edit generated files.
Controlled setup now empties both allowed input/cache roots before executing the
recipe. The worker must recreate them from recorded sources and can repair a
failure using its existing test allowance. Fifteen setup tests pass, including a
real shell reset on synthetic files that preserves candidate files and symlink
targets outside the cache. Candidate-first construction was not reached in 005.

## 2026-10-20 — first complete unattended rejection

Campaign 006 correctly rejected a generated export/inventory filename mismatch
without operator edits. The analysis itself ran; this is a malformed generated
candidate, not a broken scientific notebook. The host completed and resources
were cleaned up. Preserved the original worker explanation alongside controller
records; its extra claim about preparation hash placeholders is unsupported and
is explicitly separated from the confirmed filename mismatch. Added only a
general filename/inventory consistency reminder and automatic retention of
controller test diagnostics. Candidate-first construction and the positive
validation path still need live exercise, so the next run starts from the seed.

## 2026-10-20 — autonomous construction and recoverable admission feedback

Campaign 007 completed construction after GLM repaired its own first candidate,
then executed an independent solution without answer access. Grading remained
incomplete: a requested shell timeout no longer fit the remaining campaign
allowance, and the pre-dispatch refusal aborted the stage. This is infrastructure
failure, not scientific rejection. The host terminated and all owned sandboxes
were deleted; original receipts are in `autonomous-runs/007`.

The controller now distinguishes safe time-budget refusal before dispatch from
uncertain remote execution. A shell worker gets actionable remaining-time feedback
when a shorter operation could still fit; the deadline and computation ceilings
do not change. Exhausted budgets and lost provider responses remain terminal.
Fifty-eight focused grading/setup tests pass. No generated scientific content was
manually changed. The next comparison uses the original approved motifs notebook,
without any previous generated artifacts, to test the same controller on a
different analysis. This is a known seed, not a new held-out notebook.

## 2026-10-20 — command evidence must survive workspace cleanup

Campaign 008 failed during setup when a generated cleanup command removed the
controller's active named log. Archived operation evidence confirms the exact
command; this is infrastructure failure, not a scientific rejection. Host
termination and absence of owned Daytona sandboxes were verified. Command output
now spools to an anonymous file descriptor and is atomically saved after the
command ends, so worker cleanup cannot unlink its live output. Seventeen focused
logging/setup tests pass, including directory deletion followed by nonzero exit
and timeout. No notebook-specific instructions or generated task edits were added.

## 2026-10-20 — submit graders before duplicating controller checks

Campaign 009 completed autonomous construction with a GLM repair and independently
executed a solution, but grader authoring exhausted the work allowance while
running preliminary shell checks. Pre-dispatch time feedback worked, permitting
a shorter command without extending the deadline. Stage archival subsequently
timed out; both the primary budget failure and secondary archive failure are
preserved in `autonomous-runs/009`. Final root evidence was recovered and all owned
resources were removed.

Initial grader authoring now submits a candidate before shell exploration.
The existing controller checks run first and their failures guide repair.
This changes tool ordering, not scientific requirements, request counts or
deadlines; independent probes and review remain required. Forty-four grading
tests pass. Also retain the last three operation receipts per stage in the small
diagnostic export, avoiding a separate recovery job for ordinary command failures.
Live effectiveness of the grader ordering change remains unproven.

## 2026-10-21 — autonomous grading accepted; deadline still prevents completion

Campaign 010 built its first candidate successfully and GLM repaired a grader
formatting defect exposed by the frozen independent probes. All 17 final controls
passed and review accepted packaging. Grading took 4,696 seconds; its subsequent
archive export timed out. No native trial launched. Original small receipts and
verified cleanup are in `autonomous-runs/010`; this remains an infrastructure
failure, not full validation. Initial candidate-first grader authoring was exercised
successfully (two responses), but repair still spent 32 responses before submission.

Apply candidate-first tool ordering separately to each authoring/repair session;
44 grading tests pass. Native admission now uses the remaining campaign allowance
instead of requiring a full worst-case 1,500 seconds, still reserving 120 seconds
for cleanup and preserving phase ceilings. Eighteen execution/native tests pass;
outer trial timeouts remain infrastructure failures. These changes are general
controller behavior, not notebook-specific scientific edits. Campaign 011 will
start again from the original notebook, without reusing generated artifacts.

## 2026-10-21 — provider creation and cleanup conflict

Campaign 011 ended after preparation because Daytona creation exceeded 420 seconds.
The host terminated, but automatic deletion reported a conflict for its sole
sandbox. Ownership-checked reconciliation shortened the TTL to one minute;
readback still showed CREATING after that deadline. Force-stop and delete both
returned conflicts. Preserve the original failed cleanup and subsequent actions in
`autonomous-runs/011`. Do not launch another campaign until removal is verified.
This provider failure exercised neither the new grader-repair ordering nor the
native admission change; the autonomous positive path remains incomplete.

At 01:32:15 UTC a fresh full ownership inventory confirmed that the provider had
removed the failed sandbox. Preserve that final observation separately from the
conflicting cleanup receipts. Campaign 012 will retry the original seed with the
same factory behavior as 011, since provisioning never reached the new changes.

## 2026-10-21 — recover explicit context exhaustion without resetting execution

Campaign 012 passed construction after GLM repaired a missing-column error, but
its independent worker exhausted provider context after 74 received responses.
The original notebook was not rejected; validation remained incomplete. Preserve
stage receipts, the explicitly labeled failure observation, and verified cleanup
in `autonomous-runs/012`.

Upstream Tasksmith disables compaction in its Pi and OpenCode runtimes. The local
adapter now offers opt-in recovery after explicit HTTP 400 context-length rejection,
enabled for tool-supported artifact stages: retain original instructions and the
latest complete candidate/revision chain, explicitly discard exploratory dialogue,
and continue against unchanged workspace/controller state. Full traces, deadline
and request accounting remain intact. No recovery occurs for uncertain transport,
server errors or an oversized original context. Preserve small sanitized provider
failure receipts in subsequent diagnostic exports as well.

Eighty-nine focused tests and lint/type checks pass. The design-stage output-limit
assertion already failed against the unchanged adapter; it now checks the existing
specific exception without relaxing the no-replay contract. Campaign 013 starts
from the original notebook and does not reuse prior generated artifacts.

## 2026-10-21 — distinguish probe mutation from scientific acceptance

Campaign 013 passed all 23 scientific controls and review, without manual task
edits, but grading-stage export exhausted its remaining allowance. Native trials
were never reached. Preserve the recovered receipts and verified cleanup in
`autonomous-runs/013`; do not count this as end-to-end validation.

The probe worker spent substantial time inspecting and transcribing records.
Its first suite also hit a generic preflight bug: renaming an output was rejected
before grading because the original path was required to remain present.
Preflight now accepts successful actual mutations, including deletion/rename,
while the unchanged grader determines scientific acceptability. New synthetic
tests cover deletion/rename, no-op and crashing scripts in preflight and grading
modes; all 52 grading tests pass. The prompt encourages batched inspection and
deterministic selectors, and avoids duplicate preflight work without reducing
coverage. These changes contain no seed-specific methods or values.

## 2026-10-21 — first unattended native validation

Campaign 014 completed every stage from the original notebook with zero operator
interventions. All 13 scientific controls passed, review accepted packaging,
Harbor oracle/no-op rewards were 1/0, and the blind GLM solver scored 1. Pipeline
elapsed time was 60 minutes 35 seconds; solver execution was 3 minutes 37 seconds.
The host terminated successfully and a fresh complete ownership inventory found
no stage or native trial sandboxes. Preserve receipts in `autonomous-runs/014`.

This proves one autonomous successful execution on a known development seed,
without manual generated-task edits or prior generated artifacts. It does not
establish held-out generality. A new Hub release and promotion of the complete
runner remain outstanding; PR #23 stays draft and unmerged.

## 2026-10-21 — freeze two additional examples before execution

The user selected the original MDAnalysis RMSD and COBRApy FBA notebooks.
Pin both sources and retain their root licenses under `autonomous-cases`.
Simulation-trajectory and curated-model lineage are explicit; data terms remain
separate from the source-code licenses. No scientific endpoint or method is
manually selected in their seed metadata. `additional-notebooks.md` records the
same-revision, sequential first-attempt protocol.

Both sources exposed general conversion limitations. Profile v3 normalizes only
standalone `%matplotlib inline` and first-line argument-free `%%time`, recording
each cell/line change. Token positions protect strings and comments; timing bodies
execute once, and ordered Python syntax is checked after normalization. Known
editor presentation metadata is recorded and ignored. Unknown magics and execution
directives remain explicit unsupported cases. Both real notebooks now convert;
25 conversion/intake tests and eight orchestration tests pass, plus lint and
converter type checks. Scientific notebook code was not executed locally.

The aggregate spending ledger was stale relative to the transfer and autonomous
runs. Reconcile retained holds against the recorded resource/lifetime bounds and
cleanup evidence, adding those runs explicitly and reserving $5 for each new
example. `budget-reconciliation-20261021.json` distinguishes conservative holds
from invoices. Total retained holds, including both new attempts, remain $100;
no free-credit assumption or new aggregate authorization is used.

## 2026-10-21 — additional first outcomes; reject source-code repairs

The two same-revision first attempts are preserved in `autonomous-runs/015` and
`016`. MDAnalysis passed reference execution and replays but specification failed
on response 26: finish_reason tool_calls with null tool_calls and empty content.
The adapter executed no action from it. Recover the original response with a
verified hash using the already-active COBRApy host's read-only storage client;
no extra model or sandbox work was launched for recovery.

COBRApy passed reference execution after its GLM setup worker added a missing
import. Its claim that Jupyter implicitly supplies the package binding is
incorrect; hidden prior kernel state is only a possible explanation. After
discussion, the user decided to reject sources needing code repairs such as this.
The run had independently returned a blocked diagnostic construction candidate
before a stop was necessary. Do not conflate that original worker decline with
automatic enforcement of the new source-code policy.

Clarify the general setup prompt: install dependencies and stage inputs, but reject
missing imports, undefined names and other source-code defects. A controller
import-signature check now rejects added/removed/changed analysis imports before
controlled execution. Twenty setup tests and lint pass. Original scientific
calls and generated artifacts were not manually fixed. Both jobs are terminal;
fresh provider ownership inventories show no remaining sandboxes. No new accepted
task, publication, policy rerun or held-out success is claimed.

## 2026-10-21 — retry an empty received response without replaying actions

The user requested general empty-response recovery and a fresh MDAnalysis run,
preserving the original failure. The adapter now permits one retry per stage
instance, including any upstream resubmissions, after an otherwise complete
response contains no text/action/refusal. Save the original response, retain its
request slot, append the canonical recovery notice, and continue from all completed
actions and feedback. Do not replay uncertain transport, partial actions or
refusals, and do not reset time/turn/request limits. One-call stages remain bounded
to their original single call. The recovery notice hash is captured in stage
identity. Eighty-two focused tests pass, covering both successful recovery and
bounded failure paths.

Prepare fresh attempt 017 from the original MDAnalysis notebook, with the strict
source-import policy retained. Preserve all of attempt 015 unchanged. Its new
configuration and `rmsd-empty-response-rerun.md` distinguish the rerun. Reconcile
the two completed example holds to $1 each using verified teardown, reserve $5
for 017, and retain $97 aggregate holds under the $100 authorization. No scientific
source, generated artifact or solver result is manually patched.

## 2026-10-21: remaining issue-18 panel intake

User requested running all remaining issue-18 seeds. Fetched the seven original
sources not covered by Scanpy, active MDAnalysis rerun 017 or COBRApy outcome 016;
every source matched its original panel hash. The old manually selected compact
task directions are not worker inputs. See remaining-panel.md and its manifest.
R Markdown (four seeds), Bash (bedtools) and embedded IPython shell commands
(scikit-bio) expose unsupported conversion/execution paths. Asked whether to add
generic R support; no answer yet. Do not count these gaps as scientific rejection.

Added conversion profile python-narrative-v4 for documented boolean cell editing
and deletion permissions. These affect notebook editing, not execution; retain
values in the receipt and retain ordered AST equivalence. PyRadiomics now
converts without changing source code. Prepared original source/license/identity
and campaign 018, not submitted. Twenty-seven converter tests and Ruff passed.
No new sandbox or model call was launched for this panel.

At 15:11 UTC, active 017 had finished setup and fresh reference replays and reached
specification. Setup trace records one empty-response retry at call 60, unchanged
allowances and no action executed from the empty response. The completed stage
establishes live recovery; original failure 015 remains unmodified.

## 2026-10-21: run supported Python seeds first

User chose to defer R support and run supported Python seeds first. The four
R Markdown cases remain explicitly deferred, not scientifically rejected.
PyRadiomics remains next after active MDAnalysis 017 and verified cleanup.
At 15:33 UTC, 017 had completed specification and construction and was grading;
the independent implementation finished and the grader worker had started.
No new paid campaign has been submitted.

## 2026-10-21: parallel notebook campaigns authorized

User explicitly authorized launching notebooks in parallel. Up to two reserved
Iris hosts and one 4 CPU/8 GiB/10 GiB CPU-only Daytona sandbox per campaign;
per-campaign 7200-second work and 300-second cleanup ceilings remain unchanged.
Reconciled the completed original 019/020 shared-deadline reservation from $5
to $2 using original cleanup/result/configuration evidence, and reserved $5 for
PyRadiomics 018. Aggregate held $99 of $100, not a measured invoice or credit
assumption. See budget-reconciliation-radiomics018.json. No new paid Iris capacity.

At 15:42 UTC, MDAnalysis 017 finished with an explicit grading rejection:
independent_comparison_unresolved. The first grader rejected the independently
produced solution; no native solver ran. Root archive/host termination and fresh
cleanup observations are still being collected. This does not establish that
the original notebook is broken. Empty-response recovery succeeded earlier.

PyRadiomics campaign autonomous-radiomics-018 submitted at 15:44 UTC from frozen
factory bd0c81c640c1be3d7b30a958ab84264807d9d18a. Payload identity and aggregate
reservation checked before submission. No original source or generated scientific
artifact was manually repaired. Local submit peak RSS 441,656 KiB, exit 0.

MDAnalysis 017 receipts recovered after host SUCCEEDED at 15:45 UTC; root pipeline
rejected with zero interventions. Provider inventory found all four stage owners
absent. Independent RMSD columns matched to the proposed tolerance, while the
public time formula yielded a 0.5 ps origin and the reference yielded 1.0 ps.
The guard rejected the contradiction before repair or a solver attempt.
Preserved original 015, raw empty/next responses, retry event, conflict and
control records, and cleanup evidence in autonomous-runs/017. Reconciled its
$5 hold to the prior $1 resource bound; aggregate holds now $95, $5 unallocated,
not provider invoice figures. No notebook-specific timing offset was introduced.

## 2026-10-21: PyRadiomics first outcome collected

Collected original 018 receipts after host FAILED. Preparation completed; setup
stopped on the controller snapshot-inputs helper after the setup command had
completed. Underlying helper log remains undiagnosed; do not infer a notebook
defect or scientific execution. Setup cleanup and fresh ownership inventory
confirm no remaining sandboxes. Preserved first outcome in autonomous-runs/018.
No new campaign or repair was launched. User is discussing whether to improve
the MDAnalysis comparison-conflict recovery path; no change adopted yet.
