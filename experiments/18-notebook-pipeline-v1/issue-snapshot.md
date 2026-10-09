# Build and evaluate notebook-to-task pipeline v1 on ten diverse biology notebooks

Build a first reproducible pipeline for converting computational-biology notebooks into executable, deterministically graded tasks in native Harbor format. Exercise it on an initial proposal of ten seed notebooks spanning different biological domains, and make the full notebook → task → attempt workflow inspectable.

Use GLM-5.3 through ZCode, its official harness, as the LLM worker in a versioned task-generation pipeline driven by prompts and a seed notebook. For each accepted task, run one fresh GLM-5.3 solver attempt using Pi through Harbor and preserve its trajectory, submitted artifacts, deterministic grade and resource measurements.

## Seed notebooks

Start from the following ten proposed notebook/literate-analysis seeds, each pinned to a source revision. The panel includes Scanpy and bedtools and spans distinct scientific objectives, modalities and operations. Eight sources come from the [inventory in #16](https://github.com/Open-Athena/biotasks/issues/16); the Harvard bedtools and scikit-bio IL6 notebooks are additional discoveries. This is a deliberately selected development panel, not a random sample or a claim of representative domain coverage. R Markdown vignettes count as literate-analysis seeds alongside Jupyter notebooks.

Select one compact scientific question from each seed for the **five-minute solver limit**. The directions below guide authoring; they are not finalized task instructions. The worker receives the seed and authoring prompt; the solver receives only the resulting task and permitted inputs.

| Domain | Pinned seed | Compact task direction | Inputs and preparation |
| --- | --- | --- | --- |
| Transcriptomics | [Scanpy: PBMC3k clustering tutorial](https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering-2017.ipynb) | QC, cell/gene filtering and normalization; omit the full clustering and marker-discovery workflow. | 10x PBMC3k count matrix and feature/barcode files; stage before solving. |
| Genomic intervals | [Harvard Bioinformatics Coffee Hour: bedtools](https://github.com/harvardinformatics/bioinformatics-coffee-hour/blob/17531934f410d6afe654c33c3ced192b1a01c5c2/bedtools/index.ipynb) | Identify chr22 enhancers overlapping strand-aware upstream gene intervals, with an explicit duplicate/overlap contract. | Repository BED files and hg38.genome: about 276 KB total. Check genome-build consistency and source attribution. |
| Epigenomics | [methylKit user guide](https://github.com/al2na/methylKit/blob/32212a6cc2046e97371eb528533964c1e1a54afa/vignettes/methylKit.Rmd) | Coverage filtering, joining CpG sites across four samples and comparing group methylation; use the bundled count-table section, not alignment or segmentation. | test1/test2/control1/control2.myCpG.txt; four files total about 374 KB. |
| Proteomics | [QFeatures: processing quantitative proteomics data](https://github.com/rformassspectrometry/QFeatures/blob/c4b3bb93ec0b824a52d2f20ea05d5b15a26d7c52/vignettes/Processing.Rmd) | Filter contaminants/missing values and aggregate a prepared peptide assay to proteins, using a specified aggregation contract. | CPTAC study 6 A/B peptide table from MsDataHub; six quantitative sample columns. Stage a documented subset if needed. |
| Structural biology | [MDAnalysis: RMSD of atomic structures](https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb) | Backbone alignment and CORE/LID/NMP domain RMSD summaries for the supplied adenylate-kinase trajectory. | MDAnalysisTests PSF/DCD inputs; stage a fixed frame subset if needed. No new molecular-dynamics simulation. |
| Metabolomics | [xcms: LC-MS preprocessing and analysis](https://github.com/sneumann/xcms/blob/088a3c1494331241bbe0910551954356a43b0288/vignettes/xcms.Rmd) | The final PCA section: missing-feature handling, log transformation and sample structure in a prepared feature-intensity table. | Derived feature table plus sample metadata from the vignette's eight faahKO samples; upstream preprocessing belongs to input preparation, not the solver attempt. |
| Systems biology | [COBRApy: simulating with FBA](https://github.com/opencobra/cobrapy/blob/6f83a534569557f6a10bfdf6909522016985e47f/documentation_builder/simulating.ipynb) | Compare biomass and ATP-maintenance objectives in the E. coli core model; grade objectives/feasibility rather than requiring one unique flux vector. | Local copy of the textbook model and a CPU solver; avoid broad flux sampling or expensive loopless analysis. |
| Microbiome science | [phyloseq: microbiome census analysis](https://github.com/joey711/phyloseq/blob/8a6c2350b985afb909428d396081605e9b3e2f0b/vignettes/phyloseq-analysis.Rmd) | Per-sample richness and Shannon diversity from GlobalPatterns, joined correctly to sample metadata; avoid full ordination and plotting workflow. | Bundled GlobalPatterns count table and sample metadata. |
| Evolutionary biology | [scikit-bio: basic bioinformatics (IL6)](https://github.com/scikit-bio/scikit-bio-tutorials/blob/3b41d72a4114a3761bdc97dfe5a793c074426062/01-basic-bioinfo/01-basic-bioinfo.ipynb) | Pairwise evolutionary distances or neighbor-joining topology from a prepared IL6 protein alignment of seven species; omit visualization and full alignment construction. | Pinned il6.ffn and a reference-prepared alignment; record translation/alignment provenance. Verify APIs against the pinned environment. |
| Bioimage analysis | [PyRadiomics: two brain-image examples](https://github.com/AIM-Harvard/pyradiomics/blob/8ed579383b44806651c463d5e691f3b2b57522ab/notebooks/RadiomicsExample.ipynb) | Compare a fixed set of original-image first-order and shape descriptors within supplied tumor masks. | brain1/brain2 images and masks from getTestCase, staged offline; fixed feature settings. No segmentation or broad filter-bank extraction. |

**Inspection status:** All ten source documents were fetched and their relevant code inspected. The eight inventory files matched their recorded SHA-256 hashes. The source-inspection manifest, hashes and selection notes are preserved in the collapsed appendix below; copy them into the research artifacts when implementation begins. No notebook, generated task or solver attempt has been executed for this panel. Runtime, offline completeness, scientific grading and redistribution eligibility remain to be validated; the five-minute fit is a selection hypothesis.

Preserve source revisions, input versions/hashes, terms and benchmark overlap before execution. Confirm the original lineage of the methylKit example counts before describing them as observed. MDAnalysis uses a supplied simulation trajectory, COBRApy uses a curated mechanistic model, and the xcms and scikit-bio tasks use explicitly derived inputs. Review supplied masks, sample labels and biological assumptions rather than treating the tutorial narrative as independent validation.

Allow documented substitutions when inspection or execution reveals a fundamental suitability issue, such as unavailable inputs, incompatible licensing, irreparable source code, or no meaningful task that fits the resource budget. Preserve domain coverage where practical. Record the original seed, evidence for the issue, replacement and rationale; pin the replacement source revision and preserve any generation or solver attempts already performed. Distinguish initial-panel outcomes from replacement outcomes. Do not replace seeds merely to increase GLM success: a solver failure or five-minute timeout alone is insufficient reason.

Prepare any derived inputs through reproducible, recorded steps and keep their reference outputs outside solver-visible files.

## Pipeline v1

Start with the simplest useful pipeline and one task candidate per seed. Use GLM-5.3 for its LLM stages. The number and arrangement of LLM stages are design choices, not fixed requirements: the pipeline may use separate calls to propose a scientific objective, specify the task, build the Harbor package, review it statically, and repair defects. Combine or split stages as useful; generation need not be a single call. Keep the overall execution and repair budgets bounded, and record each stage's prompt, inputs, outputs and model settings.

For optional inspiration, see the SETA authoring and builder prompts inspected in [issue #17](https://github.com/Open-Athena/biotasks/issues/17) and its [preserved prompt snapshots](https://github.com/Open-Athena/biotasks/tree/9819917efaf925d51e10f06e19ef056cd964c91c/experiments/17-notebook2task/baselines/seta-v1). These are references, not a required starting implementation or prescribed architecture. Start simply and add stages when they address a concrete need.

The pipeline must cover the following activities, which need not map one-to-one to LLM calls:

1. Identify a self-contained scientific objective grounded in the notebook.
2. Assemble a native Harbor task package with task instructions, configuration, solver-visible inputs and a reproducible environment.
3. Construct a reference solution and deterministic grader, kept separate from solver-visible assets.
4. Validate reference success, rejection of empty and meaningfully incorrect submissions, and compliance with resource limits.
5. Run a bounded repair cycle when needed, preserving failed attempts and recording human interventions.
6. Freeze the accepted Harbor task package and run one GLM-5.3 solver attempt using Pi through Harbor on Daytona in a fresh environment and conversation. Give the solver only the task instructions and permitted inputs, without the seed notebook, authoring conversation, reference solution or hidden grader assets. Preserve the attempt before sandbox teardown.

The task should preserve meaningful biological analysis rather than merely reproduce notebook outputs. Any input reduction or adaptation must document its effect on the scientific objective. Reference success alone is insufficient: review the task’s scientific assumptions and whether the grader accepts valid alternative solutions.

LLM-based static review can guide construction and repair, but does not replace executable reference/verifier validation or supply the reward. The five-minute limit applies to the separate solver attempt, not to the number of authoring stages.

Demonstrate at least one successful end-to-end GLM-5.3 solve within the five-minute budget. Report outcomes for every accepted task; individual task acceptance depends on scientific validity and reference/verifier validation, not GLM success. Distinguish task defects requiring repair, infrastructure failures, and valid solver failures, including timeouts. Do not simplify a scientifically sound task solely to obtain a passing GLM attempt.

Any revisions prompted by solver failures create a new task version and preserve the original attempt. The baseline remains one attempt per initially accepted task. Set an explicit finite budget for additional attempts after repairs before running them; report these separately rather than replacing baseline outcomes. If no successful solve is obtained within the budget, record that the end-to-end success goal remains unmet and investigate the failure modes without automatically extending the run.

## Scientific specification and implementation freedom

Task statements focus on the biological question and specify the inputs, methodological assumptions, required analysis and output contract precisely enough to establish correctness. Make consequential choices explicit, including filtering criteria, normalization, statistical models, reference genomes and missing-data handling where relevant. Leave programming language, package choice and code structure open within the prepared environment. The software named in the seed panel identifies the source workflow, not a solver requirement.

Use the seed's native ecosystem for the reference implementation and default dependencies. V1 does not require equivalent reference implementations or equally complete toolsets in both Python and R for every task. Grade scientific outputs and properties with justified tolerances, accepting valid alternative implementations rather than checking package imports or exact commands. If a software-specific behavior is necessary to define correctness, document and justify that exception explicitly.

Keep solver-facing environment guidance neutral: “Internet access is disabled. Inspect the environment for available software; required dependencies are installed.” Do not highlight a preferred package or provide a recommended software recipe in the task statement. Prefer a few reusable environment profiles with consistent packages across related tasks where practical, rather than narrowly tailoring installed tools to reveal the intended solution. Record the full package/version manifest with the experiment. Installed tools remain discoverable and can influence solver behavior; report results as performance within the recorded environment, without claiming implementation-neutral performance.

## Harbor task format and execution

The pipeline's output contract is a native Harbor task package, including `instruction.md`, `task.toml`, the environment definition and permitted inputs, a reference solution, and deterministic verifier assets. Pin the Harbor repository revision and agent integration used for validation and solving. Encode the agreed resources, 300-second solver timeout and network restrictions in the task/run configuration supported by that revision, and verify their effective enforcement.

Validate package loading, reference execution and grading through Harbor, including meaningful incorrect submissions. Keep reference and verifier assets outside the solver environment and use separate verifier execution. Preserve Harbor trial results, trajectories, submitted artifacts and verifier logs, and use these records to populate the explorer's Task and Attempt views.

## Deterministic partial-credit scoring

Report a partial-credit reward in [0, 1] and a separate full-task success flag. Start with two to four binary scientific subgoals per task, with positive weights summing to one. The reward is the weighted sum of satisfied subgoals; full-task success requires every required subgoal to pass. The goal of at least one successful GLM-5.3 solve requires full-task success, not merely positive partial credit.

Define subgoals, weights, dependency rules and justified numerical tolerances before solver attempts. Score meaningful scientific deliverables rather than the raw number of tests; multiple implementation or format checks may support one subgoal. Keep the task a coherent scientific question with connected deliverables, and grade submitted artifacts while accepting valid alternative workflows. Use tolerance-based correctness for numerical results rather than smooth rewards for numerical closeness in v1.

Make dependencies explicit: downstream credit must check required input identities and upstream validity where they affect scientific correctness. Avoid accidental repeated penalties for the same error; where useful, report correct computation on a submitted intermediate separately from correctness of the final biological result. Validate the scoring contract with fully correct, partially correct and meaningfully incorrect submissions, including missing artifacts and violated dependencies.

At the solver timeout, stop solver activity and preserve available artifacts for grading within the separate verifier budget. An incomplete attempt can receive partial credit for valid artifacts. Infrastructure failures remain ungraded rather than becoming zero-reward examples; report grading failures separately from an ordinary timeout or incorrect submission.

## Resources and execution budget

Use the selected per-sandbox resource ceiling, based on the Marin Daytona profile discussed for this experiment; confirm backend support before execution:

- **4 vCPU**
- **8 GiB RAM**
- **10 GiB disk**
- **No GPU**

Authoring execution, reference validation and solver execution must fit this CPU-only profile. Hosted GLM-5.3 inference is separate from the task sandbox; no task may delegate biological computation to external compute services. Assess requirements from the selected analysis rather than excluding whole biological domains. Record over-budget cases explicitly.

**Solver time limit: 300 seconds per GLM-5.3 attempt**, starting when the prepared environment is handed to the solver and including model calls and tool execution. Environment construction, input staging and grading are outside this clock and measured separately. Preserve timed-out attempts without automatic solver retries. Select compact scientific questions that leave time for input inspection, coding and error recovery. This is a solver limit, not an authoring or reference-execution limit.

Before execution, pin ZCode and Pi versions/configurations, GLM-5.3 settings, token/spend budget, repair limit, concurrency, and remaining stage budgets. Record generation, environment setup, reference validation and solver execution separately. Verify the configured sandbox allocations at launch.

## Internet access and environment preparation

Allow internet during task authoring and environment construction to retrieve source material, data and dependencies, preserving versions and hashes. Preinstall required software, including agent-launcher and verifier dependencies, and supply fixed biological inputs and relevant versioned documentation. If additional package installation is needed during solving, provide a prepared local package cache.

Disable external network access during solver attempts, reference validation and deterministic grading. Verify the restriction in the actual execution backend and record the effective network configuration. Provide the Pi agent access to hosted GLM-5.3 inference while denying task commands general internet access. Verify the separation in the chosen Harbor/Pi integration; an installed agent must not be assumed to support a fully network-disabled sandbox without additional inference routing. Disabling browser tools or requesting offline behavior in the prompt is insufficient.

Inspect solver images and inputs for accidentally included seed notebooks, solutions, reference outputs or hidden grading assets, including package examples and caches. Run grading in a separate environment. Missing dependencies and network-related infrastructure failures must remain distinct from scientific failures.

Reuse prepared images or snapshots where practical. Record image size and cold/warm startup time separately from sandbox disk usage. Confirm which storage the backend charges against the 10 GiB allocation, then measure peak usage under that accounting, including inputs, temporary files and outputs.

## Measurements and visualization

Record, per seed and pipeline version:

- Generation and validation outcomes, including failure reasons.
- Generation and solver tokens, cost where available, and elapsed time by stage.
- Reference execution time, peak memory and input/environment sizes.
- Environment profile and complete package/version manifest for each attempt.
- Solver execution time, peak memory, submitted artifacts, per-subgoal outcomes, weighted partial-credit reward, full-task success flag and infrastructure failures.
- Repair attempts and human interventions.
- Task acceptance and rejection decisions.

Reuse the [explorer from #17](https://github.com/Open-Athena/biotasks/issues/17) to browse each notebook, generated task, reference/verifier evidence, authoring and repair records, and the GLM-5.3 solver attempt. Show unrun, failed, ungraded and graded attempts distinctly, with subgoal scores and full-task success visible separately. Reference runtime and solver runtime are separate measurements.

## Completion criteria

- A versioned pipeline and reproducible configuration exist on a new permanent research branch based on recorded `main`.
- All ten initial seeds and any replacements have a recorded disposition, including unsuccessful conversions and documented substitution reasons.
- Accepted tasks load in the pinned Harbor runtime and pass reference and grader validation through Harbor, including partial-credit controls and dependency checks, with limitations documented.
- Solver and grading environments run with verified external network restrictions and all required dependencies available locally.
- Each accepted task has a recorded baseline GLM-5.3 solver attempt, including unsuccessful or infrastructure-failed attempts. Any budgeted post-repair attempts are linked to their task versions and reported separately. Solver success is not required for individual task acceptance.
- At least one accepted task has a successful end-to-end GLM-5.3 solve within the five-minute solver budget.
- The explorer exposes the source-to-task lineage, attempts, validation evidence and resource measurements.
- A report summarizes generation yield, solver outcomes, costs, failure modes and limitations.

All initial seeds and replacements must be accounted for; ten accepted tasks are not required. Substitutions must stay within the recorded execution budget. Failed or incomplete attempts remain visible and are not silently retried or converted into scientific outcomes.

## Design decisions and alternatives considered

This record summarizes the scoping discussion and its rationale. These are design choices for v1, not experimental findings.

- **Scope: build and exercise a pipeline.** The initial discussion included benchmark-performance correlations and runtime as ways to assess generated tasks. The selected scope is a working generator, native validation, GLM-5.3 attempts and inspectable resource/outcome records. A multi-model benchmark comparison is outside this issue. Deferring all solver runs was also considered; retaining a bounded GLM attempt makes the complete workflow concrete.

- **Seeds: breadth with familiar anchors.** Ten seeds keep the first iteration manageable. Scanpy and bedtools are the chosen familiar anchors; including both Scanpy and DESeq2 was rejected to avoid spending two slots on transcriptomics. The inventory in #16 supplies domain guidance and most sources. Although random sampling was discussed initially, the proposed panel was selected deliberately for domain breadth and plausible resource fit; it should not be described as a representative random sample.

- **Formats: both Jupyter and R Markdown.** The current proposal includes six `.ipynb` files and four `.Rmd` vignettes. Five Jupyter sources use Python and the bedtools source uses shell commands. Restricting intake to Python/Jupyter would exclude useful R analyses. The generated deliverable is a Harbor task, not necessarily a notebook.

- **Panel changes: permit justified substitutions.** A permanently frozen panel would make fundamental source problems unnecessarily blocking. Substitutions are allowed for evidenced suitability problems while preserving original records and domain coverage where practical. Replacement merely because GLM fails would bias the results toward easy tasks and is not allowed.

- **Pipeline architecture: simple, but not necessarily one-shot.** A proposal/specification stage, Harbor builder, static reviewer and repair stage are possible arrangements, not mandatory components. Start with the simplest useful structure and add stages for concrete needs. SETA's prompts and builder workflow from #17 are optional inspiration; copying that recipe or adopting its restrictions is not required. Static LLM review is advisory and cannot supply the reward.

- **Model and task interface: GLM-5.3 and native Harbor.** Fix GLM-5.3 for authoring and solving to keep this iteration interpretable. Use separate authoring and solving contexts so the solver does not inherit solutions. Harbor packages and Harbor execution provide the common task, validation and attempt interface; pin the runtime and agent integration.

- **Harnesses: ZCode for authoring; Pi for solving.** Use [ZCode](https://zcode.z.ai/en), the official GLM-5.3 harness, for authoring. Use [Pi](https://github.com/earendil-works/pi/tree/main/packages/coding-agent) through Harbor for solver attempts, choosing a general harness that can remain fixed in future evaluations across models. This is an implementation choice, not a claim that Pi outperforms Terminus-2. Terminus-2 was considered for its Marin and synthetic-trajectory precedent; other alternatives included OpenCode, Claude Code/Agent SDK and a custom tool loop. Before execution, verify unattended ZCode operation with the selected GLM endpoint, stage artifact/trace capture, and Pi inference routing under the offline task policy. Pin prompts, tools, model settings and harness versions; do not silently substitute harnesses if integration is blocked. Multi-model evaluation remains outside this issue.

- **Resources and time: optimize for short iterations.** Use the agreed 4-vCPU, 8-GiB RAM, 10-GiB disk profile with no task GPU. Longer solver limits were proposed during discussion; the selected limit is five minutes. This is specifically the solver's wall-time budget, including model calls and tool execution; proposed authoring/reference time limits were not adopted. Setup and grading are measured separately. Select a compact scientific question from each notebook rather than requiring full-notebook reproduction. Five-minute suitability remains untested until execution, and timeout alone does not invalidate a task.

- **Network: construction online, solving and grading offline.** Open internet for package installation and documentation lookup was initially proposed, following Terminal-Bench's evaluation setting. Concern about rewarding solution retrieval during repeated training motivated the offline starting policy. Terminal-Bench later documented actual solution retrieval and introduced [reward-hacking enforcement](https://www.tbench.ai/news/leaderboard-integrity-update); [TB3 remained open-internet](https://www.tbench.ai/news/terminal-bench-3-0). That evaluation policy does not settle the appropriate training-environment design here. Offline execution also reduces dependence on changing external services, but narrows the task to analysis with supplied inputs and tools. Verify backend enforcement rather than relying only on task settings.

- **Dependency preparation: accept image costs to avoid repeated setup.** Preinstallation can increase image size and cold-start transfer time, while avoiding repeated downloads, compilation and dependency resolution during attempts. Shared environment profiles and snapshots are preferred where useful; their benefit and disk fit must be measured. A prepared local package cache can support additional installation without general internet. Supporting precedents include [SkillGym's no-runtime-network selection](https://arxiv.org/html/2609.37539v1#S3.SS1), [SETA's documented egress-blocked RL configuration and verifier-dependency warning](https://github.com/camel-ai/seta/blob/5868a1b5e6ae7528db5904ccb87ff245c2761651/scripts/miles/examples/qwen3_8_27b_grpo/README.md), and [Nemotron-Terminal's shared prebuilt images](https://arxiv.org/html/2602.21193v1#S4.SS2.SSS3). These establish different precedents, not a universal network policy. Offline images can still leak solutions through bundled examples or caches, so source/reference separation remains necessary.

- **GLM success: demonstrate the workflow without selecting only easy tasks.** Requiring success on every task could encourage oversimplification. Instead, require at least one full successful solve, while accepting individually sound tasks that GLM fails. Separate task defects, infrastructure failures and valid solver failures. Repairs create new versions; bounded additional attempts are reported separately. Exhausting the budget without a full success leaves that goal unmet rather than authorizing unlimited retries.

- **Reward: partial credit plus full-task success.** Pure all-or-nothing reward hides useful progress in short attempts. Raw test-pass fractions can overweight incidental format checks. Start with two to four binary scientific subgoals and predetermined weights; report both their weighted score and an all-pass flag. Smooth numerical-closeness rewards are not needed for v1. Specify dependencies to avoid rewarding invalid downstream results or accidentally penalizing the same error repeatedly. Grade available timeout artifacts, but keep infrastructure failures ungraded. Multiple deliverables should form one coherent biological task, not a collection of unrelated questions.

- **Scientific methods versus software: constrain the former.** Specify enough methodological context to determine correctness while allowing Python, R, different packages or custom code within the environment. The seed provides a reference implementation, not a required software recipe. Equivalent implementations in multiple languages are not required for v1. Package-specific exceptions need a scientific justification; graders should otherwise check outputs and properties rather than imports or commands.

- **Tool availability can influence choices.** Listing preferred packages in the task statement could steer the solver toward the reference workflow. Use neutral environment guidance and let the solver inspect available software. Prefer consistent reusable profiles over highly revealing task-specific environments, and preserve package manifests. This reduces prompting cues without claiming to eliminate environmental bias or making dependency reconstruction the task.

- **Inspection and research record.** Reuse #17's Notebook → Task → Attempt explorer, extending it with versioned stages, partial credit, failures and resource measurements. Keep work on a new permanent research branch with reproducible inputs and evidence. Source inspection, native execution, solver outcomes and publication are distinct states; the selected notebooks have only been source-inspected so far.

### Details to settle before execution

Pin the Harbor revision, ZCode authoring configuration and Pi solver integration; verify unattended authoring, trace capture and offline solver networking; choose GLM-5.3 context/output and sampling settings; set finite authoring, repair, post-repair attempt and total execution budgets; select concurrency and setup/verifier timeouts; finalize environment profiles, backend disk accounting, input provenance/terms and derived-input preparation; and define each task's subgoals, weights, tolerances and dependency rules. None of these open details changes the agreed five-minute solver limit or authorizes execution merely by filing this issue.

<details>
<summary>Source-inspection manifest and selection notes</summary>

```json
{
  "status": "proposed_seed_panel_source_inspected_not_executed",
  "solver_limit_seconds": 300,
  "selection": "Purposive domain-diverse v1 panel; not a random sample. Eight inventory entries plus two additional sources.",
  "seeds": [
    {
      "label": "Scanpy: PBMC3k clustering tutorial",
      "domain": "Transcriptomics",
      "url": "https://github.com/scverse/scanpy/blob/8c1463d5d97272d5811ad3f4efb57483e23b4c7e/docs/tutorials/basics/clustering-2017.ipynb",
      "revision": "8c1463d5d97272d5811ad3f4efb57483e23b4c7e",
      "path": "docs/tutorials/basics/clustering-2017.ipynb",
      "source_sha256": "1d4e8b1cb3ef8423bb1c4bb6ad6228e4c54b2352b5d9e7f142619737e189f439",
      "inventory_document_key": "github:scverse/scanpy:docs/tutorials/basics/clustering-2017.ipynb",
      "focus": "QC, cell/gene filtering and normalization; omit the full clustering and marker-discovery workflow.",
      "inputs": "10x PBMC3k count matrix and feature/barcode files; stage before solving.",
      "input_origin": "Observed single-cell measurements.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "Harvard Bioinformatics Coffee Hour: bedtools",
      "domain": "Genomic intervals",
      "url": "https://github.com/harvardinformatics/bioinformatics-coffee-hour/blob/17531934f410d6afe654c33c3ced192b1a01c5c2/bedtools/index.ipynb",
      "revision": "17531934f410d6afe654c33c3ced192b1a01c5c2",
      "path": "bedtools/index.ipynb",
      "source_sha256": "ca3f9ab07c5132e346a5e048fcf4067b591b953bf1f655fd49c30f39f4a28c7d",
      "inventory_document_key": null,
      "focus": "Identify chr22 enhancers overlapping strand-aware upstream gene intervals, with an explicit duplicate/overlap contract.",
      "inputs": "Repository BED files and hg38.genome: about 276 KB total. Check genome-build consistency and source attribution.",
      "input_origin": "Published enhancer/peak examples and curated gene annotations; original dataset lineage still needs checking.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "methylKit user guide",
      "domain": "Epigenomics",
      "url": "https://github.com/al2na/methylKit/blob/32212a6cc2046e97371eb528533964c1e1a54afa/vignettes/methylKit.Rmd",
      "revision": "32212a6cc2046e97371eb528533964c1e1a54afa",
      "path": "vignettes/methylKit.Rmd",
      "source_sha256": "1bc3018553cac949c6156dd33489b273946e13ed701062aeed83f26fa113ef63",
      "inventory_document_key": "github:al2na/methylkit:vignettes/methylKit.Rmd",
      "focus": "Coverage filtering, joining CpG sites across four samples and comparing group methylation; use the bundled count-table section, not alignment or segmentation.",
      "inputs": "test1/test2/control1/control2.myCpG.txt; four files total about 374 KB.",
      "input_origin": "Bundled example counts; observed versus simulated origin unresolved. Do not label as observed without further evidence.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "QFeatures: processing quantitative proteomics data",
      "domain": "Proteomics",
      "url": "https://github.com/rformassspectrometry/QFeatures/blob/c4b3bb93ec0b824a52d2f20ea05d5b15a26d7c52/vignettes/Processing.Rmd",
      "revision": "c4b3bb93ec0b824a52d2f20ea05d5b15a26d7c52",
      "path": "vignettes/Processing.Rmd",
      "source_sha256": "b03314c83a8ac4efdb96820844914858692bc2a94891a8b386aaf3f90342a269",
      "inventory_document_key": "github:rformassspectrometry/qfeatures:vignettes/Processing.Rmd",
      "focus": "Filter contaminants/missing values and aggregate a prepared peptide assay to proteins, using a specified aggregation contract.",
      "inputs": "CPTAC study 6 A/B peptide table from MsDataHub; six quantitative sample columns. Stage a documented subset if needed.",
      "input_origin": "Observed proteomics measurements, processed by MaxQuant; any subset is an adapted input.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "MDAnalysis: RMSD of atomic structures",
      "domain": "Structural biology",
      "url": "https://github.com/MDAnalysis/UserGuide/blob/b20b22d2b050238436c76df0f984be7827854bce/doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb",
      "revision": "b20b22d2b050238436c76df0f984be7827854bce",
      "path": "doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb",
      "source_sha256": "58132de825e5e266f2c9890594a32b548167ac23f43826a3341db7abd71e3e7b",
      "inventory_document_key": "github:mdanalysis/userguide:doc/source/examples/analysis/alignment_and_rms/rmsd.ipynb",
      "focus": "Backbone alignment and CORE/LID/NMP domain RMSD summaries for the supplied adenylate-kinase trajectory.",
      "inputs": "MDAnalysisTests PSF/DCD inputs; stage a fixed frame subset if needed. No new molecular-dynamics simulation.",
      "input_origin": "Supplied simulated trajectory; structural reference lineage retained separately.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "xcms: LC-MS preprocessing and analysis",
      "domain": "Metabolomics",
      "url": "https://github.com/sneumann/xcms/blob/088a3c1494331241bbe0910551954356a43b0288/vignettes/xcms.Rmd",
      "revision": "088a3c1494331241bbe0910551954356a43b0288",
      "path": "vignettes/xcms.Rmd",
      "source_sha256": "4b6ea152eab306084910823e40406fea4f56821bbe5243d924ae49c144c8d210",
      "inventory_document_key": "github:sneumann/xcms:vignettes/xcms.Rmd",
      "focus": "The final PCA section: missing-feature handling, log transformation and sample structure in a prepared feature-intensity table.",
      "inputs": "Derived feature table plus sample metadata from the vignette's eight faahKO samples; upstream preprocessing belongs to input preparation, not the solver attempt.",
      "input_origin": "Observed mouse LC-MS measurements with derived inputs. Record preprocessing and retain the technical-bias caveat.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "COBRApy: simulating with FBA",
      "domain": "Systems biology",
      "url": "https://github.com/opencobra/cobrapy/blob/6f83a534569557f6a10bfdf6909522016985e47f/documentation_builder/simulating.ipynb",
      "revision": "6f83a534569557f6a10bfdf6909522016985e47f",
      "path": "documentation_builder/simulating.ipynb",
      "source_sha256": "43f93df5610db2f5c950e297121cfa85665cd4c589ca69dbec0af69371d1505d",
      "inventory_document_key": "github:opencobra/cobrapy:documentation_builder/simulating.ipynb",
      "focus": "Compare biomass and ATP-maintenance objectives in the E. coli core model; grade objectives/feasibility rather than requiring one unique flux vector.",
      "inputs": "Local copy of the textbook model and a CPU solver; avoid broad flux sampling or expensive loopless analysis.",
      "input_origin": "Curated mechanistic model and computed predictions, not measured fluxes.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "phyloseq: microbiome census analysis",
      "domain": "Microbiome science",
      "url": "https://github.com/joey711/phyloseq/blob/8a6c2350b985afb909428d396081605e9b3e2f0b/vignettes/phyloseq-analysis.Rmd",
      "revision": "8a6c2350b985afb909428d396081605e9b3e2f0b",
      "path": "vignettes/phyloseq-analysis.Rmd",
      "source_sha256": "73292276b1ac38601d7e7f7f0967f734ad3897570abccfa660aefbddb3576a75",
      "inventory_document_key": "github:joey711/phyloseq:vignettes/phyloseq-analysis.Rmd",
      "focus": "Per-sample richness and Shannon diversity from GlobalPatterns, joined correctly to sample metadata; avoid full ordination and plotting workflow.",
      "inputs": "Bundled GlobalPatterns count table and sample metadata.",
      "input_origin": "Observed community measurements; keep mock-community samples identified separately.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "scikit-bio: basic bioinformatics (IL6)",
      "domain": "Evolutionary biology",
      "url": "https://github.com/scikit-bio/scikit-bio-tutorials/blob/3b41d72a4114a3761bdc97dfe5a793c074426062/01-basic-bioinfo/01-basic-bioinfo.ipynb",
      "revision": "3b41d72a4114a3761bdc97dfe5a793c074426062",
      "path": "01-basic-bioinfo/01-basic-bioinfo.ipynb",
      "source_sha256": "b43f9d64de0c650ce5a3f28db7eccbda2b5ce25f07f3ed7b147492fabf5bb61e",
      "inventory_document_key": null,
      "focus": "Pairwise evolutionary distances or neighbor-joining topology from a prepared IL6 protein alignment of seven species; omit visualization and full alignment construction.",
      "inputs": "Pinned il6.ffn and a reference-prepared alignment; record translation/alignment provenance. Verify APIs against the pinned environment.",
      "input_origin": "Reference coding sequences with derived protein alignment; sequence accession lineage needs recording.",
      "source_inspected": true,
      "executed": false
    },
    {
      "label": "PyRadiomics: two brain-image examples",
      "domain": "Bioimage analysis",
      "url": "https://github.com/AIM-Harvard/pyradiomics/blob/8ed579383b44806651c463d5e691f3b2b57522ab/notebooks/RadiomicsExample.ipynb",
      "revision": "8ed579383b44806651c463d5e691f3b2b57522ab",
      "path": "notebooks/RadiomicsExample.ipynb",
      "source_sha256": "a92a5af3c46995fea7510fb1d91ce7f8854d8932f51b554698bdce885cab3702",
      "inventory_document_key": "github:aim-harvard/pyradiomics:notebooks/RadiomicsExample.ipynb",
      "focus": "Compare a fixed set of original-image first-order and shape descriptors within supplied tumor masks.",
      "inputs": "brain1/brain2 images and masks from getTestCase, staged offline; fixed feature settings. No segmentation or broad filter-bank extraction.",
      "input_origin": "Source describes brain images with supplied tumor segmentations; retain original image and mask provenance.",
      "source_inspected": true,
      "executed": false
    }
  ],
  "rejected_candidates": [
    {
      "source": "scikit-bio-cookbook / Alignments and phylogenetic reconstruction.ipynb",
      "reason": "Archived source with CC-BY-NC-SA terms; selected the BSD-3-Clause scikit-bio tutorials notebook instead."
    },
    {
      "source": "ipyrad / testdocs/analysis/cookbook-distance.ipynb",
      "reason": "Inspection found simulated inputs and incomplete example cells; selected a more self-contained observed-sequence example."
    }
  ]
}
```

</details>
