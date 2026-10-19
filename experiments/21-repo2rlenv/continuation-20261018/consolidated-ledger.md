## Consolidated result ledger

First pass and continuation combined. Every accepted task below has independent validation; a scored attempt is separate from acceptance. Pending outcomes are not zero scores.

| Reward family | Accepted | Scored once | Maximum reward | Partial | Zero | Pending |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Correctness / algorithmic | 17 | 16 | 13 | 1 | 2 | 1 |
| Patch similarity | 12 | 12 | 1 | 3 | 8 | 0 |

### Repository-route ledger

Cells are **accepted tasks / charged candidate attempts**. The target is 3 accepted tasks per supported cell, with a cap of 10 candidates. `?` means the counter is not reconciled; `—` means unsupported native language/profile; `B` marks a model/backend/input blocker. Candidate definitions differ by recipe, so these are tracking counts rather than comparable production-yield estimates.

| Route | Biopython | scikit-bio | bedtools2 | DESeq2 |
| --- | ---: | ---: | ---: | ---: |
| pr_diff/native | 3 / 10 | 3 / 10 | 3 / 10 | 3 / 10 |
| pr_runtime/native | 3 / 9 | 3 / 5 | 0 / ? B | 0 / ? B |
| commit_runtime/native | 0 / 4 | 1 / 3 | 0 / ? B | 0 / ? B |
| code_instruct/native | 0 / 10 | 0 / 10 | — | — |
| equivalence_tests/native | 0 / ? B | 0 / ? B | — | — |
| cve_patches/native | 0 / ? | 0 / ? B | 0 / ? B | 0 / ? B |
| tasksmith/tasksmith | 0 / ? B | 0 / ? B | — | — |
| repo_mutate/swe_smith | 2 / 10 | 2 / 7 | — | — |
| pr_to_env/swe_gen | 0 / 1 | 0 / 1 | — | — |
| repo_reconstruct/swe_flow | 0 / 6 | 2 / 5 | — | — |
| equivalence_tests/r2e | 0 / 10 | 0 / 10 | — | — |
| pr_runtime/swe_next | 0 / 4 | 0 / 1 | — | — |
| commit_runtime/r2e_gym | 0 / 7 | 1 / 2 | — | — |
| env_repair/cli_gym | 0 / ? B | 0 / ? B | — | — |
| repo_reconstruct/codemidas | 0 / ? B | 0 / ? B | — | — |

### Seed-cohort ledger

| Recipe / fixed cohort | Accepted | Charged candidates | State |
| --- | ---: | ---: | --- |
| terminal_synth/seta_seed2synth / seta-genomic-intervals-v1 | 0/3 | 3/10 | target not met work remaining |
| task_evolve/seta_evol / pr2633-parent-v1 | 0/3 | 3/10 | target not met work remaining |
| terminal_synth/dataarc / pr2633-parent-v1 | 0/3 | 1/10 | target not met work remaining |
| terminal_synth/tmax / tmax-biological-v1 | 0/3 | 3/10 | target not met work remaining |
| terminal_synth/endless_terminals / retained-native-draws-biological-context | 0/3 | 10/10 | candidate cap exhausted below target |
| terminal_reconstruct/terminalworld / bioinfo-notebook-v1 | 0/3 | ?/10 | blocked eligible input or terms |
| reasoning_synth/scaler / synthetic-DNA-edit-distance-family | 3/3 | 3/10 | target met for declared native reward |
| optimization_synth/frontiersmith / unprepared-optimization-seeds | 0/3 | ?/10 | blocked native model support |

### Accepted-task score ledger

| Route | Repository / cohort | Task | Single-attempt GLM native reward |
| --- | --- | --- | ---: |
| pr_diff/native | biopython/biopython | biopython__biopython-5338 | 0 |
| pr_diff/native | biopython/biopython | biopython__biopython-5369 | 0 |
| pr_diff/native | biopython/biopython | biopython__biopython-5376 | 0 |
| pr_diff/native | scikit-bio/scikit-bio | scikit-bio__scikit-bio-2630 | 0 |
| pr_diff/native | scikit-bio/scikit-bio | scikit-bio__scikit-bio-2633 | 0 |
| pr_diff/native | scikit-bio/scikit-bio | scikit-bio__scikit-bio-2636 | 0 |
| pr_diff/native | arq5x/bedtools2 | arq5x__bedtools2-1030 | 0 |
| pr_diff/native | arq5x/bedtools2 | arq5x__bedtools2-1043 | 0.784762 |
| pr_diff/native | arq5x/bedtools2 | arq5x__bedtools2-999 | 0.380675 |
| pr_diff/native | thelovelab/DESeq2 | thelovelab__DESeq2-118 | 0 |
| pr_diff/native | thelovelab/DESeq2 | thelovelab__DESeq2-59 | 1 |
| pr_diff/native | thelovelab/DESeq2 | thelovelab__DESeq2-64 | 0.504236 |
| pr_runtime/native | scikit-bio/scikit-bio | PR2633 | 1 |
| repo_mutate/swe_smith | biopython/biopython | LCC constant mutation | 1 |
| repo_mutate/swe_smith | scikit-bio/scikit-bio | swe-smith-e3fc0018c5332295d4ab | 1 |
| repo_reconstruct/swe_flow | scikit-bio/scikit-bio | swe-flow-c80f6a9306c83c7db638 | 1 |
| commit_runtime/r2e_gym | scikit-bio/scikit-bio | r2e-gym-bf5a63ab005130388e02 | 0 |
| reasoning_synth/scaler | synthetic-DNA-edit-distance-family | scaler-2e50c70b17100648e7a1 | 1 |
| reasoning_synth/scaler | synthetic-DNA-edit-distance-family | scaler-5e341fa6b75229faea47 | 1 |
| reasoning_synth/scaler | synthetic-DNA-edit-distance-family | scaler-f41f832f3de994640a39 | 1 |
| pr_runtime/native | scikit-bio/scikit-bio | scikit-bio__scikit-bio-2630 | 1 |
| pr_runtime/native | scikit-bio/scikit-bio | scikit-bio__scikit-bio-2636 | 0 |
| pr_runtime/native | biopython/biopython | biopython__biopython-5317 | 1 |
| pr_runtime/native | biopython/biopython | biopython__biopython-5308 | 1 |
| pr_runtime/native | biopython/biopython | biopython__biopython-5316 | 1 |
| repo_reconstruct/swe_flow | scikit-bio/scikit-bio | swe-flow-3ad7ba60ca7686b2007b | 1 |
| repo_mutate/swe_smith | biopython/biopython | swe-smith-53ec5f51639d4053971f | 1 |
| commit_runtime/native | scikit-bio/scikit-bio | scikit-bio__scikit-bio-d25f305cea3a | 0.75 |
| repo_mutate/swe_smith | scikit-bio/scikit-bio | swe-smith-f39ded25ef48a6575366 | pending |

Patch-similarity rewards do not establish functional correctness. Scaler uses native −1/+1 rewards; the other scored correctness profiles use 0–1. No combined benchmark pass rate is claimed. Full stable identities and source hashes are preserved in `consolidated-ledger.json`.
