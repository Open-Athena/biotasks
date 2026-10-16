# Repo2RLEnv cross-language experiment

## 2026-10-16 — preparation

- Published issue #21 and verified the exact body and agent-generated label.
- Started codex/research/21-repo2rlenv from main at 2a1950d239f1ada467c35393991dac87debe35f7.
- Pinned Repo2RLEnv, four biological source repositories, and Marin in source-manifest.json.
- Inventoried 23 executable routes plus planned SEC-bench in applicability.csv. These are static assessments, not execution results. No model calls, generation, biological execution, or workers launched.
- The non-Python panel exposes a real gap: native runtime log dispatch has no R/testthat or bedtools shell-test parser. C++ bootstrap support alone cannot establish test-based task generation. Preserve unmodified baseline blockers before considering adapters.
- Biopython uses Tests/run_tests.py, a custom PyUnit runner with offline selection; scikit-bio keeps tests under skbio. Explicit source/test profiles are needed rather than assuming a root tests directory. Parser compatibility is untested.
- Tasksmith requires an Anthropic author. CodeMidas documents dedicated Sol/Luna stages; its GLM substitution remains unresolved. Neither is authorized to fall back to paid models.
- Native equivalence_tests exposes its reference in the learner image. Record generation separately from isolation acceptance.

Next: inspect dedicated model paths and cap semantics, select bounded historical candidates, prepare Python profiles, and fix the worker/backend and aggregate execution ceilings. Budget fields left null are unresolved, not unlimited. Seed routes need separately frozen cohorts. Any billable worker launch requires an agreed allowance.

### Bounded PR discovery

Recorded ten merged PR locators per repository in pr-discovery.json (40 total), using the CLI default updated ordering. These are discovery records, not 40 generation attempts. Titles suggest useful leads: Biopython #5344 (alignment score), scikit-bio #2630 (sequence case conversion), bedtools #999 (genome-file line endings), and DESeq2 #118 (greaterAbs with useT). Source/test diffs, historical environments, and exact execution base/head commits remain to inspect. Documentation-only and maintenance changes stay in the discovery ledger rather than disappearing from the denominator.

## 2026-10-16 — native PR-diff run and independent diagnostics

- Checkpoint d1a7d15 recorded the four-cohort, ten-candidate, zero-model/worker run. Native generation completed in 53.71 seconds at 45,932 KiB peak RSS; no owned worker remained. Local load/memory stayed within the shared-node thresholds.
- Forty candidates yielded 19 exports: Biopython 4, scikit-bio 3, bedtools 6, DESeq2 6. All native skips are retained. Exact bundles, checksums, configurations, and logs are in evidence/pr-diff-01.
- Scorer-only controls produced oracle=1 and empty=0 on all 19. Reversing added/deleted lines still scores 0.806–0.900. This string-level probe demonstrates similarity sensitivity, not an executable exploit or biological grading result.
- Bounded pinned-file downloads and git apply --check succeeded for 17/19 patches. bedtools #1067 and #1083 fail against the base recorded by the generator. One passing patch has a file-mode warning because raw downloads do not preserve executable bits. No full checkout or container has been tested.
- Instruction inspection found maintenance/docstring/vignette tasks, contribution-template boilerplate, explicit solution hints, and GPU-related content among exports. Repository membership and oracle score alone do not establish useful biological tasks.
- Current pinned pr_diff code keeps the oracle/verifier in tests/, not the learner Dockerfile; this differs from the older published dataset assessment. Runtime isolation still requires validation.
- Confirmed CodeMidas is also incompatible with GLM configuration alone: recipe_options.py restricts author/reviewer to Sol/Luna, pipeline.py rejects custom endpoints, and the dedicated OpenAI agent has a matching allowlist. Record it as a model blocker, alongside Tasksmith, before any optional adaptation.
- Installation initially failed because the selectively extracted source omitted THIRD_PARTY_NOTICES.md. Restoring it from the same archive allowed locked installation; original failure retained. This was preparation, not a generation candidate failure.

No tasks are independently validated or admitted to Marin yet. Patch failures, scientific relevance, container execution, and remaining recipes are still open; the research objective is not complete.

### Confirmed newline defect

The two failing bedtools patches are not a base-selection error. Fetching gh pr diff as bytes preserves 13 CRLF lines for #1067 and 8 for #1083. Each raw patch applies to the same recorded base files. Replacing CRLF with LF produces exactly the exported patch bytes. The pinned GitHub client's subprocess.run(text=True) performs this normalization. Evidence is in evidence/pr-diff-01/newline-diagnosis.json; keep the original failed exports unchanged. This is a concrete non-Python-panel finding and motivates a separately recorded byte-preservation intervention.

