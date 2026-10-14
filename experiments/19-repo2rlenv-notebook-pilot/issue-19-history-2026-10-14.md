## Current follow-up: design-stage preparation — 2026-10-13

The newer-notebook design work is paused for review of the [canonical prompt](https://github.com/Open-Athena/biotasks/blob/3d92a14e0758e3854a14bf0e4549b424400ed527/src/biotasks/prompts/notebook-task-design.md) and [prepared integration](https://github.com/Open-Athena/biotasks/blob/3d92a14e0758e3854a14bf0e4549b424400ed527/experiments/19-repo2rlenv-notebook-pilot/design-intake-reuse.md). Tasksmith's artifact controller now has a tested GLM adapter and a factual file profiler; live tool-calling compatibility and real-data profiling remain untested. No construction, solver or viewer update ran in this preparation. The completed release below is unchanged.

## Completed after GLM repairs — 2026-10-13

The repaired task is [published publicly at immutable revision `353e8a2`](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19/tree/353e8a296c4101d3c0647e4c50e2b0ed7214d5de). GLM added integrality-before-conversion checks for detected-gene metadata and replaced unrestricted mitochondrial truthiness coercion with Boolean-value validation. Numeric `0/1` flags remain accepted. No task-specific artifact was manually repaired.

**[Open the updated HTML explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/6a3ebc4ebe1cfd611158caf245b2d2a21c27a809/experiments/19-repo2rlenv-notebook-pilot/explorer/index.html)**. It uses issue #17’s Approaches and Notebook → Task → Attempt interface, replacing the generation approaches with this pipeline’s actual stages, exact prompts, outputs and repair evidence. Review records the current release and its limitations; historical attempts retain their bundle identities.

Recovery 022 passed fresh native controls: reference **1**, empty baseline **0**, omitted-gene-filter wrong answer **0**, alternative implementation **1**, blind GLM solver **1 in 70.24 seconds**. Scientific review passed with validated citations, and all five task sandbox cleanups were verified. The independent reviewer found no new blocking regression. That re-review assessed the two coercion repairs statically; dedicated mutation trials for those exact defects were not performed.

Upstream staging and release verification passed. A forced fresh download verified file hashes, executable modes and bundle identity `sha256:be244320301182840a1e8a9b453b363a9fd227ac6e1c7ece39aea17ce00761be`. Anonymous access confirmed the dataset is public. [Result and evidence receipts](https://github.com/Open-Athena/biotasks/tree/6a3ebc4ebe1cfd611158caf245b2d2a21c27a809/experiments/19-repo2rlenv-notebook-pilot/release-evidence) preserve publication, download and review evidence. The original release remains available at its immutable revision.

The repair run used 17 quality calls, seven solver calls, one GLM repair and five native trials. Conservative aggregate Daytona reservations remain **$76 of the authorized $100**, not actual invoiced spend. No further campaign is needed for this pilot. The experiment remains on its permanent research branch; no merge or promotion PR is implied. Issue #18 remains deferred.

Conclusion: SETA Seed2Synth plus Repo2RLEnv’s shared quality/release infrastructure can produce this notebook-grounded task with reusable notebook intake, scientific/schema/coercion review and execution adapters. This is evidence for one notebook, not a benchmark or proof of general fidelity. Scientific dependencies/base image remain unpinned, and no broad adversarial audit was performed.

The entries below preserve the earlier checkpoints and decisions; pending statements there are historical.

---

## Historical reopening after independent review — 2026-10-13

The published native controls and file-integrity checks remain verified, but an independent review found a grader false acceptance: integer coercion can admit fractional detected-gene metadata. Boolean coercion also weakens the promised annotation representation. This is a static finding; no new biological trial has yet exercised that mutation. The previous completion conclusion below is historical, not the current status. A GLM-authored repair and fresh validation are pending; no task-specific artifact will be manually patched.

[Open the notebook → pipeline/prompts → task → attempts HTML explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/codex/research/19-repo2rlenv-notebook-pilot/experiments/19-repo2rlenv-notebook-pilot/explorer/index.html). It includes exact captured prompts/responses, selected solver turns and controls, and the current review caveat. Current prompt templates are clearly separated from historical run inputs. This is a selected evidence view, not all campaign history.

Reusable fixes reject path escapes in label reconstruction and bound archive metadata expansion before extraction. Eight focused tests pass; desktop/mobile browser navigation checks pass. [Review fixes, explorer and bounded repair configuration](https://github.com/Open-Athena/biotasks/commit/0868488).

Campaign 019 is reserved for one GLM repair, five native trials, one five-minute solver attempt, at most 24 quality/review and 24 solver requests, two hours plus cleanup, and $5 Daytona. Aggregate conservative reservations are now $71 of $100, not actual billed charges. The original immutable release remains preserved.

---

## Historical completion checkpoint — 2026-10-13

Published [the one-task notebook pilot](https://huggingface.co/datasets/gonzalobenegas/biotasks-notebook-pilot-issue-19), generated and repaired by GLM-5.3 from the full observed Scanpy PBMC3k inputs. The final task passed reference success, empty-submission rejection, meaningful wrong-answer rejection and a valid alternative implementation. The blind GLM solver succeeded in **77.6 seconds**. Offline preflight and all owned sandbox cleanup checks passed.

The scoped experiment supports reusing SETA Seed2Synth and Repo2RLEnv’s quality/release infrastructure for notebook-grounded tasks, but this was not a zero-adaptation integration. Notebook intake and fidelity/schema review were needed alongside endpoint, execution, serialization, cleanup and evidence-portability fixes. Generic infrastructure failures and scientific contract defects were both observed; their original records remain in the research branch and decision log. No generated task was manually patched.

The upstream release workflow published immutable revision `5231e1ac828101c04707a905a47be7a553f23928`; a fresh forced download verified file hashes, executable modes and task identity. [Final results and receipts](https://github.com/Open-Athena/biotasks/tree/f786f61/experiments/19-repo2rlenv-notebook-pilot) include the publication and download checks. The release includes scientific review, provenance/licenses and the solver trajectory, and links the existing Harbor Visualiser.

Limitations: one notebook does not establish benchmark performance or broad scientific fidelity; model review is not independent biological execution; no broad adversarial security audit was performed; package/base-image versions remain unpinned. The release discloses historical recipe metadata versus the actual pinned execution dependency. Conservative total reservations are **$66 of the $100 authorization**, not a measured invoice. Stop further campaigns. Preserve this research branch; no merge or promotion to main is implied. #18 remains open and deferred.

---

Test whether Repo2RLEnv's SETA Seed2Synth pipeline can turn one biological notebook into a scientifically faithful, executable Harbor task with minimal upstream changes. Keep the integration in BioTasks, starting with a pinned Repo2RLEnv dependency. This is a separate, smaller experiment from #18; leave that issue open and deferred, preserving its code and experimental evidence.

## Approach

Start from the upstream SETA Seed2Synth workflow rather than recreating the existing BioTasks factory inside it. Adapt notebook intake and assess scientific fidelity. Use the selected Scanpy PBMC3k notebook, scoped to QC, filtering and normalization with its full observed input matrix; record source/data permissions and check that the analysis plausibly fits five minutes. Record the source revision and input lineage. The task must remain grounded in the notebook's real data and methodology; documented input reductions are allowed. A task merely inspired by the notebook is insufficient. Specify the biological objective, methodology, consequential parameters and required outputs without prescribing a programming language or software package. Software choice remains open within the prepared offline environment; the grader must accept scientifically valid alternative implementations.

Use GLM-5.3 through the existing inference endpoint for design, construction, review, verifier probes, repair and solving. Authoring uses upstream direct structured calls, with an endpoint adapter only if needed. ZCode is not required. Disable automatic escalation to other models. Use upstream Terminus-2 for solving, subject to the endpoint and execution integration checks recorded below; Pi is not required.

Reuse upstream package construction, quality review/repair, Harbor execution, reports, trajectory viewers and release tooling wherever compatible. Record necessary deviations and their rationale. Prefer the pinned dependency; discuss any required fork or substantive change in scope before adopting it. Do not build a custom viewer unless inspection establishes a concrete gap.

## Validation and execution

Keep upstream binary grading for this pilot; defer weighted partial credit. Scientific output tests determine rewards, not LLM judgment. Use the shared quality loop to check task clarity, verifier behavior and leakage, including reference success, no-op failure, rejection of a meaningful wrong solution, acceptance of a valid alternative and review of a blind solver attempt. Explicitly assess fidelity to the notebook's methodology and observed data. A generic upstream quality label alone does not establish biological fidelity.

Use offline solver and verifier execution. Internet access is allowed during authoring and environment setup to stage data and dependencies. Distinguish inference-service access from network access available to the solver's tools, and verify the chosen implementation enforces that separation.

Each finite campaign permits:

- One initial build and at most two generation repairs.
- At most one quality-loop repair.
- At most two blind solver attempts total, allowing a fresh attempt after repair.
- Five minutes per blind solver attempt, including model and tool time; this is not the environment-build or generation timeout.
- Routine factory fixes, recovery and sequential retries are authorized within the updated $100 aggregate budget below, stopping early on success. Each run must have explicit repair, attempt, request and time limits; recoveries carry forward prior usage and the original deadline.

The agreed host, task, time and request ceilings are recorded in the decision log below. The current aggregate authorization is $100 before credits, superseding the earlier ten-replacement/$50 allowance. Current campaign reservations remain $5 each, shared by their recoveries. The previous 4-CPU/8-GiB/10-GiB profile is not automatically inherited. Configure and verify the above repair/attempt bounds across generation and quality stages rather than assuming upstream defaults match them.

Factory improvements only: reusable code, adapters and version-controlled prompts may be edited. GLM workers must produce task-specific instructions, solutions, graders, scientific probes and repairs through the pipeline. No manual task patches or bespoke operator repair instructions to make the candidate pass. Preserve failed outputs, exact prompts/configurations, revisions, runtime and available usage records. Keep infrastructure failures distinct from scientific defects and valid solver failures.

## Release and completion

Use `release stage` → `release verify` → `release publish` for the selected recipe bundle. Publish publicly under the personal Hugging Face namespace `gonzalobenegas`, using `gonzalobenegas/biotasks-notebook-pilot-issue-19`. Verify redistribution eligibility before uploading. Publish the task with source/input provenance, limitations and validation evidence. Download the published release and verify its integrity, including executable modes where they enter the bundle identity. Release integrity does not substitute for execution or scientific validation.

Completion requires a scientifically validated task, at least one valid blind solver attempt, inspectable upstream reports/trajectories, and a published release whose downloaded contents pass integrity checks. Solver success is informative but is not required. Missing validation, infrastructure failure or exhausted generation/repair budget must be reported as an unmet outcome, not converted into success or permission for unlimited retries.

## Remaining decisions and checks

- Verify GLM compatibility with upstream structured authoring and Terminus-2; the harness choice and preparation of endpoint support are agreed below.
- Implement and validate the agreed Iris/Daytona execution integration, including offline solving/grading and credential isolation.
- Implement and verify the agreed resource/time/request bounds below, including accounting for provider-side image builds and cleanup, before execution.
- Discuss any further substantive upstream changes or deviations; no fork is currently planned.

## Relationship to prior work

The previous factory encountered generic packaging, schema, handoff and recovery failures before reaching scientific validation. This experiment tests reuse of upstream infrastructure so custom work can focus on notebook intake and scientific fidelity. Prior supervised task fixes do not establish autonomous generation. Preserve #18's historical records, collect the already-submitted fifth panel's outcomes and reconcile any resources; launch no further #18 batches while it is deferred.

References: [SETA Seed2Synth](https://huggingface.github.io/Repo2RLEnv/pipelines/terminal_synth/), [quality loop](https://huggingface.github.io/Repo2RLEnv/pipelines/quality_loop/), [release workflow](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/docs/guides/publishing.mdx).

## Decision log

Keep this dated log current as choices change. An agreed design is not evidence that its implementation or execution has passed.

### 2026-10-09 — pilot scope agreed when filing

- Create this one-notebook upstream pilot separately from #18; leave #18 open and deferred. Begin with pinned Repo2RLEnv SETA Seed2Synth and reuse its quality loop, Harbor reports/viewers and release workflow.
- Use GLM-5.3 throughout, direct structured calls for authoring, binary grading and scientifically valid software alternatives. No automatic model escalation. GLM must author and repair task-specific artifacts; operator changes are limited to reusable infrastructure and prompts.
- Retain the notebook's observed data and methodology. Allow documented reductions, but require scientific validation; solver success is informative rather than mandatory.
- Permit one initial build, two generation repairs, one quality repair and at most two blind solver attempts, each limited to five minutes. Keep task execution and grading offline. No automatic fresh campaign after budget exhaustion.
- Require a public release at `gonzalobenegas/biotasks-notebook-pilot-issue-19`, including redistribution eligibility, validation evidence and a download/integrity check.

### 2026-10-09 — notebook selected

- **Agreed:** use the [Scanpy PBMC3k notebook](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering-2017.ipynb), scoped to QC, filtering and normalization, retaining the full observed count matrix. Software choice stays open; this is not a requirement to solve using Scanpy.
- **Reason:** compact scientific scope and explicit [CC BY 4.0 dataset permission from 10x Genomics](https://www.10xgenomics.com/datasets/3-k-pbm-cs-from-a-healthy-donor-1-standard-1-1-0). The bedtools candidate has an unresolved coordinate/assembly consistency concern and is not selected for this pilot.
- **Status:** notebook source inspected and intake conversion checked; no biological execution or generated-task validation yet.

### 2026-10-09 — harness and integration changes

- **Agreed:** retain upstream Terminus-2 for solving and prepare custom-endpoint support. The pinned Repo2RLEnv trial runner explicitly rejects custom endpoints, although its authoring client and Harbor's Terminus harness expose endpoint configuration.
- **Patch location:** small version-controlled patches on this BioTasks research branch, applied to the pinned Repo2RLEnv dependency with recorded hashes. No full fork is currently needed. The endpoint patch is prepared and has isolated helper tests; full integration remains unverified.
- **Agreed:** prepare an Iris/Daytona execution integration, keeping the model client on Iris and task tools offline in Daytona. Retain upstream generation, quality and release logic. This adapts Repo2RLEnv's currently fixed worker/Docker execution arrangement to the approved model-access environment; no change to shared inference services is authorized or planned.
- **Status:** preparation authorized; remote execution has not started. Resource/time/request ceilings and total compute budget still require agreement before running. Turn bounds must not be represented as raw-request bounds because the harness can retry calls.
- **Isolation:** work is on `codex/research/19-repo2rlenv-notebook-pilot`, started from main `2a1950d239f1ada467c35393991dac87debe35f7`. The #18 research branch is preserved.

### 2026-10-09 — first campaign budget agreed

- **Host:** one Iris job on existing reserved CPU capacity, 2 vCPUs, 4 GiB RAM and 20 GiB storage; no GPU, new paid capacity, inference deployment or automatic job restarts.
- **Tasks:** one active Daytona task sandbox at a time, 1 vCPU, 2 GiB RAM and 10 GiB disk. Two-hour campaign ceiling, followed by five minutes for export/cleanup only. Build timeout 600 seconds, reference 600 seconds, verifier 120 seconds; whole-trial timeout at most 1,500 seconds and bounded by the enclosing deadline.
- **Solver:** preserve the two-attempt maximum and five-minute model/tool limit; at most 12 harness turns and 24 outgoing inference requests per attempt, including retries.
- **Request ceiling:** 80 total = 4 small compatibility requests + 4 SETA design/build requests + 24 quality-loop requests + 24 for each of two solver attempts. These are ceilings, not target usage; request allowances do not add repair rounds. Uncertain/provider-error requests consume allowance.
- **Trial ceiling:** 16 scientific validation/solver trials: up to six generation controls and ten quality trials across two revisions. Permit one additional infrastructure-preflight sandbox for at most ten minutes. Stop rather than automatically start a new campaign if any allowance is exhausted.
- **Metered usage:** at most USD 1 for Daytona compute/storage, with conservative reservations and cleanup. Account credits may cover the usage; account credit/billing status has not been verified. Published usage rates are not a statement that the account will be charged.
- **Status:** bounds approved, launcher/request accounting and live preflight still pending. Local tests exercise actual upstream control-plane code with mocked model/cloud dispatch; no biological validation or offline-network enforcement has yet run. No pilot model requests, jobs, task sandboxes or release have occurred.

### 2026-10-09 — implementation checkpoint: scientific review

- **Implementation:** version-controlled notebook guidance now feeds upstream SETA design and construction; a separate GLM scientific-fidelity review uses the existing 24-request quality allowance. It records findings against source/task evidence with exact citation checks. This review does not supply rewards or establish independent execution.
- **Validation:** fourteen local mocked tests cover execution integration, preserved design-call behavior and review evidence checks. The three patches apply sequentially to the pinned source and reproduce the inspected checkout. Task resource overrides and the whole-trial time bound are included.
- **Status:** campaign assembly is committed and pushed, but launcher/preflight, provider-cost and cleanup accounting, actual generation/validation, and release remain incomplete. No pilot model requests or sandbox jobs have run.
- **Evidence:** [implementation checkpoint](https://github.com/Open-Athena/biotasks/commit/26eca23302aa8133e12507fa747879d0f6735a99), with detailed limitations in the branch-local logbook.

### 2026-10-09 — first approved campaign submitted

- **Execution:** submitted the single authorized Iris job from [cf222db](https://github.com/Open-Athena/biotasks/commit/cf222dba3eab6216209aad14427f7ac072fe6255), using the agreed host, task, time and request ceilings. Failure/preemption retries are disabled. The launch receipt and job identity are retained privately; an observation timeout does not authorize resubmission.
- **Integration:** the upstream supervisor now labels and cleans up its own Daytona sandboxes instead of attempting Docker cleanup. Unresolved cleanup blocks subsequent trials. The bootstrap verifies frozen inputs and patches, and exports evidence with download checks. Local mocked submission, cleanup and campaign-wiring checks passed; they do not establish live provider behavior.
- **Accounting:** conservative reservations total at most USD 1: USD 0.030 preflight + 16 × USD 0.057 trials + USD 0.058 image/storage allowance. These are internal usage allowances, not a provider billing cap or a verified account charge; actual usage and cleanup still require reconciliation.
- **Status:** submitted, not scientifically validated. The job will check model compatibility and infrastructure isolation before generation. Publication and download verification remain outstanding.

### 2026-10-09 — first job terminal; diagnosis pending

- **Observed:** Iris reports the job FAILED with one failure and zero preemptions. The outer traceback reached the campaign subprocess after dependency setup and reports exit status 1. This establishes neither a scientific failure nor successful generation. No replacement campaign has been submitted.
- **Evidence access:** detailed campaign evidence is at the private artifact destination, but a direct read from the operator VM returned HTTP 403. Request counts, precise failure stage and any sandbox cleanup remain unverified until those records are retrieved. A bounded read-only recovery job has been proposed for approval; it would not run models, generate tasks or create task sandboxes.
- **Outcome:** issue completion remains unmet; publication has not occurred.

### 2026-10-09 — prior #18 panel outcome summaries recovered

- **Observed:** all ten fifth-panel jobs are terminal. Final pipeline summaries show four incomplete validations, two incomplete reviews, two exhausted budgets and two other incomplete runs; none reports acceptance. Scheduler success is not scientific validation.
- **Evidence:** [source-bound summaries and log hashes](https://github.com/Open-Athena/biotasks/blob/5bf3801cc6910d091997e35033dc157200585b40/experiments/19-repo2rlenv-notebook-pilot/prior-issue18-panel5.json), also [reported on #18](https://github.com/Open-Athena/biotasks/issues/18#issuecomment-6090252880). Native artifact inspection and sandbox cleanup reconciliation remain outstanding.
- **Scope:** read existing logs only; no new #18 campaign or sandbox was launched. Approval for the separate read-only #19 diagnostic recovery job is still pending.

### 2026-10-09 — overnight continuation authorized (America/New_York)

- **Approved:** one read-only recovery job on reserved Iris capacity, limited to 1 CPU, 1 GiB RAM and five minutes, to retrieve the failed pilot evidence. It makes no model calls, generates no tasks and creates no Daytona sandbox. Submitted once; its existing handle is retained for observation.
- **Approved:** up to ten replacement campaigns after diagnosing and fixing reusable factory code. Run campaigns sequentially and stop earlier on success. Each retains GLM-5.3 only, one notebook, 80 model requests, the existing generation/quality repair bounds, at most two five-minute solver attempts, and a two-hour campaign plus cleanup. No manual task fixes or GPU work.
- **Approved Daytona ceiling:** USD 5 per replacement campaign and USD 50 across the ten replacements, before any credits. This replaces the USD 1 cap only for new campaigns; it does not increase CPU/RAM/disk or time/model limits. Additional aggregate ceilings are 800 model requests and 20 campaign hours plus cleanup.
- **Execution discipline:** preserve every failed run and exact inputs. Observation timeouts do not authorize duplicate submissions. Public release to the agreed personal Hugging Face dataset remains authorized, conditional on scientific validation and redistribution eligibility.

### 2026-10-09 — diagnosis recovered and replacement 1/10 running (America/New_York)

- **Original failure:** hash-verified recovery confirms exactly one compatibility request, HTTP 200, with successful response parsing. Saving nested LiteLLM usage metadata then raised a JSON-serialization TypeError. The job never reached Daytona preflight, task generation or scientific trials. See [campaign-001 evidence](https://github.com/Open-Athena/biotasks/blob/5ff327c359d0f2d52590540531badbca3a826d2f/experiments/19-repo2rlenv-notebook-pilot/campaign-001-result.json).
- **Factory fix:** patch 0004 serializes usage models in JSON mode, preserving nested token details. A regression using the installed LiteLLM Usage class passed. No task-specific artifact was edited.
- **Execution:** campaign 002, the first of ten authorized replacements, was submitted once from [5ff327c](https://github.com/Open-Athena/biotasks/commit/5ff327c359d0f2d52590540531badbca3a826d2f). A live observation reports RUNNING. Nine replacement slots remain; no validation or release is yet claimed. New jobs return bounded hash-verified diagnostics through their existing logs to avoid unnecessary recovery jobs.
- **Publication access:** existing Hugging Face authentication identifies the approved personal account with write access. No dataset has been published.


### 2026-10-09 EDT: first replacement result and diagnostic recovery

Campaign 002 finished without emitting a task: SETA rejected the design at schema validation. It used two model requests (one compatibility check and one design call). The real Daytona isolation preflight passed representative outbound TCP probes and verified sandbox deletion; no scientific validation or solver trial occurred. The detailed model/error receipts remain in the checked remote export, but the bounded diagnostic selector omitted them. The factory now includes candidate receipts and preserves artifact file modes for subsequent releases.

A read-only recovery job is charged against replacement slot 2 of the ten approved slots, using 1 CPU/1 GiB for at most five minutes and no model calls or Daytona sandbox. Eight replacement slots remain. Inspect the exact saved validation error before a further generation campaign. [Campaign evidence](https://github.com/Open-Athena/biotasks/blob/3711838/experiments/19-repo2rlenv-notebook-pilot/campaign-002-result.json).


### 2026-10-09 EDT: empty-response diagnosis and next replacement

Recovery completed with original hashes verified. The saved design response was empty: all 9,000 completion tokens were attributed to reasoning; the schema error was EOF while parsing JSON. This is a model-output exhaustion failure, not a notebook suitability rejection. The factory config now explicitly sets the service-supported lower reasoning effort, while retaining the existing output-token, request, turn and runtime ceilings. Three adapter regression cases passed, including unchanged default forwarding, settings propagation and refusal of conflicting settings. No generated scientific artifact was edited.

Campaign 004 was submitted once and observed RUNNING at 00:40:27 UTC on October 10, from [d485dba](https://github.com/Open-Athena/biotasks/commit/d485dba13fac34f53775d21d7e0ae7055c87b915). It is replacement slot 3, including the read-only recovery in slot 2; seven slots remain. The per-campaign Daytona ceiling remains $5 and aggregate replacement ceiling $50 before credits. No validated task or release is yet claimed.


### 2026-10-09 EDT: construction output failure and compatibility check

Campaign 004 ended without a task after the initial build and both generation repairs. The design succeeded with lower reasoning effort. The first two builder responses contained placeholder code; the last flattened Python and shell line breaks and contained invalid JSON. Five requests were used, no scientific trial ran, and preflight sandbox deletion was verified. [Evidence](https://github.com/Open-Athena/biotasks/blob/76b280fb053446763ff23a72b1d818c0a89a400a/experiments/19-repo2rlenv-notebook-pilot/campaign-004-result.json).

Test an endpoint compatibility hypothesis: use JSON-object mode, retain the original schema explicitly in the prompt, and keep upstream validation. Do not rewrite model outputs or manually repair generated files. A new small compatibility request checks exact preservation of newlines, tabs, quotes, backslashes and Unicode before any sandbox creation. It remains within the existing four-request compatibility allowance. Seven local adapter/pipeline checks passed, including rejection before sandbox creation when string characters are lost.

Campaign 005 was submitted once from [76b280f](https://github.com/Open-Athena/biotasks/commit/76b280fb053446763ff23a72b1d818c0a89a400a). It uses replacement slot 4; six slots remain. All runtime, repair, resource, model-request and monetary ceilings are unchanged. No scientific validation or release is claimed.


### 2026-10-09 EDT: structured-output check passed; verifier overhead corrected

Campaign 005 passed both compatibility checks, including exact string escaping, and materialized a GLM-authored task package. The controller then stopped before scientific execution because upstream adds 30 seconds of wrapper time to the inner test timeout: the factory supplied 120 seconds and therefore emitted a 150-second verifier. The approved 120-second guard correctly rejected it. Five requests were used; preflight sandbox cleanup was verified. [Recorded failure](https://github.com/Open-Athena/biotasks/blob/5eb1e505d4d189cf0e4ef246e2f303eb103fe2aa/experiments/19-repo2rlenv-notebook-pilot/campaign-005-result.json).

The reusable configuration now gives tests 90 seconds, yielding the approved 120-second total verifier timeout. A regression exercises the actual upstream emitter and checks its phase limits. Both wiring tests and focused lint/format checks passed. No task-specific instructions, solution, tests or repairs were manually edited. The source license notice and primary data attribution evidence have also been preserved for the eventual release.

Campaign 006 was submitted once from [5eb1e50](https://github.com/Open-Athena/biotasks/commit/5eb1e505d4d189cf0e4ef246e2f303eb103fe2aa), using replacement slot 5. Five slots remain. Scientific validation and public release are still unfulfilled; all approved ceilings remain unchanged.


### 2026-10-09 EDT: native controls reached; discriminating probe still missing

Campaign 006 generated a task and reached the upstream quality loop. Its final recorded controls are reference 1, no-op 0, valid NumPy alternative 1 and wrong-solution probe 1. The wrong probe changed comparison boundaries without changing the observed artifacts on this fixed dataset. Upstream therefore returned `needs_repair`; no blind solver ran. Its installed-control immutability rule remains intact, and the task/verifier was not changed to reject an equivalent output. The valid alternative's parsing fix was authored by GLM within the quality repair allowance. The separate fidelity review supplied abbreviated quotations and was rejected by exact citation checks. [Recorded result and limitations](https://github.com/Open-Athena/biotasks/blob/f07a53f/experiments/19-repo2rlenv-notebook-pilot/campaign-006-result.json).

General factory improvements: versioned quality guidance asks GLM for probes with observable effects on the actual inputs, keeping schemas, upstream calls and budgets. Citation guidance forbids ellipses and reconstructed JSON. Invalid fidelity assessments now retain their response and report `supported=false`, rather than discarding the campaign outcome through an exception. Seven focused tests passed. No scientific task or probe was manually edited.

The bounded diagnostic download filled before reaching final ledgers/cleanup records. It now prioritizes those records and permits 4 MB of selected diagnostics. A read-only job in replacement slot 6 recovers campaign 006's missing records and #18's previously recorded native stages: 1 CPU/1 GiB, at most five minutes, no model calls or Daytona creation. Four replacement slots remain. Scientific validation and release are still incomplete.


### 2026-10-10 UTC: recovered evidence and next campaign

Read-only recovery 007 succeeded. Campaign 006 used 13 requests (2 compatibility, 3 generation, 8 quality), and all ten native trial claims have verified cleanup. The four final native result files match their quality-record hashes. The quality rejection and invalid fidelity assessment remain unchanged. [Verified records](https://github.com/Open-Athena/biotasks/blob/1873ddde0a7099623ebf4cbdf8d88d9d9ded148b/experiments/19-repo2rlenv-notebook-pilot/campaign-006-result.json).

The old #18 panel audit is complete: twelve native stage records recovered; four infrastructure failures and eight not-runnable outcomes. All five sandbox IDs identified in those records were absent on provider read-back. No new #18 generation or sandbox mutation occurred.

Campaign 008 was submitted once from [1873ddd](https://github.com/Open-Athena/biotasks/commit/1873ddde0a7099623ebf4cbdf8d88d9d9ded148b), testing the general quality-probe and citation guidance described above. It uses replacement slot 7; three remain. The $5 per-campaign/$50 aggregate ceilings and all other approved bounds remain unchanged. No accepted task, blind solver attempt or release is yet claimed.


### 2026-10-10 UTC: cleanup race reconciled; campaign 009

Campaign 008 generated a task on the first build (four requests total). Generation controls completed with verified cleanup. The first quality baseline exited Harbor with code zero, but its cleanup reported NotFound, so the pipeline stopped before review or solver execution. A fresh query of its exact ownership label found no resources. [Original failure and separate reconciliation](https://github.com/Open-Athena/biotasks/blob/7f93dea27d9c110a38686c7e69e65b7918561144/experiments/19-repo2rlenv-notebook-pilot/campaign-008-result.json).

The existing execution-boundary patch now handles deletion races: a NotFound during deletion is followed by an independent ID check and a full ownership-label query. Other errors, wrong ownership, remaining resources and uncertain creation still block continuation. Seven cleanup tests pass, and all five pinned patches apply sequentially to original upstream source. No task artifact was manually changed.

Campaign 009 was submitted once from [7f93dea](https://github.com/Open-Athena/biotasks/commit/7f93dea27d9c110a38686c7e69e65b7918561144), using replacement slot 8; two remain. Bounds are unchanged. The upstream release download verifier is also prepared and tested, but scientific validation, a blind solver attempt and publication remain outstanding.


### 2026-10-10 UTC: successful native solver; continue from preserved evidence

Campaign 009 produced quality controls of no-op 0, reference 1, meaningful wrong solution 0 (skipped gene filtering), and independent alternative 1. GLM-5.3 then solved the task through Terminus-2: reward 1, no exception, four requests, about 178 seconds of agent execution under the 300-second limit. Eleven requests and nine native trials were used overall. The controller stopped afterward because cleanup's final list contained an ID whose direct read-back reported absence. A later exact-ID query and ownership-label query both confirmed absence. [Evidence and limitations](https://github.com/Open-Athena/biotasks/blob/22b714178b392937b05157a2d42f5a5d156070c7/experiments/19-repo2rlenv-notebook-pilot/campaign-009-result.json).

The cleanup adapter now independently checks final listed IDs rather than treating a stale list entry as a live resource. More importantly, upstream already supports importing native baseline, oracle and rollout results: all three original results successfully bind to the unchanged task via Harbor checksums. The factory uses this existing import path and the original GLM probe definitions, without manually changing task files or resetting consumed budgets. Relevant cleanup, continuation and factory-wiring tests passed.

Continuation 010 was submitted once from [22b7141](https://github.com/Open-Athena/biotasks/commit/22b714178b392937b05157a2d42f5a5d156070c7), with its task/evidence archive frozen by checksum. It uses replacement slot 9; one remains. Carrying prior use forward leaves seven native trials, at most one additional solver attempt, and 22 quality requests. The upstream loop can rerun its existing probes and use the one still-unused quality repair. It skips task generation. All resource/time/monetary ceilings remain unchanged. Final quality/fidelity review and public release are still outstanding.


### 2026-10-10 UTC: final bounded review/repair

Continuation 010 finished with upstream status `usable`, no quality repair, five requests and two repeated probes with verified cleanup. Its report retains the original no-op 0/reference 1/solver 1 and confirms wrong probe 0/alternative 1. The separate scientific-fidelity assessment was correctly rejected again because GLM fabricated a quotation containing an ellipsis. [Recorded result](https://github.com/Open-Athena/biotasks/blob/c0fdb34c159ababa9068a7c46bf810da17660a45/experiments/19-repo2rlenv-notebook-pilot/campaign-010-result.json).

Two general review gaps remain: the grader requires exact output ordering not explicitly required in the public instructions, and a root solver plus shared verifier means chmod alone does not establish a protected reference-data boundary. The versioned GLM review guidance now asks the worker to address undocumented representation constraints and reference-input integrity. Actual task edits remain GLM-authored and limited to the single still-unused quality repair.

Fidelity citations now use numbered document ranges, with exact passages resolved and validated by the controller; model verdicts remain advisory and cannot supply rewards. Existing unchanged probe receipts can be reused through upstream's hash-binding checks. Tests cover citation resolution, evidence tampering, budget carry-forward, disabled exhausted scopes and continuation wiring.

Final continuation 011 was submitted once from [c0fdb34](https://github.com/Open-Athena/biotasks/commit/c0fdb34c159ababa9068a7c46bf810da17660a45), using replacement slot 10. **No replacement slots remain.** Prior use is retained: 16 requests, 11 native trials, one solver attempt and zero quality repairs. The remaining allowance is five native trials, at most one further five-minute solve, 19 quality requests and one GLM quality repair; the exhausted compatibility allowance stays disabled. Resource, time and $5-per-campaign/$50-aggregate ceilings are unchanged. There has been no Hugging Face upload; final validation and release remain outstanding.


## Final approved campaign result — 2026-10-10

Replacement 011 (slot 10/10) finished successfully at the infrastructure level. The GLM-authored repaired task passed the reference, rejected the empty baseline and wrong-analysis probe, accepted the alternate implementation, and was solved by GLM-5.3 in 156.6 seconds (8 solver API requests). All five native result hashes and trial/preflight cleanup receipts were verified. The continuation chain used 32 requests, 16 native trials and two solver attempts.

**Release remains blocked.** Both staged and reference data copies are still writable by the root solver; comparing their hashes does not independently establish input identity. This is a static defect, not a demonstrated exploit. The separate scientific review identifies this failure and also fails citation validation because several line spans exceed the allowed maximum. Upstream quality's `usable` label is insufficient to override these findings. Scientific package/base-image pinning is also incomplete. No manual task repair or Hugging Face upload occurred.

All ten replacement slots are exhausted. No additional model/sandbox campaign is authorized. Keep this issue open: publication and the fresh download check remain unfinished. Further execution requires a new bounded authorization; the existing public Hub destination remains approved.

[Final result and accounting](https://github.com/Open-Athena/biotasks/blob/f8c6dee/experiments/19-repo2rlenv-notebook-pilot/campaign-011-result.json) · [Decision log](https://github.com/Open-Athena/biotasks/blob/f8c6dee/experiments/19-repo2rlenv-notebook-pilot/logbook.md).


### Prepared follow-up, awaiting authorization

Reusable prompts now explicitly classify mutable reference inputs as blocking and require citation-span self-checks. No generated task was edited and no new model/sandbox execution occurred. [One-campaign proposal](https://github.com/Open-Athena/biotasks/blob/bb36f1c/experiments/19-repo2rlenv-notebook-pilot/follow-up-proposal.md): one GLM repair, at most 40 new requests, five fresh scientific trials including one five-minute solver, two hours plus cleanup, and $5 Daytona usage. This is a requested new allowance; the exhausted ten-campaign authorization remains unchanged. Prompt changes have only been inspected with a clean diff check, not validated by a new campaign.


### 2026-10-13 — Additional campaign approved

The user approved the prepared follow-up: one additional campaign (012), up to 40 new requests (16 quality/review and 24 solver), five native validation trials plus one infrastructure preflight, one five-minute/12-turn solver attempt, one GLM-authored repair, two hours plus cleanup, and $5 Daytona usage. Existing CPU/RAM/disk, GLM-only, offline solving/grading and factory-only rules remain. Historical usage is retained separately and subtracted from cumulative ceilings. This supersedes the pending-approval status above; it does not authorize any additional replacement after 012.


Campaign 012 submitted once from [factory checkpoint 11cb1f0](https://github.com/Open-Athena/biotasks/commit/11cb1f0). Prior job states were verified terminal before submission. Local checks passed: five continuation/accounting tests, four mocked wiring tests, Ruff lint/format and ty. Both imported semantic-probe receipts were checked against their unchanged generated variants. Initial scheduler state was pending; submission is not a validation result.


### Campaign 012 outcome — infrastructure interruption

GLM authored a repair that checks the retained source archive against the pinned checksum in the private verifier before reference computation. Fresh native results: empty baseline 0, reference 1, wrong-analysis probe 0; no native trial exception. The campaign then stopped on `DaytonaConflictError` during cleanup after the third trial, although Harbor returned 0. Seven quality requests were used; no new blind solver ran. Scientific review, the alternate-implementation control, solver and release remain incomplete.

A fresh exact ownership-label query found no sandboxes at 2026-10-13 14:48:24 UTC. The failed cleanup did not retain a sandbox ID, so this is label-based reconciliation, not an exact-ID readback. Original receipts are preserved. The narrow cleanup patch now handles delete conflicts by independently checking ID and label absence; it still rejects live or uncertain resources. Ten cleanup tests and local lint/format/type checks passed; all six pinned patches apply to original upstream source. No manual scientific task edits.

[Results and remaining allowance](https://github.com/Open-Athena/biotasks/blob/5aeed9aab911d9b00da15cc20b2670c8a3ce7d43/experiments/19-repo2rlenv-notebook-pilot/campaign-012-result.json): 33 requests remain (9 quality/review, 24 solver), two native trials, one solver attempt and zero repairs. No recovery worker has been submitted. Resuming would preserve these remaining allowances and the existing $5 campaign ceiling, rather than request a fresh campaign budget.


### 2026-10-13 — $100 total budget and routine recovery authorized

The user approved recovery of the interrupted campaign within its remaining limits, then authorized up to **$100 total Daytona usage for issue completion**, with routine factory fixes, recovery and retries proceeding without repeated approval. This supersedes the earlier aggregate monetary/campaign-count stop conditions. Retain CPU-only resources, GLM-5.3, offline tools/grading, factory-only changes and explicit per-run request/time limits. Maintain cumulative accounting; the $100 is a ceiling, not a target or measured invoice.

The immediate recovery keeps campaign 012’s remaining 33 calls, two native trials, zero repairs, original absolute deadline and $5 ceiling including prior reservations. It imports completed raw native controls by task checksum and preserves the failed cleanup receipt alongside a separate ownership-label reconciliation. A new blind solver is required for this task revision.


### Recovery completed; final contract repair underway

Recovery 013 succeeded: the alternative implementation and fresh GLM solver both received reward 1. All five completed native controls/results are bound to the repaired task; cleanup passed. It used four quality calls and three solver calls. The scientific review again failed citation-format validation, and operator audit identified two remaining public-contract mismatches: an example annotation field treated as mandatory and unstated exact row/column ordering. Original evidence is preserved; no publication yet.

The factory now uses single-line citations and explicit general guidance on example fields versus mandatory output schemas and identifier order versus scientific equivalence. Campaign 014 allows one GLM repair followed by up to five fresh native trials, 40 new calls, one five-minute solver and two hours plus cleanup. It reserves $5 within the $100 aggregate budget: conservative total reservations $61, not measured charges. No generated task was manually edited. [Source and prior results](https://github.com/Open-Athena/biotasks/tree/2e0bd6e/experiments/19-repo2rlenv-notebook-pilot).


### Scientific feedback now drives repair

Campaign 014 used five quality calls and reused completed controls; it did not repair the task because upstream review called the ordering mismatch optional. The separate scientific review produced valid single-line citations and correctly failed public_contract. That failure is now fed into the upstream repair loop as a task-bound GLM finding. The adapter preserves original reviews, resolves the model-selected citations, checks current file contents and bundle identity, and never authors task changes. Old findings cease to apply after the task changes; release still requires a fresh scientific review.

Continuation 015 is frozen at [9ac75d6](https://github.com/Open-Athena/biotasks/commit/9ac75d6), using the current campaign’s remaining 35 requests, five trials, one repair and one solver attempt, with the same absolute deadline and cost reservation. Seven focused feedback/fidelity tests and local lint/format/type checks pass. Aggregate conservative reservations remain $61 of $100.


Continuation 015 stopped on an adapter error after one quality call and no scientific trials: upstream `_review` returns `(review, context)`. Tuple handling and its regression fixture were corrected in [1cc596a](https://github.com/Open-Athena/biotasks/commit/1cc596a). Preflight cleanup passed and all exported evidence was recovered. Continuation 016 was submitted once, carrying the used call and cost holds: 34 calls remain under the same campaign deadline and trial/repair limits. No additional monetary reservation or manual task edit.


### Focused schema audit added after release audit

Continuation 016 repaired identifier ordering and passed all native controls, a fresh solver attempt and the broad scientific review. Operator release audit still found an example annotation field unconditionally required by the grader. Rather than manually edit the task, the factory now inventories literal keyed accesses in Python graders and asks GLM to classify each against the public artifact schema, with exact source citations and complete inventory coverage. A mandatory-but-optional/absent public key becomes a blocking GLM finding for upstream repair.

Campaign 017 is frozen at [54d13f0](https://github.com/Open-Athena/biotasks/commit/54d13f0). Bounds: one GLM repair, five native trials, one five-minute solver, 48 requests (24 quality/review including the focused audit, 24 solver), two hours plus cleanup, $5 Daytona. Conservative aggregate reservations are $66 of $100. Local focused schema/feedback tests and code-quality checks pass. No task was manually edited or published.


### 2026-10-13 — bounded recovery after preflight timeout

Campaign 017 failed during the offline-network preflight before any model calls or native task trials; sandbox cleanup was verified. The factory now allows 60 seconds for the network probe command, retaining fail-closed behavior and the same isolation checks. Four preflight tests passed, including timeout cleanup. [Source and evidence checkpoint](https://github.com/Open-Athena/biotasks/commit/8a871a9).

Recovery 018 was submitted within the original campaign deadline and $5 reservation, carrying $0.088 in prior conservative cost holds. It retains the remaining 48-call ceiling, one GLM repair, five native trials and one five-minute solver attempt. Aggregate conservative reservations remain $66 of the authorized $100; these are budget holds, not an actual invoice. No task-specific manual changes or publication occurred.


### 2026-10-13 — release evidence portability checked

The upstream label exporter failed to locate probe provenance at a temporary worker path. On a disposable local copy of campaign 016 evidence, upstream probe reconstruction reproduced both bundle identities and original Harbor checksums, and upstream label validation succeeded with unchanged raw trial results. A derived quality report remaps only evidence paths; original reports remain preserved. [Reconstruction helper and evidence](https://github.com/Open-Athena/biotasks/commit/6d127bc). This addresses packaging only: campaign 016 remains ineligible for publication because of its known instruction–grader mismatch. Recovery 018 is still running; no release has been published.


### 2026-10-13 — review follow-up and bounded recovery

The independent reviewer rechecked the infrastructure fixes at 0868488 and reported no residual actionable findings; eight tests passed independently. The HTML explorer passed public HTMLPreview desktop/mobile navigation after the embedded-data fix at 6efd741.

Campaign 019 returned needs_evidence because its schema review omitted a field. It used four quality calls and no repairs/native trials; preflight cleanup was verified. Generic conversion-specific GLM review now supplements the broader review, and schema inventory incompleteness gets one bounded retry. Three focused audit/feedback tests pass. [Source checkpoint](https://github.com/Open-Athena/biotasks/commit/d6c1672).

Recovery 020 submitted with the original deadline and $5 reservation, carrying prior $0.088 cost holds and four used requests. Remaining ceilings: 20 quality calls, 24 solver calls, one GLM repair, five native trials and one five-minute solver. Aggregate conservative reservations remain $71 of $100. Scientific correction and replacement publication remain pending.


### 2026-10-13 — GLM count-metadata repair and continued validation

Recovery 020 produced a GLM repair that checks integrality before converting detected-gene counts. Four native controls passed (reference 1, empty 0, wrong output 0, alternative 1), but no fresh solver attempt ran. The controller erroneously treated private verifier settings marked not_applicable as public-output requirements and stopped the run. That generic classification bug is fixed and regression-tested. Boolean truthiness remains a representation gap; the generic conversion audit now explicitly checks original values rather than treating a comparison after casting as sufficient. No task was manually patched.

[Checkpoint 1766fc8](https://github.com/Open-Athena/biotasks/commit/1766fc8) preserves the failed quality outcome and repaired task evidence. Campaign 021 has been submitted with one repair, five native trials, one five-minute solver, 24 quality and 24 solver calls, two hours plus cleanup, and a fresh $5 reservation. Conservative reservations are $76 of $100. The existing public release remains unchanged; corrected publication is pending.


### Recovery 022: citation validation retry

The focused GLM audit identified the remaining Boolean-metadata false acceptance. Campaign 021 stopped when a later schema-audit quote omitted Markdown formatting. Recovery 022 uses a tested, single bounded retry for malformed citations; invalid evidence is still rejected. It retains campaign 021’s deadline and $5 reservation, with 17 quality requests, 24 solver requests, one repair, five native trials and one five-minute solver remaining. Aggregate conservative Daytona reservations remain $76 of the authorized $100. The published release and HTML remain historical until the replacement passes validation and fresh-download verification.


### Compute-policy clarification — 2026-10-13

Task suitability is governed by CPU-only execution and configured CPU, RAM, disk and time limits; there is no categorical model-training exclusion. [Factory update](https://github.com/Open-Athena/biotasks/commit/b2f220e) removes that inherited SETA restriction and fixed resource wording from both design and builder prompts. The controller now renders the run budget from configuration. The completed pilot’s 1 CPU / 2 GiB / 10 GiB profile was a conservative choice matching upstream defaults, not Daytona’s maximum. Historical artifacts and recorded prompts remain unchanged. No new model or sandbox run was performed for this policy change.


### Prompt review: design-only call — 2026-10-13

The user is reviewing revised prompts before any full rerun: 4 vCPUs / 8 GiB / 10 GiB, CPU-only, ten-minute solver budget. After reviewing the cleaned design prompt, the user authorized one design-only GLM-5.3 call on the same Scanpy seed. It returned a schema-valid response in 82.88 seconds (6,869 input / 2,649 output tokens), with no retry, builder, repair, native validation, solver or Daytona sandbox. [Unmodified draft specification](https://github.com/Open-Athena/biotasks/blob/46e7b95/experiments/19-repo2rlenv-notebook-pilot/design-reviews/001/draft-spec.md) and [separate initial observations and exact records](https://github.com/Open-Athena/biotasks/tree/46e7b95/experiments/19-repo2rlenv-notebook-pilot/design-reviews/001) are available for review. Scientific inconsistencies remain in this proposal; no corrections were applied. The viewer was left unchanged, and no later pipeline stage is authorized until the user reviews the response.


### Seed and task-design responsibility — 2026-10-13

The user selected the newer Scanpy `clustering.ipynb` notebook and clarified that task design, including biological objective and analysis scope, belongs to the GLM worker. The current seed now contains the complete notebook source and factual provenance only; the previous manual QC/normalization restriction is removed. [Current seed and provenance](https://github.com/Open-Athena/biotasks/tree/dd2d948/experiments/19-repo2rlenv-notebook-pilot/seeds) and [updated design prompt](https://github.com/Open-Athena/biotasks/blob/dd2d948/src/biotasks/prompts/notebook-task-design.md) are committed. The worker must justify its scope against general resource and quality constraints. Prior pilot artifacts remain unchanged. No new model call or viewer update was performed.


### Newer-notebook design-only response — 2026-10-13

The user authorized one design call using the newer notebook and updated prompt, with no manually specified task scope. GLM-5.3 returned a schema-valid draft in 38.95 seconds (7,360 input / 3,246 output tokens), choosing preprocessing, clustering, differential expression and NK-cell identification. [Unmodified response](https://github.com/Open-Athena/biotasks/blob/5ede6de/experiments/19-repo2rlenv-notebook-pilot/design-reviews/002/draft-spec.md) and [exact request/response records](https://github.com/Open-Athena/biotasks/tree/5ede6de/experiments/19-repo2rlenv-notebook-pilot/design-reviews/002) are preserved. Resource estimates, scientific details and proposed fallbacks remain unvalidated proposals. No retries, construction, repair, native validation, solver, Daytona sandbox or viewer update. Stop at user review.

### 2026-10-13 — Design prompt revision and isolated review 003

Added general requirements for methodological fidelity, explicit artifact/test coverage, stage-correct scientific checks, justified tolerances, and a consistent final contract to the [canonical design prompt](https://github.com/Open-Athena/biotasks/blob/aade723/src/biotasks/prompts/notebook-task-design.md). Ran one GLM-5.3 design call on the same newer Scanpy notebook, with unchanged seed and inference settings. The [unmodified draft](https://github.com/Open-Athena/biotasks/blob/3eefc0b/experiments/19-repo2rlenv-notebook-pilot/design-reviews/003/draft-spec.md) and [execution evidence](https://github.com/Open-Athena/biotasks/tree/3eefc0b/experiments/19-repo2rlenv-notebook-pilot/design-reviews/003) are preserved. The call completed in 19.68 seconds; its JSON adds an unexpected difficulty field and therefore fails the requested top-level schema. Scientific validity remains untested and the draft still has unresolved methodological and grading choices. Stopped for user review: no retry, construction, native validation, solver attempt, or viewer update.

### 2026-10-13 — Design-only findings and upstream reuse proposal

The user authorized further design-only iteration without seed-specific hardcoding or overfitting, then requested inspection of other pipelines, including Tasksmith and prepared-data/tool access. Reviews 004–013 preserve six design calls and four critique calls on the unchanged newer notebook. General prompt revisions and larger reasoning/output budgets did not reliably resolve contract and verification errors; some critique responses exhausted their output budget. This adaptive development series is not a controlled comparison or generalization evidence. [All preserved records](https://github.com/Open-Athena/biotasks/tree/942f9fa/experiments/19-repo2rlenv-notebook-pilot/design-reviews) include the schema-valid but rejected [draft 013 and static review](https://github.com/Open-Athena/biotasks/tree/942f9fa/experiments/19-repo2rlenv-notebook-pilot/design-reviews/013). No generated output was manually repaired; no construction, native validation, solver or viewer update ran.

Static upstream inspection found that original SETA has a tool-enabled notebook idea agent consuming prepared dataset manifests; the selected Repo2RLEnv adaptation instead makes a tool-free structured call. Tasksmith's schema-parametric artifact controller is already available at our pinned revision and can be reused without adopting its PR-specific task definition. Its current model runtimes need a GLM adapter; source inspection is not a compatibility test. The proposed next mechanism is factual intake plus bounded inspection within one GLM design stage, preserving worker ownership of the scientific objective and the existing SETA builder/quality/release path. [Exact sources, reuse boundaries, alternatives and proposed checks](https://github.com/Open-Athena/biotasks/blob/942f9fa/experiments/19-repo2rlenv-notebook-pilot/design-intake-reuse.md).

Further text-only iterations stop pending review of this proposal. The architectural changes remain proposed, not implemented; the completed public pilot release remains unchanged. The next step is to review the concrete runtime/intake adaptation and canonical prompt before another design-stage run.

### 2026-10-13 — Prepared factual intake and bounded design tools

Prepared the agreed design-stage adaptation on the research branch: a narrow runtime-injection patch reuses Tasksmith's artifact submission, revision and retention controller with SETA's existing TaskDesign schema. GLM-5.3 retains ownership of the scientific question, scope and task-specific revisions. The profiler records source hashes and bounded structural facts without selecting an analysis; unknowns remain explicit. The [actual canonical prompt](https://github.com/Open-Athena/biotasks/blob/3d92a14e0758e3854a14bf0e4549b424400ed527/src/biotasks/prompts/notebook-task-design.md) now supports evidence-driven inspection and a compact proposal.

The adapter preserves request/response and tool evidence, enforces a durable request ceiling, reserves the final two calls for submission/revision, and stops incomplete or uncertain operations without automatically retrying them. The old direct-call campaign refuses this prompt before model or sandbox activity. Root checks, five design-stage integration tests, five affected campaign-wiring checks, two native HDF5 fixture checks and sixteen upstream artifact-stage regressions passed; the SDK test used a mock HTTP transport. These are software checks, not live model or scientific validation.

[Concrete implementation, proposed finite budgets and remaining launch requirements](https://github.com/Open-Athena/biotasks/blob/3d92a14e0758e3854a14bf0e4549b424400ed527/experiments/19-repo2rlenv-notebook-pilot/design-intake-reuse.md) are recorded for review. A real run still needs a prepared remote workspace, factual input profiling, live endpoint compatibility and owned-resource accounting/cleanup. No new model call, biological download, remote sandbox, construction, solver, release or viewer update occurred in this preparation.
