### Question

Can we develop a reusable prompt that lets LLM workers independently turn computational-biology notebooks into scientifically sound, runnable tasks? The research object is the worker prompt and its execution workflow; generated tasks provide evidence of how well it works.

### Prior work

Use [the source-inventory and task-authoring prompt study (#10)](https://github.com/Open-Athena/biotasks/issues/10) as a research-workflow reference: version prompts, run workers on fixed inputs, inspect artifacts and failures, revise the prompt, and compare subsequent runs. Its conclusions did not establish successful task authoring or select a supported prompt. Carry forward the experimental approach and its lessons about scientific fidelity, repeated comparisons and isolating changes.

### Current state — October 8, 2026

The research remains exploratory: no general notebook-to-task prompt has been selected or shown to transfer reliably. We have inspected source documents and published task pairs, run bounded authoring pilots, validated one manually reviewed and repaired variant natively, and completed two third-party solver attempts. These are separate kinds of evidence.

[Open the current explorer](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/8537099b995507afafb3b6bdf7df82d5e041861b/experiments/17-notebook2task/explorer/index.html) · [Refreshable research-branch link](https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/codex/research/17-notebook2task/experiments/17-notebook2task/explorer/index.html). Commit links identify tested artifacts; branch previews can be cached.

- **Approaches** opens first. Select SETA or BixBench, then click a workflow stage to see its explanation and relevant prompt. SETA includes three complete, hash-verified released prompt components, assembly notes and upstream attribution. BixBench's exact authoring prompt remains not located in the inspected public sources; its solver/evaluation prompts are not presented as authoring prompts.
- **Notebooks** lists 14 analyses with provenance filters, including the two released comparison examples. Each detail page separates **Notebook**, **Task** and **Attempt**. Task contains instructions, verifier, reference solution and creation/validation diagnostics. Attempt contains the model trace, submitted artifacts, native outcome and separate review annotations.
- Both retained solver traces use the bundled atif-lens viewer with search, expandable tool calls/results and syntax highlighting. Offline desktop/mobile checks passed for the attempt views and latest workflow navigation, including keyboard activation and saved selection. The limitations-annotation update initially had a browser-startup timeout; the subsequent stage-isolation update passed focused offline browser checks, including the limitations panel. Specification authoring combines both prompt components into one input; its selector changes only the reading view. Construction instructions appear only in step 03. Earlier SETA live HTMLPreview checks passed; the latest navigation check was offline.

### Baseline and authoring findings

Start v1 from SETA's unchanged released notebook adapter, shared idea prompt and task builder, pinned to `5868a1b5e6ae7528db5904ccb87ff245c2761651`. Keep staging and harness deviations explicit. [Prompt snapshots and protocol notes](https://github.com/Open-Athena/biotasks/blob/675cabd04c41832c80071ca74bf470f4de5d34cd/experiments/17-notebook2task/baselines/seta-v1/README.md). The earlier bespoke BioTasks prompt remains a separate candidate. AutoSDT's released adaptation/instruction prompts are a possible second baseline; no notebook adaptation has been validated. An equivalent BixBench authoring prompt and the specific LongDS authoring skill were not established in the inspected sources.

Bounded SETA-prompt trials exposed a domain mismatch: ASXL1/DESeq2 is rejected by the multiple-model gate. Cytopathology authoring encountered conflicting training requirements, output/context limits and incomplete packaging. These failures are outcomes, not evidence that the underlying biology cannot yield a task. GLM-5.3 runs through the existing service; no inference deployment or accelerator was provisioned. [Initial baseline evidence](https://github.com/Open-Athena/biotasks/blob/1194151a7fdfb10b451f00736529875874f88ad4/experiments/17-notebook2task/runs/20261006-seta-v1-pilot/README.md) · [Subsequent run records](https://github.com/Open-Athena/biotasks/tree/675cabd04c41832c80071ca74bf470f4de5d34cd/experiments/17-notebook2task/runs).

The CPU-training variant fixes the split, folds, model choices and grading contract. Its unchanged generated solution ran in 6.3 seconds on one CPU and matched an independent implementation to 2.22e-16 in OOF/test probabilities. After a recorded parent repair removing an unsupported correlation-count bound, all nine native tests and eight control expectations passed. The specification also received parent edits and the model needed continuations: this is not autonomous authoring success, faithful SETA reproduction or an isolated prompt-only comparison. Container/Harbor execution and independent solver evaluation of this generated variant remain untested. [Validation, failures and repair](https://github.com/Open-Athena/biotasks/blob/1dc9e8eea3fcc7c7bd4b4fc3717d4c84c3644909/experiments/17-notebook2task/validation/cpu-training-v1/README.md).

### Released-task solver results

One sequential Pi 0.87.0 / GLM-5.3 attempt per original released task used 128k context, 32k output, medium thinking and original one-hour agent limits. Generated tasks were excluded. No solver retries were launched; both Daytona sandboxes are removed.

| Example | Recorded outcome | Interpretation |
|---|---|---|
| SETA cytopathology | Native reward 1.0; all ten released tests passed; 12 saved messages and ten tool calls | Verifier pass, not an independent scientific audit |
| BixBench ASXL1 (`bix-1-q1`) | Agent timeout at 3,600 seconds, missing `answer.txt`, then verifier timeout at 600 seconds; 31 saved messages and 32 calls, one unfinished | Unscored; the final exception overwrote the earlier timeout, preserved in the diagnostic excerpts |

Proxy counters record ten SETA and 29 BixBench solver requests, with zero judge requests. The authorized allowance was at most one Together `openai/gpt-oss-120b` judge call without retries; none reached the proxy. BixBench's intermediate `0.0013` was not submitted or graded. [Retained outcomes and provenance](https://github.com/Open-Athena/biotasks/tree/675cabd04c41832c80071ca74bf470f4de5d34cd/experiments/17-notebook2task/attempts/20261007-pi-third-party/results).

### Scientific review and provenance limits

- SETA's report test checks length and keywords; it does not establish sound explanations. Its verifier also relies on solver-supplied labels and reported metrics. Proposed improvements combine trusted numerical checks with separately evaluated, advisory LLM report review; no new reward is claimed.
- SETA advertises specific modeling libraries and requires multiple classifiers plus an ensemble. Package-list steering is a hypothesis; task constraints directly limit the strategy. The precise generation-time Kaggle source version remains unresolved.
- BixBench uses expert-prepared capsules, then model-drafted and human-reviewed questions. Its ASXL1 capsule references an earlier study, but that study's original code format and any prior notebook lineage are unverified. Notebook access during authoring differs from solver inputs.
- BixBench's brief question omits analysis choices that affect its numerical answer. The capsule narrative, published question reference and attempt's intermediate result are not interchangeable. Their discrepancy remains unresolved. A justified deterministic numerical comparator is a proposed alternative, not the released grading contract.

### Agreed limitations of the pinned SETA notebook recipe

These findings concern the Kaggle adapter and shared idea-agent prompt at `5868a1b5e6ae7528db5904ccb87ff245c2761651`, not SETA as a whole.

- **Conflicting training instructions.** The Kaggle adapter requires multiple trained models; the shared idea-agent instructions prohibit model training. This is a confirmed inconsistency between prompt components. **Proposed change:** Make the permitted computation explicit and consistent across components.
- **Model-count gate.** The adapter rejects a notebook with only one trained model and expects two or more. Model count is a weak proxy for meaningful analytical decisions and restricts coverage of non-training workflows. **Proposed change:** Assess analytical decisions and verifiable outputs without a minimum model count.
- **EDA-only rejection.** The early-ditch examples treat EDA-only notebooks as lacking a clear objective. Exploratory analysis can still yield an assessable task; an actually undefined objective remains a valid reason to reject or refine it. **Proposed change:** Extract an analytical question and required evidence; verify calculations, reproducibility and support for conclusions.
- **Modality and keyword exclusions.** The initial gate rejects mentions of deep learning, neural networks, GPUs, transformers, images, audio or video. Such labels do not establish the resources needed for the task extracted from the notebook. **Proposed change:** Assess the proposed computation and dependencies directly, including CPU analysis of saved predictions, embeddings or images.

[Notebook adapter](https://github.com/camel-ai/seta/blob/5868a1b5e6ae7528db5904ccb87ff245c2761651/datasynth/seed2synth_pipeline/agents/seed2idea_prompts/kaggle_notebook_adapter.md) · [Shared instructions](https://github.com/camel-ai/seta/blob/5868a1b5e6ae7528db5904ccb87ff245c2761651/datasynth/seed2synth_pipeline/agents/seed2idea_prompts/idea_agent_base_prompt.md). Existing pilots record a multiple-model rejection and a training-instruction conflict; aggregate rejection rates and causal effects on generation quality remain unmeasured. These proposed revisions are not validated improvements. CPU/resource budgets remain deliberate execution constraints; local-data/browser restrictions are not classified as established limitations.

### Independent review and corrections

An independent agent reviewed explorer code, source/prompt provenance, authoring and solver evidence, scientific claims and issue reporting. All five actionable findings were addressed: the original SETA stream now has durable public retention; BixBench displays its full pilot submission instructions and pinned judge/launcher; its reference-answer record is separate; SETA annotations record the observed CV defect; and “All notebooks” returns to the directory. A second static review found no blocking regression; two stale labels it identified were corrected. Focused browser checks passed for both examples. No model calls, scientific reruns or reward changes were made.

**Confirmed SETA code finding:** supervised feature selection precedes downstream model/ensemble CV, and the k search uses a different feature-selection procedure from the final pruned feature set. The report’s fully nested claim is overstated. The magnitude of CV optimism is unmeasured; this finding alone does not invalidate the held-out test. Original reports and native grades are preserved.

All 17 small retained evidence files were anonymously downloaded from their immutable Git commit and matched the manifest’s sizes/hashes. Both original Pi streams match the displayed traces’ source hashes. Private runtime configuration and model transport records are excluded; this does not claim a complete raw-archive mirror. [Review and disposition](https://github.com/Open-Athena/biotasks/blob/675cabd04c41832c80071ca74bf470f4de5d34cd/experiments/17-notebook2task/reviews/20261008-independent.md) · [Retention verification](https://github.com/Open-Athena/biotasks/blob/675cabd04c41832c80071ca74bf470f4de5d34cd/experiments/17-notebook2task/reviews/20261008-retention-verification.json).

### Next steps and scope

1. Resolve source/version gaps and freeze a small development set plus reserved transfer examples; keep SETA/BixBench evaluation material outside training and transfer pools.
2. Make focused prompt changes addressing observed baseline failures, preserving matched inputs, settings and explicit budgets. Record human interventions separately.
3. Complete container validation and independent solver assessment for the generated variant before claiming acceptance; do not infer these from its native tests or the third-party solver pilot.
4. Test transfer on non-benchmark examples and report failure rates, scientific fidelity, grader robustness and cost. No reliable prompt recommendation is established yet.

Future model calls or compute remain subject to the agreed execution budget; listing a next step does not launch it. Prior use in a scientific-method benchmark alone is not an LLM-training exclusion. Keep large evidence in durable, versioned-manifest storage and retain research on the permanent branch.

### Issue maintenance

Keep this body as the current synthesis of the question, goals, findings, limitations, links and next steps. Use new comments as append-only iteration logs; preserve existing comments and add corrections in subsequent comments. Detailed decisions and executable evidence remain in the branch logbook and artifacts.

<details><summary>Experiment design and assessment</summary>

### Worker job

Each worker receives a notebook or analysis document selected with Gonzalo, its source context, the versioned notebook2task prompt, an isolated workspace, and a defined execution budget. It should complete the conversion without interactive human guidance:

- Retrieve real inputs, resolve dependencies and reproduce the relevant reference analysis. Report blocked inputs or failed execution explicitly; saved outputs or simulated execution are not reference-run evidence.
- Identify meaningful scientific objectives and decide which analytical decisions the solver must make. Produce language-agnostic objectives where appropriate, retaining necessary method/tool constraints.
- Build task packages containing instructions, staged inputs, environment, private reference evidence and graders. Keep solution-bearing notebook material out of the solver workspace.
- Execute checks and repair problems within its budget. Return artifacts, execution evidence, source-to-task lineage, unresolved scientific assumptions and a structured completion or failure report.

For the unchanged SETA baseline, stage and verify inputs before the authoring stages because its prompt assumes local data; account for that preparation separately and give matched prompt comparisons the same inputs. End-to-end retrieval by the worker is a separate workflow comparison.

Workers run independently in parallel across examples. The experiment needs a small batch runner and consistent outputs, rather than a human authoring each task in a chat. Independent validation determines acceptance; a worker's completion claim is not sufficient.

### Experiment

1. **Establish inputs and a baseline.** Select examples with Gonzalo from the familiar-repository shortlist, prior #10 inspections, or directly supplied analyses; do not substitute discovery rankings for source review. A suggested initial set is 4–6 analyses across biological workflows and Python/R where feasible. Reserve additional examples for testing transfer after prompt development. Start from the pinned SETA v1 prompts; freeze input staging, output contract, harness deviations and explicit run budget.
2. **Run a baseline batch.** Dispatch one isolated job per source using the same prompt and model settings. Save the exact prompt, source revision, model/reasoning settings, tool environment, budget, logs, artifacts and cost for each run. Keep blocked and failed jobs in the results.
3. **Review outputs independently.** Check scientific fidelity, instruction clarity and reproducibility. Test reference success, no-op failure, plausible scientific errors and valid alternative solutions where applicable. Use fresh solver attempts without the reference solution to expose ambiguity, leakage and grader exploits. Record limitations of automated review and scientific judgments needing further inspection.
4. **Revise the prompt from observed failures.** Group failures, form a concrete hypothesis for each proposed change, and version the revision. Prefer focused changes over bundles. Rerun the same examples with comparable settings and budgets; repeat promising comparisons to distinguish improvement from run-to-run variation. Log any manual rescue separately, and encode generalizable fixes in the prompt or tooling before rerunning fresh workers.
5. **Test transfer and conclude.** Run the selected candidate on reserved examples without further source-specific coaching. Report regressions, unresolved failures and the cost/quality tradeoff. If no revision reliably improves on the baseline, retain that result rather than declaring a winning prompt.

Human involvement is experiment design, supplying examples and reviewing evidence between batches. Each notebook2task job must stand on its own without a human steering its conversion.

### Outputs and assessment

- Versioned notebook2task prompts, a minimal parallel batch runner, reproducible run records and a logbook connecting revisions to hypotheses and evidence.
- Generated runnable task packages and independent validation results, including failed conversions and rejected tasks.
- An HTML explorer showing original notebooks, published notebook-derived tasks from comparison examples, our conversion recipes and generated tasks, with artifact links and explicit execution/validation status.
- Per-prompt results on matched sources: input retrieval, reference execution, task production, independent acceptance, scientific/grader defects, fresh-solver outcomes, manual intervention and cost. Count accepted source conversions and distinct tasks separately; more generated tasks alone is not an improvement.
- A documented prompt recommendation, or an inconclusive/negative result, with development-set and reserved-example performance reported separately.

Keep known LLM evaluation analyses/datasets out of the training candidate pool and record overlap checks and unresolved provenance. Prior use in a scientific methods benchmark (for example, single-cell integration) is provenance, not by itself an exclusion. Downstream SFT/RL benefit, scaling and comparisons with Skill2Env remain follow-up experiments.

</details>

<details><summary>Literature hypotheses</summary>

### Literature ideas to test in the prompt

The following are concrete starting points for prompt revisions, with distinct evidentiary limits:

- **SETA — extract the objective before building the task.** Its notebook adapter identifies objectives, approach and metrics, then proposes an exploratory task; environment construction is a separate stage. Start with these as explicit stages within the worker job, and test whether they improve scientific fidelity. The adapter assumes pre-downloaded data, so our worker must additionally retrieve and verify inputs. Do not copy its ML-specific filters or suggested train/test-gap checks as universal biological requirements. [v2, §3.1](https://arxiv.org/html/2607.10891v2#S3.SS1); [Kaggle adapter pinned at `5868a1b`](https://github.com/camel-ai/seta/blob/5868a1b5e6ae7528db5904ccb87ff245c2761651/datasynth/seed2synth_pipeline/agents/seed2idea_prompts/kaggle_notebook_adapter.md).
- **BixBench — derive questions from a completed biological analysis.** Experts assemble a hypothesis, data and reference notebook; an LLM drafts questions that experts review. Borrow the separation between reference analysis and solver-visible questions/inputs, and review whether answers follow from the analysis. This is an evaluation-construction precedent with expert involvement, not evidence that autonomous notebook conversion works. [Original v1, §§3.1–3.2](https://arxiv.org/html/2503.00096v1#S3).
- **LongDS-Bench — turn concrete examples into reusable authoring instructions.** Its authors manually convert three seed examples, derive an authoring skill, and use execution and review to validate further conversions. This motivates grounding prompt revisions in inspected examples and testing them on new notebooks. Our experiment tests autonomous workers; the paper's manual seed construction is not a requirement for a human to guide every job. Stateful follow-ups are a later extension. [v3, §§3.1–3.4](https://arxiv.org/html/2605.30434v3#S3).
- **AutoSDT — execute and repair, then assess scientific preservation separately.** Its scientific-program pipeline adapts dependencies and I/O, executes/repairs the program and derives instructions. Expert review still finds clarity and fidelity failures. Borrow the execution loop and separate fidelity assessment; this is a Python-program method, so transfer to notebooks remains to be tested. [v1, §§2–3](https://arxiv.org/html/2506.08140v1#S2).
- **ExeDS and Jupyter Agents — test task granularity and answer ambiguity.** ExeDS constructs execution-grounded cell tasks; Jupyter Agents generates questions and fresh traces, reporting trivial questions and preprocessing-dependent answer disagreements. Compare intermediate-result and whole-analysis objectives, preserve required context, and inspect disagreements instead of automatically treating the reference answer as correct. Do not inherit ExeDS's short-cell restrictions. [ExeDS, §§3–4](https://aclanthology.org/2022.dash-1.5.pdf#page=2); [Jupyter Agents, “Dataset Pipeline” and “Results”](https://huggingface.co/blog/jupyter-agent-2).

These sources motivate prompt hypotheses and validation checks. They do not establish that notebook-derived tasks outperform other training sources or improve biological model performance. Change and evaluate prompt components separately rather than bundling every idea into an assumed best design.

</details>