Prepared remote_worker_probe.py and remote-execution-proposal.md. The backend probe is import/argument checked only, with no provision call made. User approval is pending for the proposed $25 / eight aggregate remote-hour CPU allowance; GLM call/token limits are proposed and generation guards remain to implement. No paid fallback is permitted.

Ruff 0.16.9 formatted the experiment scripts after execution; it also flagged a loop-variable capture in the synchronous progress callback. Bound that callback explicitly for future runs. The original executed script revisions remain preserved by their pre-run commits.

## 2026-10-16 — byte-preserving intervention and Marin contract inspection

Previous goal turn made progress (native generation and diagnostics), not a verified remote wait. Remote CPU approval remains unanswered; no paid action was taken.

Checkpoint 19f0eb8 records a separate GitHub-reader patch and frozen-input replay. On the same two PR inputs, the original reader/emitter loses CRLF and both oracle patches fail; the intervention preserves exact original diff bytes and both apply. Public instructions remain byte-identical. JSON output and UTF-8 subprocess-error behavior also pass. Both replays completed in under one second without network, models, containers, or biological code execution. The complete fixture/replay archive and hashes are in evidence/newline-intervention. This is a narrow reader/emitter regression result, not a full pipeline rerun or independent task acceptance.

Inspected the pinned Marin TaskSpec and repository conversion/export contracts. The generic-looking Harbor exporter is the reverse direction; existing TaskTrove SWE converters require a different test-ID contract. Recorded the required native workspace/reward/private-resource mapping in marin-contract-assessment.md. /workspace versus /testbed and Git-state capture need explicit treatment before any runtime parity claim. No converter or Atlas release has been executed.

## 2026-10-16 — approval correction and interrupted probe

The user approved a $100 ceiling. I incorrectly treated that reply as approval of all proposed operational and model limits and launched the first zero-model Daytona probe. The user immediately clarified that other limits require agreement. Sent SIGTERM to the exact probe controller; it exited after 25.38 seconds (113,244 KiB peak RSS). Creation had not returned an identity, so the native receipt correctly remained creation_uncertain. Reconciled the unique provider name, found and deleted that sandbox, and confirmed a subsequent lookup returns DaytonaNotFoundError / HTTP 404. Private cleanup-result.json preserves this evidence; the stale native receipt is not evidence of a live worker. No model calls or biological execution occurred. Cost remains unreconciled and the $5 reservation remains held conservatively. No new dispatch until operational limits are agreed. Corrected remote-execution-proposal.md to distinguish the approved dollar ceiling from proposed limits.

## 2026-10-16 — static Python cohort selection

Previous turn provided format advice and requested separate limit agreement; it did not execute work. Continued only local preparation while that answer remains pending. Recorded pinned SeqUtils and alpha-diversity source/test selections in python-profile-selection.json. The Biopython CAI initialization fixture expects the Tests working directory; preserve this test and explicitly resolve compatibility with the shared runner's /workspace working directory. Do not silently filter it out to get a passing baseline. The scikit-bio suite uses inline test inputs; it is not an observed-data cohort. Neither profile establishes baseline execution or applies automatically to unrelated historical changes. Updated source-manifest.json to reflect the interrupted worker launch, confirmed cleanup, approved $100 ceiling, and unresolved operational limits; the previous zero-launch field was stale.

## 2026-10-16 — separately agreed execution limits and seed inspection

The user separately approved up to four simultaneous remote CPU sandboxes; initial allocation of 2 vCPUs, 4 GiB RAM, and 10 GiB disk each; a fresh 30-minute compatibility probe with cleanup afterward; no aggregate remote-hour cap beyond the $100 campaign budget; and an initial two-hour generation-run timeout. Model-call and token allowances remain unresolved. These approvals do not authorize parallel Codex agents. Recorded eight seed-route input contracts and biological eligibility gaps in seed-input-assessment.md; no seeds or tasks generated in this inspection. No worker relaunched during these questions.

## 2026-10-16 — backend probe passes; model limits agreed

After separate compute approval, the second Daytona probe completed successfully: byte-preserving transfer, Docker build, offline container, fresh-container reset, and native cleanup. Controller elapsed 7.73 seconds, peak RSS 108,756 KiB; measured local load/memory remained within shared-node limits. A separate provider lookup confirmed HTTP 404 after deletion. No model calls or biological execution occurred. Sanitized result is evidence/daytona-probe-02/summary.json. Preserve $5 reservations for each of the two probes ($10 total against $100) until charge reconciliation; these are conservative reservations, not measured charges. No owned workers remain.

