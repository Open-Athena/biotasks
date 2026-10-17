Assess which [Repo2RLEnv](https://github.com/huggingface/Repo2RLEnv) generation methods transfer to biological repositories, what competencies their tasks exercise, and whether the outputs can enter Marin's RL data curation pipeline. This is a broad, bounded exercise alongside custom notebook2task work: assess every available route and execute every applicable route on a small repository panel, preserving failures and unsupported combinations as findings.

Notebook2task targets scientific analysis workflows. This experiment explores complementary tasks in biological software repair, function reconstruction, library use, and terminal workflows. A task originating in a biological repository is not automatically a biological reasoning task; record the competency actually required.

## Repository panel

| Repository | Language/profile | Purpose |
| --- | --- | --- |
| [Biopython](https://github.com/biopython/biopython) | Python | Sequence algorithms and biological formats; Python recipe coverage. |
| [scikit-bio](https://github.com/scikit-bio/scikit-bio) | Python | Diversity and phylogenetic computations; a second Python repository helps distinguish recipe limitations from repository-specific failures. |
| [bedtools2](https://github.com/arq5x/bedtools2) | C++ and command-line tools | Genomic interval operations, compiled builds, and file-based verification. |
| [DESeq2](https://github.com/thelovelab/DESeq2) | R/Bioconductor with compiled components | Statistical biology, Bioconductor dependencies, and numerical reproducibility. |

These repositories occur in the [discovered inventory](https://github.com/Open-Athena/biotasks/blob/a342f41d9d0674cbe280a33a2f537285547552d3/experiments/5-classification-pilot/full-inventory/repository-counts.csv). Discovery does not establish execution readiness. Keep Scanpy with the initial notebook2task work to broaden this experiment's domain coverage.

Pin a source revision per repository for source-based recipes. Historical routes must additionally preserve each selected PR or commit's exact base/head revisions. Inspect source and fixture terms before redistribution, and record whether biological inputs are observed, adapted, or simulated.

## Coverage and baseline

Start from Repo2RLEnv revision `27d04ee8203cd5b2f20c3997d13836e5f5b64238`, inspected during planning, and record any deliberate upgrade before execution. Its documented catalog contains six native pipelines, Tasksmith, and sixteen experimental research recipes. Treat native pipelines and named recipe variants as distinct routes; planned but unimplemented methods are not executable routes.

The baseline is each applicable route without modifications to its generation logic, using an explicit repository profile where required. A fixed-budget setup or generation failure is a result. Record any later language adapter, model adapter, prompt change, or manual repair as a separate intervention rather than silently replacing the baseline.

| Route family | Exercise |
| --- | --- |
| Repository source, function, PR, and commit routes | Run against each supported panel repository using pinned source and bounded candidate selection. |
| Existing-task evolution, including SETA Evol and DataArc | Run after validated Harbor parent tasks exist; preserve parent/child lineage and keep variants distinct from independent source tasks. |
| Question/answer or terminal-recording routes | Prepare a small biologically grounded seed collection or recorded workflow with explicit provenance. |
| Security, reasoning-family, or optimization routes | Run only when suitable inputs exist within the panel's scope; otherwise record the missing input. |

Create a route-by-repository matrix for repository-based routes and a separate list of input cohorts for seed-based routes: fixed parent-task collections, question/answer collections, recordings, or problem families. Preserve each cohort's biological provenance without forcing it into a single repository cell. Distinguish applicable, unsupported language/profile, missing input, model/backend blocker, and unimplemented route. Do not count unsupported combinations as generation failures. In particular, Python-only recipes do not become C++ or R recipes by bypassing a language check. R bootstrap and test-report compatibility are open questions, not assumed capabilities.

## Models and execution budget

Use the existing GLM-5.3 service as the default for supported generation and review stages, with no paid-model fallback. Preflight authenticated endpoint access, structured outputs, token limits, and tool calls as required by each route. Discover the approved endpoint at launch and supply credentials through the protected runtime environment; keep private service details out of public artifacts.

Tasksmith currently requires an Anthropic author model. Record it as blocked on model support under the GLM-only baseline. Any adaptation to GLM is a separately recorded intervention. Do not assume that a configurable generation model also replaces every reviewer or solver model in a route.

The first pass targets three independently validated tasks per applicable route–repository combination, with a maximum of ten candidate attempts per combination. For seed-based routes, apply the same target and cap to each named input cohort: one fixed parent-task collection, seed collection, or problem family declared in the execution manifest. Stop when three tasks pass independent validation, ten candidate attempts have been used, or any execution budget limit is reached, whichever comes first. Retain zero-yield and partial-yield results without automatically extending the search.

Record candidate selection, what constitutes a candidate attempt for each route, and separate limits for model calls, input/output tokens, repair rounds, generated instances, and wall time before execution. Retries and repairs consume those limits rather than resetting them. Total the applicable combinations and seed cohorts before launch: for N execution units, the planned target is at most 3N validated tasks and the candidate ceiling is 10N attempts, subject to the aggregate budget. Include seed preparation in that budget and keep any subsequent expansion separate from this first pass. Three validated tasks demonstrate limited feasibility and expose obvious problems; they do not establish a reliable quality or yield estimate.

The agreed campaign ceiling is $1,000 for incremental remote CPU/sandbox execution, including failed runs and controllers. Permit up to four CPU sandboxes concurrently, initially 2 vCPU / 4 GiB RAM / 10 GiB disk each, with two-hour generation-run deadlines and no aggregate hour cap. Use existing free GLM only, at most four simultaneous model requests, no new GPU deployment or paid-model fallback, and no global call-count or token ceiling. Preserve recipe candidate and repair bounds. Explicitly adapted generation may use up to 131,072 combined reasoning-and-answer tokens, medium effort, and a 20-minute request timeout; keep original-limit failures as separate results. Dollar figures derived from list prices are planning estimates and reservations, not verified charges; account credit coverage remains unverified. Preserve artifacts and verify cleanup after each run. Build and biological execution belong on remote workers, not the shared small VM.

## Execution and validation

1. Inventory all routes and their source, language, model, backend, reward, and validation requirements. Establish the applicability matrix and bounded execution manifest.
2. Run the applicable repository-based routes. Preserve attempted candidates, skips, setup failures, rejected candidates, exported bundles, logs, and manual interventions.
3. Validate exported tasks independently of the generator's own checks using a declared acceptance profile for each reward type. For binary correctness tasks, require a passing reference, a failing baseline/no-op, rejection of meaningful incorrect submissions, and acceptance of valid alternatives. For graded correctness rewards, test full, partial, and incorrect outcomes against the native contract. For optimization tasks, check feasibility separately from reward, require reference improvement over the feasible baseline, and test no-op behavior, score repeatability, and sensitivity to solution quality; a valid solution need not earn a positive or maximal score. Check instruction–verifier agreement, scientific tolerances, determinism, and solver isolation from solutions and grading assets.
4. Exercise seed-dependent routes using accepted parent tasks or explicitly prepared inputs. Preserve lineage and avoid train/evaluation leakage across related tasks and variants.
5. Evaluate every independently validated task with one blind GLM solver attempt initially, using a 15-minute attempt deadline, 12 agent turns, and 2,048 output tokens per request. These solver limits remain unchanged by generation adaptations. Preserve solver traces and native rewards, and report infrastructure failures separately from scored attempts. Solver success is separate from task validity; solver failure alone is not evidence that a task is invalid.

Retain native rewards and their meaning. In particular, `pr_diff` measures patch similarity, not functional correctness. The native `equivalence_tests` route documents a learner-visible reference function; record that isolation limitation explicitly rather than treating generation success as acceptance. The separate R2E recipe uses a private verifier reference but still needs shortcut and isolation checks. Keep upstream generation checks, independent validation, and solver outcomes separate.

## Marin and RL Data Atlas compatibility

Use [Marin task curation](https://github.com/marin-community/marin/tree/main/experiments/post_training/task_curation) as the integration entry point. Atlas displays curation and curriculum records; a Harbor bundle or inventory entry does not establish runnable conversion or admission.

Pin the Marin checkout, converter implementation, execution runtime, and environment dependencies in the execution manifest; the `main` links here are navigation, not reproducibility pins. Try conversion early on one representative task from each distinct environment/verifier structure. Preserve the source environment, instructions, reference solution, private verifier, fixtures, native reward range and semantics, and provenance. Execute reward-specific controls through both the native and converted paths and compare rewards before claiming compatibility. Record unsupported build contexts, resource requirements, or verifier behavior explicitly.

Keep recipe cohorts distinguishable in source metadata and assessment outputs. Maintain stable task identities and parent lineage. Map curriculum coverage from the task's actual requirements, distinguishing biological reasoning from general software work. Inventory visibility, successful conversion, admission after controls, sampled quality judgments, and training readiness are separate outcomes.

## Comparison criteria and results

Report the funnel for each route and named input cohort: applicable inputs → attempted candidates → exported tasks → independently validated tasks → converted and execution-validated tasks. Break repository cohorts out by repository, and report seed-based cohorts with their parent or family lineage. Preserve missing and failed outcomes in their appropriate denominators.

Compare scientific relevance and distinct competencies, environment reproducibility, verifier quality and shortcut resistance, model usage, worker time, setup effort, manual interventions, and Marin compatibility. Do not rank methods by exported-task count alone, or generalize a small bounded sample into a reliable production yield estimate.

The final result should identify which methods merit expansion, which require explicit adaptations, which generate useful software tasks with little biological content, and which are unsuitable within the tested scope. Negative and inconclusive findings are valid conclusions; there is no requirement that every route produce an accepted task.

Preserve executable inputs and run evidence on a permanent research branch from a recorded BioTasks `main` commit, with a branch-local logbook and immutable artifact references. The issue should summarize conclusions and link decisive evidence. Promotion of reusable tooling is separate from this experiment.

## References

- [Repo2RLEnv pipeline comparison](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/docs/choose-a-pipeline.mdx)
- [Research recipe mapping and execution contracts](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/docs/pipelines/owned_recipes.md)
- [Tasksmith model constraints](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/src/repo2rlenv/tasksmith/models.py)
- [FrontierSmith optimization reward and controls](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/docs/pipelines/frontiersmith.md)
- [Marin dataset declarations](https://github.com/marin-community/marin/blob/main/experiments/post_training/task_curation/datasets/README.md)
- [RL Data Atlas semantics](https://github.com/marin-community/marin/blob/main/docs/references/rl-data-atlas.md)

