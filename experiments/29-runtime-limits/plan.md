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
