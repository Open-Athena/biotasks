# Baseline and comparison protocol

## Question and baseline

Can independent workers preserve a source analysis's science while producing
runnable, deterministically graded tasks? Baseline `v1-seta-original` starts from the released SETA notebook adapter,
shared idea prompt and datapoint builder, pinned under `baselines/seta-v1/`.
Keep their text unchanged for the baseline; record input/harness porting separately.
The original BioTasks draft in `src/biotasks/prompts/notebook2task.md` is retained
as `v0-biotasks-draft`, a separate untested candidate, not the default baseline.
Neither prompt has been executed or experimentally selected.

Issue #10 established no successful task authoring or supported prompt winner.
Use its fixed inputs, evidence preservation, failure inspection, and repeated
comparisons as workflow lessons; do not transfer its counts as a baseline score.
The literature ideas in #17 are hypotheses supplied by the issue. This initial
draft is not an independent literature replication or a component ablation.

## Input assignment

Select 4–6 development analyses with Gonzalo, spanning biological workflows and
Python/R where feasible, plus separate reserved examples. A smaller pilot may
exercise orchestration, but cannot establish general transfer. Record source
revision/hash, language, source context, study lineage, terms, evaluation overlap,
and split in `sources.json` before conversion. Keep related studies/derived
notebooks in one split. Do not tune on reserved examples.

Gonzalo requested brainstorming in Scanpy, DESeq2, bedtools, AlphaGenome, and
gReLU, with reuse of issue #10 inventories. `explorer/catalog.json` records
candidate analyses and task ideas, not a frozen experimental input set.

## Proposed budget — not approved execution

For the first development batch, propose one job per supplied source, at most
60 minutes per author job including repair, and at most two repair cycles after
the first packaged check. Stop earlier when input access or scientific adequacy
is blocked. Use identical limits for matched baseline/revision jobs.

Model, reasoning effort, token cap, dollar cap per job and batch, author compute,
task compute, concurrency, and validation/solver budget remain unassigned.
No launch until those are explicit and the execution backend can enforce them.
Do not treat this wall-clock proposal as authorization for paid services.
Record validation and solver costs separately from authoring.

The user clarified that the NeurIPS single-cell benchmark is not an LLM
evaluation exclusion. Retain dataset provenance and check overlap against
evaluations relevant to our models; do not reject a source merely because it
was used in a biological method benchmark.

## Batch runner requirements

Implement a small runner once the backend is selected. It must create one
isolated job per source, freeze rendered prompts and input manifests, and record
model/provider/version, reasoning settings, source and harness revisions,
environment, budgets, commands, timestamps, logs, cost telemetry, and artifact
hashes. Unknown provider details must be explicit, never guessed.

Use an append-only run directory for each attempt. Keep service errors, timeout,
missing reports, malformed reports, and blocked inputs as distinct outcomes.
Capture partial artifacts before teardown; never rerun over prior evidence.
Enforce time/spend limits outside worker instructions, support cancellation,
and verify cleanup of resources owned by each job. A process exit of zero is
not task acceptance. Directory separation alone is not sandbox isolation.

## Independent assessment

Freeze each candidate package before review. Record separately:

1. Scientific fidelity and clarity, with source-linked review findings and any
   judgments still requiring biological expertise.
2. Fresh environment/reference execution and deterministic grader behavior.
3. No-op rejection and task-specific scientific counterexamples.
4. Valid alternative methods/representations where permitted by instructions.
5. Fresh solver attempts with no reference visibility, followed by trace review
   for ambiguity, information leakage, and grader shortcuts.

Reviewers must not use the author's completion flag as acceptance. Automation
cannot establish every scientific judgment. Record manual rescue as intervention;
retain the original outcome and rerun a fresh worker after encoding any general
fix. Failed solves alone do not prove task defects.

## Revisions and decision

Group observed failures, then register one focused prompt-change hypothesis with
predicted effects and regression risks. Match sources, settings, budgets, and
validation across prompt versions. Repeat promising comparisons before choosing
a candidate; select repeat counts before those runs. Keep attempt-level results.
Report small-sample uncertainty and do not infer component effects from bundles.

For each split/version report all scheduled sources, retrieval and reference
success, produced packages, accepted source conversions, distinct accepted tasks,
scientific/grader defects, fresh-solver outcomes, interventions, and cost. Keep
infrastructure and unreviewed outcomes explicit; do not silently remove them
from denominators. More tasks from a source is not more accepted conversions.

Run the selected candidate on reserved sources without source-specific coaching.
If revised after seeing reserved failures, those sources become development data
and new untouched sources are needed. Conclude with a supported recommendation
or inconclusive/negative finding; no claim about SFT/RL gains is in scope.
