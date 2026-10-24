Build an unattended path from official Repo2RLEnv PR candidates to reproducible, independently controlled task bundles, preserving original grading without per-task human/LLM repairs.

**Current status:** the reusable validation component is implemented in [PR #46](https://github.com/Open-Athena/biotasks/pull/46), open and unmerged, with 41 offline tests and both GitHub checks passing. Controlled native comparisons reproduced the unchanged positive/clean Cobrapy reference and Scanpy’s prerequisite failure; all three workflows verified HF readback and owned cleanup. Main still exposes prompt inspection until this PR is reviewed. [Component evidence](https://github.com/Open-Athena/biotasks/blob/42be192b/experiments/44-validation-entrypoint/results.md).

**Next:** #45 investigates the remaining official generation/export-to-validation handoff. Source/interface preflight is complete: the unchanged exporter needs its expected cache layout. [Findings and the proposed single-reference protocol](https://github.com/Open-Athena/biotasks/issues/45#issuecomment-6384459268) are recorded; no fresh generation or model call is admitted. Full end-to-end generation/validation remains active. Recorded replay, broader portability, grader robustness and a Harbor upgrade are not established by the validation component.

**Coverage:** historical #28 counts remain 83 exports, 82 ever-positive and 67 ever-clean. Twenty-five exports are publicly eligible; 58 Matchms exports remain withheld. Follow-up controls are repeat attempts, not newly generated tasks.

**Budget:** 6.764819/32 additional allocated CPU-hours used, zero CPU reservations, new model calls or new paid capacity. Recorded paid cost $0; existing $10 archival reservation unreconciled. Operating ceiling $90, strictly below the $100 extra limit. Model execution remains disabled until a concrete priced/bounded generation protocol is checkpointed.

Keep #28 closed and this epic/children open for review. Logs and eligible append-only HF snapshots live in comments; retain research branches and protected evidence. No automatic PR merge.

