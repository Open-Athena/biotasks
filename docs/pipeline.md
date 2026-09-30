<!-- Adapted from Marin 72008dd68247318a367a840a4f41e27fb15ff7e1:docs/experiments/bio-task-generation/index.md.
Migration changes are documented in docs/migration.md. -->

# Computational biology task generation

This plan was migrated from [Marin issue #9257](https://github.com/marin-community/marin/issues/9257) at the [pinned integration snapshot](migration.md). It describes a proposed pipeline; no runnable generator exists yet. The scientific design remains under review. See the [README](../README.md) for the implemented prompt-inspection commands. Earlier prototypes remain historical references and do not impose compatibility requirements on this design.

Generate realistic computational biology tasks with deterministic executable rewards, packaged for Harbor and usable by other people's pipelines. Optimize for using bioinformatics software to answer scientific questions. Analysis scripting, metadata reconciliation and workflow configuration belong in scope. Developing new bioinformatics algorithms or fixing package internals is not the initial target.

Task generation includes repository discovery, input curation, model-assisted authoring and task validation. Recipes define meaningful instance variation and preserve shared-data lineage for downstream users. Data splitting, downstream model training, teacher-trace collection, model selection for training and context budgets are outside scope. Models used to author or trial tasks are part of the generation process.

## Read by activity

| Document | Purpose |
| --- | --- |
| [Requirements](requirements.md) | Scientific, sandbox, runtime and deterministic-reward requirements |
| [Repository discovery](discovery.md) | Find and inspect tools, pipelines, tutorials and paper-analysis repositories |
| [Task authoring](task-authoring.md) | Convert sources into tasks and generate meaningful variations |
| [Validation](validation.md) | Execute references, challenge graders, trial tasks and decide release readiness |
| [Storage and publication](storage.md) | Public artifacts, release layout, provenance and solver isolation |
| [Transcriptomics examples](examples/transcriptomics.md) | Concrete candidates for reviewing the process |
| [STAR–DESeq2 worked example](examples/star-deseq2.md) | Inspect a source workflow, define focused and integrated recipes, and plan instance variation |

## Direction

Start from recurring scientific workflows found in repositories, tutorials and reproducible studies. Use benchmarks as optional inspiration and checks for omissions; benchmark question frequencies do not determine priorities. Preserve existing out-of-distribution exclusions when borrowing benchmark material. SciGym is excluded.

Use observed biological data as the corpus backbone, with explicitly labeled adaptations and simulations where useful. Include both focused analyses and connected workflows. Prefer breadth across studies, experimental designs and scientific questions before producing many variants of a few datasets.

Track operations and scientific contexts as separate descriptive axes, plus formats, repository use and biological lineage. For example, differential expression combines statistical inference with gene expression. Single-cell, spatial and longitudinal design may be cross-cutting tags. Neither an exhaustive ontology nor a fixed task-count target is required to begin reviewing candidates.

Recipes specify how to generate and verify concrete task instances. Focused recipes can also contribute stages to integrated recipes, with explicit input/output contracts and end-to-end validation. This composition does not add a categorization level; see [task units and composition](task-authoring.md#task-units).

For recipes intended to scale, establish one instance and then target [ten validated, meaningfully varied instances](task-authoring.md#initial-instance-target). Record shared study lineage and document exceptions for useful narrower recipes. This initial target does not cap later generation.

For a selected repository, develop four prompts: **find units → author a task → solve independently → reflect on and validate the task**. Authoring has explicit proposal and construction phases. An LLM reviewer examines solver traces and executable evidence, then recommends acceptance, revision or rejection. Automated checks run between stages, and an independently controlled harness owns acceptance. See [prompt roles and worker contexts](task-authoring.md#prompt-and-run-versioning).

Work should be public: documentation, code, prompts, task inputs, references, graders and validation evidence. Public reference solutions must remain outside solver-visible task inputs. Publication is subject to the source assets' redistribution terms; see [storage](storage.md).

## Reference cases

See the [reference cases](reference-cases.md) for reviewing scientific task framing
and proposed pipeline changes. These are documented examples, not an automated
regression suite.

## Open decisions

- [Extraction rules for code and notebooks](task-authoring.md#work-item-extraction-rules-for-code-and-notebooks): define candidate boundaries for functions, classes, cells or chunks, and complete analysis documents across languages and formats.
- Recipe boundaries, composition and permitted variation axes, to be calibrated through [transcriptomics examples](examples/transcriptomics.md).
- The vocabulary for operations and scientific contexts, and how demand and missing coverage influence selection. No uniform allocation rule or numerical weighting formula is adopted.
- How much retrieval-only or generic statistical work belongs in the corpus, and how much benchmark analysis to retain.
- The size and composition of the [reusable input collection](discovery.md#reusable-input-collection). Around ten datasets per initial scientific area is a provisional idea; study diversity and recipe compatibility guide selection.
- The initial candidate portfolio and the ongoing independent-trial and human-review sampling policy after calibration.
- Authoring model, worker concurrency, budgets and repair limits. GLM is a candidate; no model service is required by a released grader.
- The public release repository name and account, storage quota and final packaging layout. The storage page proposes Hugging Face; no release repository has been created by this plan.

Next, compare a focused transcriptomics task and a connected analysis from the same observed study. Review their prompts, input boundaries, references and grading contracts, then broaden the candidate portfolio before scaling authoring.

## Earlier work and supporting catalogs

Earlier implementation and planning are preserved at [checkpoint d3f09bbb3b](https://github.com/marin-community/marin/tree/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af). Their rules and status claims are historical, not the specification for this pipeline. No new task validation or release is claimed by this documentation change.

- [Repository adoption inventory](https://github.com/marin-community/marin/blob/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af/docs/experiments/computational_biology_bioinformatics_packages.md): the original 50 repositories, including dated downloads, stars and citations. Discovery has no 50-repository cutoff.
- [Task catalog and validation evidence](https://github.com/marin-community/marin/blob/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af/docs/experiments/bio-task-catalog.md): earlier candidates and executable checks, with readiness varying by task.
- [Benchmark source inventory](https://github.com/marin-community/marin/blob/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af/experiments/post_training/bio_tasks/benchmark_sources.json) and [question inventories](https://github.com/marin-community/marin/tree/d3f09bbb3ba2e74c4c3073ed20087cd5f97139af/experiments/post_training/bio_tasks/benchmark_tasks): auxiliary discovery material; preserve recorded exclusions, including Terminal-Bench-Science, GeneBench, BioMysteryBench and SciCode.

Maintain accepted decisions in the relevant page and unresolved choices here. Track research in [BioTasks issues](https://github.com/Open-Athena/biotasks/issues), with branch-local logbooks and evidence linked by commit permalink. See the [research workflow](research-workflow.md).