The user separately agreed no additional global GLM call-count cap, no global token cap while preserving native per-request output limits, and up to four concurrent GLM requests across the campaign. Native repair limits, three validated tasks / ten candidate attempts per applicable cohort, two-hour generation timeout, and free GLM only still apply. The earlier 30/500-call and eight-million-token proposals are superseded. Next execution gate is an actual GLM route/schema compatibility check and enforcement of campaign-wide concurrency, followed by frozen repository environments. Backend acceptance is not task validation or Marin conversion.

## 2026-10-16 — preservation preparation and GLM client preflight

Prepared hf-snapshot-manifest.json with hashes and sizes for all 19 original task bundles, diagnostic reports, and the separate newline replay, including every archive member. Its allowlisted payload totals 423,946 bytes. HF destination/visibility awaits the user's UI answer; no upload or public release has occurred. Native Repo2RLEnv push_to_hub supports dataset publication but performs in-place image/task preparation; exact-byte archival should preserve the original bundles before any such transformation.

Prepared probe_glm_client.py for a single native-client JSON-schema request, with no fallback/retry and no repository execution. Ruff lint/format and argument parsing pass; the probe has not made a request. Read-only Iris inspection confirms an approved relay job is running; this establishes scheduler state only, not endpoint reachability or model/schema compatibility. Private discovery remains outside public artifacts. The upstream metered_complete treats zero-price responses as uncertain cost even when token usage exists; free-service accounting needs an explicit recorded treatment rather than pretending its paid-cost ledger measures free GLM consumption.

## 2026-10-16 — public artifact preservation complete

The user chose public preservation. Uploaded the exact allowlist plus source notices to the existing open-athena/biotasks HF bucket under research/21-repo2rlenv/2026-10-16/8fe7d33b4f42f1489b95c391806786ae76031065ed66abc62f5fc2118328fc79/. Verified anonymous fresh download of all 17 objects and hashes/sizes/modes of all 226 regular archive members. No overwrite or deletion performed. Manifest was checkpointed in 4f694d8 before upload; receipt is hf-upload-receipt.json. Transfer elapsed 2.25 seconds with 89,952 KiB peak RSS, exit zero. The snapshot is preserved research evidence, with 19 generated and zero independently validated tasks. Private service/provider artifacts and credentials were excluded.

## 2026-10-16 — free GLM native-client schema probe succeeds

The first Iris probe failed in setup because the trimmed workspace omitted config/, required by a dependency's wheel force-include. No model request ran. Preserved that failure, then submitted a separate corrected bundle with the directory included. Both attempts used 2 vCPUs / 4 GiB RAM / 10 GiB disk, a 30-minute job deadline and zero scheduler retries. Local submissions peaked at 280,112 and 272,196 KiB respectively, within the shared-node limits.

The second attempt completed with scheduler state SUCCEEDED. The pinned Repo2RLEnv complete() client successfully used free GLM with an explicit custom endpoint/key and strict JSON-schema response: one request, 36 prompt tokens, 32 completion tokens, 5.87 seconds. Native client estimated $0; that is not a provider receipt. No paid fallback, biological execution, or task solving occurred. Sanitized reports are evidence/glm-preflight/attempt-01.json and attempt-02.json. Private route discovery and job handles remain outside public artifacts. Both Iris attempts are terminal; no Daytona workers are active. Preserve $20 total conservative reservations across the four probe attempts pending reconciliation.

This establishes the basic generation-client route and schema compatibility. It does not validate recipe-specific prompts, free-service ledger settlement, global concurrency enforcement, or the Harbor solver path, whose pinned wrapper rejects custom endpoints.

## 2026-10-16 — pinned scikit-bio baseline dispatched

Checkpoint 73a6f46 records a remote Docker build and offline alpha-diversity test run for scikit-bio at bd05e60efb0e6398aa6dc1485832c80a1104511b. One approved 2-vCPU / 4-GiB / 10-GiB Daytona sandbox is running under a two-hour controller deadline; test container is restricted to one CPU, 2 GiB, no network. No model calls or mutations are included. The controller will preserve build/test outputs, JUnit, image inspection, and pip freeze before finally deleting the sandbox. At this checkpoint the build is still in progress, with no test outcome established. Private receipt directory: skbio-baseline-01 in the task's private temporary workspace. Total conservative reservations are $25 against the $100 ceiling; do not interpret them as measured charges.

## 2026-10-16 — scikit-bio offline baseline passes

