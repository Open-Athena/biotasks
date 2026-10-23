Can timeout and scheduling changes recover complete positive control pairs without repairing tasks? Follow-up to #28; investigation remains open.

**Completed controls:** four existing Matchms exports have positive nop/oracle pairs, preserved regression tests and clean oracle commands; all 40 task files are unchanged. These are completed controls, not new exports. [Results](https://github.com/Open-Athena/biotasks/blob/188091eb/experiments/29-runtime-limits/matchms-control-results.json).

**OpenMS:** the original 60-second checkout timed out again; the 300-second arm completed the same commit in 77.9 seconds with no tracked changes, using the same CPU/memory limits. This establishes acquisition recovery only. Bootstrap, PR discovery and task generation were not run. Both containers were removed and the archive verified. [Evidence](https://github.com/Open-Athena/biotasks/blob/875eab80/experiments/29-runtime-limits/openms-checkout-readback-001.json).

**Scanpy:** all 16 recorded bootstrap commands replayed with original exits and no repairs, crossing the saved Dockerfile's stop-at-first-failure barrier. Smoke/fresh-image checks remain false. The unchanged PR4389 export's nop/oracle controls are running at 300 versus 1,200 verifier seconds. Results remain pending. [Protocol](https://github.com/Open-Athena/biotasks/blob/65cfc8b5/experiments/29-runtime-limits/scanpy-controls-protocol.md).

**Remaining:** verify Scanpy controls and cleanup; collect the submitted OHIF recorded-action reconstruction, which restores original full-checkout copy behavior without command repairs; checkpoint MMseqs2's bootstrap comparison and model allowance. Longer verifier limits cannot resolve installation or checkout failures.

**Budget and retention:** nine terminal jobs used 1.18825 allocated CPU-hours. Active Scanpy controls reserve at most 9.6667 more and the submitted OHIF replay at most 8 more within the same 32-hour ceiling, on reserved capacity. Zero model calls. One Scanpy image remains for controls and will be removed after archive readback. Raw Matchms evidence remains private. No pipeline promoted. Detailed logs remain in comments.
