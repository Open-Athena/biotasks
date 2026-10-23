# Control completion and timeout comparison

The exact inventory in `control-plan.json` binds original task files and bootstrap reconstruction records to the original archive/member hashes. No tasks are regenerated. The script `inventory_controls.py --baseline-root <issue28-history-wide>` derives this plan from the original assessments and manifests.

## First stage: existing exports, no model calls

| Repository | Existing exports | Original missing controls | Proposed commands |
| --- | --- | ---: | ---: |
| Matchms | 671, 675, 70, 98 | 7 | 8 at 300 seconds |
| OHIF | 6334, 6339, 6346, 6352 | 7 | 8 at 300 seconds |
| Scanpy | 4389 | 0 unstarted; 2 timed out | 4: nop/oracle at 300 and 1,200 seconds |

The proposed count is 20 rather than 14: Matchms671/OHIF6334 have only one original missing side, but both controls must run on the same newly reconstructed image to support a pair claim. Scanpy adds two timeout arms with both controls. Previously completed controls remain separate evidence.

Keep Harbor0.6.6, one control at a time, 1 CPU/6 GiB, original tests/patches and original internal timeout-retry behavior. Override only the verifier allowance for the 1,200-second arm, without editing the task files. Runtime configuration and original files must be hashed before/after. Image reconstruction is a material comparison limit: original images were deleted, and saved recipes can contain unpinned packages or malformed transcript commands. Inspect recipes before submission, retain digests/freezes, and stop rather than manually repair a repository.

Proposed bound, not a launched allocation: three serial existing-reserved-TRC jobs, each 4 allocated CPUs/16 GiB and 160 minutes maximum, at most 32 allocated CPU-hours total; $0 model calls and no new capacity. Each job includes build/controls/archive/cleanup time. Worst-case verifier intervals including the original one retry are 80 minutes for each 8-command scheduling group and 100 minutes for Scanpy's four commands. Environment preparation may still exhaust the outer bound; report unstarted commands explicitly. Set a separate final cleanup reserve and stop starting controls when their entire allowed interval cannot fit.

No current execution budget or submission is asserted by this proposal. Validate the actual runner configuration, supported verifier override, current worker compatibility, and original Docker resource wrapper before execution. Matchms requires the protected local originals; its public curated snapshot does not contain full runnable packages. Do not upload additional Matchms content under the original curation approval.

## Later, separate acquisition/bootstrap comparisons

OpenMS: upstream `bootstrap/runner.py` hard-codes checkout60 seconds; the outer `max_seconds` option cannot change it. A small configurable checkout change and 60→300 comparison should end at checkout completion, without automatically starting model bootstrap.

MMseqs2: compare bootstrap1,800→3,600 seconds with the same model,20turns,2048tokens and other limits. The individual shell-command300-second bound stays separate. This arm needs an explicit cumulative model allowance and a checkpoint before calls; it is not included in the $0 first stage or a reset of #28's budget.

## Evidence and completion

Report raw verifier completion, expected base failures, preserved tests, oracle passes, full-command status, wall time, allocated CPU-hours, missing data and any reconstruction drift separately for each arm. Do not infer valid tasks from a timeout disappearing. Until these controls execute and are archived/read back, #29 remains incomplete.

## Original-recipe syntax preflight

`reconstruction-readback.json` verifies all three original bootstrap records. `reconstruction-findings.json` reports zero syntax errors across Matchms 4, OHIF 18 and Scanpy 16 saved RUN bodies. This is a syntax-only result, not a successful image build. Raw metadata remains local under ignored `inputs-private/`; public findings contain only identities, hashes, flags and syntax diagnostics. The protected Matchms original remains untouched.

## Verified Harbor timeout control

The SHA-verified Harbor 0.6.6 wheel exposes `harbor run --verifier-timeout-multiplier 4`. Its trial code multiplies only the verifier limit when that specific option is set, leaving the general multiplier and other stage allowances unchanged. With the original task verifier value 300 seconds and unset override/max values, this yields 1,200 seconds without editing task files. Use multiplier 1 for the baseline arm and retain -r0/original internal retry behavior. Exact CLI, model and trial sources/license are in `harbor066-source/`, bound by `harbor066-provenance.json`; no package was installed or imported.

## Controls-only runner and reconstruction caveat

`prepare_control_inputs.py` extracted only the nine selected original task packages and verified all 90 files against the original sizes, modes and SHA256 values. Protected Matchms content remains under ignored private local storage; no raw package was republished. `run_existing_controls.py` dry-runs all 20 commands with Harbor 0.6.6, 1 CPU/6 GiB, retries disabled at job level, and verifier-only multipliers 1 or 4. It checks task identity before and after execution, reserves 300 seconds for cleanup, and stops after any wrapper timeout so a supervisor can remove owned containers before further work.

Each trial reserves two verifier intervals plus 300 seconds for setup/teardown: 900 seconds at baseline and 2,700 seconds at the longer timeout. Each repository's controls therefore reserve 7,200 seconds, plus a 300-second cleanup reserve. Within a 9,600-second job, at most 2,100 seconds remain for controller setup/image reconstruction and overhead; if preparation consumes more, unstarted controls must be reported rather than reducing their limits. No remote supervisor or image build has been submitted.

`recipe-history-results.json` strengthens the earlier syntax-only check. Scanpy's saved recipe includes the exact step 7 command that originally exited 1 with an externally-managed-environment pip error. A fresh verbatim build may stop there before the successful later venv setup. This is an original observed failure, not a fresh build result; environment drift prevents claiming inevitable replay failure. It is distinct from verifier timeout and cannot be silently repaired or skipped. OHIF's BASH observations all reported exit 0, but piped commands can mask failures. Prioritize Matchms/OHIF reconstruction; retain Scanpy as an explicitly unresolved reconstruction prerequisite if the unchanged recipe fails.
