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