The baseline completed in 147.38 seconds with local controller peak RSS 109,272 KiB. Package build succeeded; the selected alpha-diversity suite passed 34 tests and 8 subtests in 1.97 seconds without network, on one CPU / 2 GiB, with no OOM. Native cleanup terminated the sandbox; a subsequent provider lookup returned HTTP 404. Evidence, JUnit, installed-package freeze, sanitized image identity, and checksums are in evidence/skbio-baseline-01. The first build resolved dependencies during installation; freeze captures installed packages but does not retroactively pin isolated build dependencies or the base tag.

Checkpointed swe-smith-skbio-worker.json against the pinned native RepoSpec and SWESmithOptions schemas: source alpha/_base.py, the same test suite, target three contrasts, at most ten candidate attempts. This worker target is an intermediate contrast count, not the issue's independently validated acceptance count. The native worker changes bootstrap details (including plugin auto-loading), so it must establish its own healthy baseline. No mutation, issue authoring, Harbor validation, or independent task acceptance is claimed yet.

## 2026-10-16 — native mutation worker dispatched and public progress published

Checkpoint 53f19b9 preceded the native SWE-smith worker dispatch on the pinned scikit-bio profile. One 2-vCPU / 4-GiB / 10-GiB sandbox is running; the native event journal reports bootstrap started, with Docker build processes active. No candidate contrasts, issue authoring, or acceptance outcome exists yet. Controller retains the existing run handle and will export partial evidence before cleanup. Conservative reservations now total $30/$100; no model request is part of this worker stage.

Published the research branch (without merging it) and progress comment https://github.com/Open-Athena/biotasks/issues/21#issuecomment-6224457725. Fetched the comment back and verified it matches the draft apart from the terminal newline. The comment links the public HF archive and immutable baseline evidence, and explicitly retains all remaining scope and the zero independently validated count.

## 2026-10-16 — native baseline passes; mutation dependency corrected

The first native mutation worker terminated after 152.55 seconds (109,844 KiB local peak RSS). It passed 34 healthy tests, then failed before any candidate attempt because the experiment harness omitted the mutation extra (libcst). This is our runtime setup error, not a biological task failure. Preserved selected evidence in evidence/skbio-smith-01; the complete 13,950,105-byte archive remains local with its hash recorded, pending the next HF snapshot. Verified provider deletion with HTTP 404.

Commit be234c7 adds the mutation and harbor extras used by the upstream runtime installer. A separate corrected launch was attempted, but nonblocking flock returned immediately because the shared lock was held; no new controller or sandbox started, and no additional $5 reservation was made. A later read-only lock-owner snapshot showed no holder; no waiting/polling loop was launched. Prepared author_swe_smith_issues.py for native issue authoring from saved contrasts through the already verified GLM client route; lint/format checks pass, but this script has not made model calls. Conservative existing reservations remain $30, not $35.

## 2026-10-16 — corrected worker running; solver coverage agreed

The corrected SWE-smith worker launched at 20:55:08 UTC after the shared lock became available, using the checkpointed mutation and Harbor extras. Its controller is still running; no outcome is claimed. Conservative reservations now total $35/$100, not measured charges. This is a separate attempt following the preserved missing-dependency failure.

The user separately approved evaluating all tasks that pass reference/grader validation and one blind GLM solver attempt per task initially. Solver-specific limits and custom-endpoint compatibility remain unresolved; no solver has been dispatched. Evaluation remains within the existing free-GLM, four-request concurrency, and $100 campaign limits. Public task and evaluation artifact preservation applies.

The corrected worker subsequently completed in 182.17 seconds, peak controller RSS 109,376 KiB. Its healthy baseline passed 34 tests and all three attempted mutations produced executable failing-versus-healthy contrasts (kempton_taylor_q, strong, esty_ci). No model calls occurred. Selected evidence is in evidence/skbio-smith-02; the complete 14,010,827-byte archive is preserved locally pending public archival. Native cleanup reports termination; independent provider lookup remains pending. These are three mutation candidates, not yet authored, exported, independently validated, or solver-scored tasks.

Independent provider lookup confirmed HTTP 404 for the corrected worker. Preparing a separate GLM authoring job on the previously verified service route: three candidates, native maximum two authoring attempts each, serial requests, native 4,096-token output limit, no fallback. No solver runs are part of this stage. The job carries saved contrasts into a model-client environment without executing repository code, and exports authoring receipts before termination. Reserve another $5 only upon dispatch ($40 total). Estimated local submission peak is 320 MiB based on the previous 272 MiB submission plus the 14 MiB input archive; apply the shared lock and thread limits.
