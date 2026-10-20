# Three-task target tracker

Current admissions count independent validation, not raw exports. PR-diff admissions preserve patch-similarity semantics. Native language/profile exclusions and model/backend/input blockers remain explicit. Each seed recipe has a separate named cohort. The goal is not complete.

| Route / recipe | Biopython | scikit-bio | bedtools2 | DESeq2 |
| --- | --- | --- | --- | --- |
| pr_diff/native | 3/3 | 3/3 | 3/3 | 3/3 |
| pr_runtime/native | 3/3 | 3/3 | 0/3 (blocked) | 0/3 (blocked) |
| commit_runtime/native | 0/3 (cap reached) | 1/3 (cap reached) | 0/3 (blocked) | 0/3 (blocked) |
| code_instruct/native | 0/3 (capture unknown; cap consumed) | 0/3 (capture unknown; cap consumed) | unsupported | unsupported |
| equivalence_tests/native | 0/3 (blocked) | 0/3 (blocked) | unsupported | unsupported |
| cve_patches/native | 0/3 | 0/3 (blocked) | 0/3 (blocked) | 0/3 (blocked) |
| tasksmith/tasksmith | 0/3 (blocked) | 0/3 (blocked) | unsupported | unsupported |
| repo_mutate/swe_smith | 2/3 (cap reached) | 3/3 | unsupported | unsupported |
| pr_to_env/swe_gen | 0/3 (cap reached) | 0/3 | unsupported | unsupported |
| repo_reconstruct/swe_flow | 0/3 | 2/3 | unsupported | unsupported |
| equivalence_tests/r2e | 0/3 (cap reached) | 0/3 (cap reached) | unsupported | unsupported |
| pr_runtime/swe_next | 0/3 | 0/3 | unsupported | unsupported |
| commit_runtime/r2e_gym | 0/3 | 1/3 | unsupported | unsupported |
| env_repair/cli_gym | 0/3 (blocked) | 0/3 (blocked) | unsupported | unsupported |
| repo_reconstruct/codemidas | 0/3 (blocked) | 0/3 (blocked) | unsupported | unsupported |

| Seed route / recipe | Named input cohort | Independently admitted | State |
| --- | --- | --- | --- |
| terminal_synth/seta_seed2synth | seta-genomic-intervals-v1 | 0/3 | declared_input_pool_exhausted_below_target |
| task_evolve/seta_evol | pr2633-parent-v1 | 0/3 | target_not_met_work_remaining |
| terminal_synth/dataarc | pr2633-parent-v1 | 0/3 | target_not_met_work_remaining |
| terminal_synth/tmax | tmax-biological-v1 | 0/3 | declared_input_pool_exhausted_below_target |
| terminal_synth/endless_terminals | retained-native-draws-biological-context | 0/3 | candidate_cap_exhausted_below_target |
| terminal_reconstruct/terminalworld | bioinfo-notebook-v1 | 0/3 | blocked_eligible_input_or_terms |
| reasoning_synth/scaler | synthetic-DNA-edit-distance-family | 3/3 | target_met_for_declared_native_reward |
| optimization_synth/frontiersmith | unprepared-optimization-seeds | 0/3 | blocked_native_model_support |

The [CSV](target-tracker.csv) and [JSON](target-tracker.json) retain per-unit caps, shortfalls, source records and next actions. Unknown counts must be resolved before new dispatch. First-pass historical captures, retrospective aggregate N and billing limitations remain documented.
