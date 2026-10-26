# Sgkit 194 — setup-budget restoration failure

The original host and pipeline ended in infrastructure failure during setup. No controlled scientific reference, construction, grading, solver or publication ran; this does not establish a broken or unsuitable notebook.

Input staging and exploration consumed most of the cumulative setup-tool allowance. The controlled build received its remaining 163 seconds and returned a verified completion receipt reporting a timeout. The following trusted authoring-workspace restoration could not dispatch because the setup allowance was exhausted. The controller recorded `restoration_failed` with `SetupBudgetExceeded`, marked remote state uncertain, returned the budget result to the worker, and then rejected its next tool call at the uncertain-state guard. [Hash-bound original sequence audit](budget-boundary-audit-194.json). No command or worker was replayed.

The general gap is lifecycle treatment of known budget exhaustion: it must terminate the stage without spending extra time or resuming an unsafe workspace, while retaining any genuinely uncertain operation as uncertain. The original outcome remains infrastructure failure. A future controller fix must preserve scientific and resource limits, report the typed boundary and retain cleanup.

All 858 science files (32,464,745 bytes) and 21 root files (988,443 bytes) were independently read back and hash/size/mode verified. Original deletion receipts plus fresh exact sandbox-ID/owner absence are verified. Pipeline time was 39.76 minutes with 91 recorded request attempts. Original data/notebook/task redistribution remains unestablished, so those bundles stay private. [Result](result-194.json), [performance](performance-194-detail.json), [cleanup](../../autonomous-runs/194/provider-cleanup.json).

Only the four undispatched stage allowances were released. The full $1 used-stage hold remains; no invoice, credit or finer resource-lifetime claim is made.
