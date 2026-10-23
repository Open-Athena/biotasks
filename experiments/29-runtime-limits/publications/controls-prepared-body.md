Can timeout and scheduling changes recover complete positive control pairs without repairing tasks? Follow-up to #28.

**Prepared:** nine original exports, all 90 task files verified, and a controls-only runner with 20 commands: eight each for Matchms/OHIF and four Scanpy timeout comparisons. Harbor 0.6.6 supports the verifier-only 300→1,200-second override without editing task files. Commands have only been dry-run; no recovered tasks or live jobs are claimed.

**Reconstruction caveat:** syntax-clean saved recipes are insufficient. Scanpy's recipe retains a command that originally exited 1 with an externally-managed-environment pip error. The original images were deleted; any reconstruction drift or failure must be reported separately from timeout effects. No failed recipe command has been repaired or skipped.

**Next:** complete the bounded supervisor for unchanged reconstruction, controls, archival and owned-resource cleanup; prioritize Matchms/OHIF. Proposed first stage remains three serial reserved-CPU jobs, at most 32 allocated CPU-hours and zero model calls. OpenMS checkout and MMseqs2 bootstrap comparisons remain separate later arms.

**Boundaries:** immutable original tasks/baselines, no extra per-task LLM repair loop. Per-trial admission includes both internal verifier attempts, setup/teardown allowance and cleanup reserve; a wrapper timeout stops further trials until owned containers are removed. Protected Matchms packages remain private.

[Plan](https://github.com/Open-Athena/biotasks/blob/e6b740de0f665128925984a4a366d757bd602351/experiments/29-runtime-limits/plan.md) · [Original input verification](https://github.com/Open-Athena/biotasks/blob/e6b740de0f665128925984a4a366d757bd602351/experiments/29-runtime-limits/control-input-readback.json) · [Recipe/transcript evidence](https://github.com/Open-Athena/biotasks/blob/e6b740de0f665128925984a4a366d757bd602351/experiments/29-runtime-limits/recipe-history-results.json) · [Full scope](https://github.com/Open-Athena/biotasks/blob/e6b740de0f665128925984a4a366d757bd602351/experiments/29-runtime-limits/issue-scope.md). Detailed updates remain in comments.
