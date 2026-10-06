# First SETA v1 pilot — October 6, 2026

The unchanged SETA idea prompts produced one rejection and one draft that changes
the source task to frozen-model evaluation. These are two comparison examples,
not a representative development batch. No task is independently accepted.

| Trial | Stage | Outcome |
| --- | --- | --- |
| Initial cytopathology | Idea | Confounded rejection: harness execution restriction and upstream no-training language; preserved, not counted as a clean baseline result. |
| Corrected cytopathology | Idea | Draft produced; transforms model training into evaluation of frozen model bundles. Those bundles are not present in the source inputs. |
| ASXL1 RNA-seq | Idea | EARLY_DITCH: one DESeq2 model; enrichment does not satisfy the adapter's multiple-model criterion. |

See each trial's `prompt.md`, `draft_spec.md`, `events.jsonl`, `execution.json`
and `resources.json`. `harness-correction.md` preserves the first failure and
resource-monitor limitation. Rendered prompts and input manifests were committed
before execution. Source hashes remained unchanged after both idea trials.

## What this tests and what it does not

Model/runtime: Codex CLI 0.160.1, requested model gpt-6-astra, medium reasoning, existing ChatGPT
login. The exact served model snapshot and full harness system prompt are not
returned in the event stream. Five-minute limit per call, sequential execution, no paid infrastructure.
This changes the model and harness from SETA's Claude implementation. Prompts
retain their source text; runtime paths and seed blocks are rendered. The model
can inspect files and write drafts but cannot execute the scientific workflow
at the idea stage. Token usage is recorded in final turn events; cost in dollars
is unavailable. No general conclusion about prompt quality follows from n=2.

The original shared idea prompt (line 195) and builder (line 395) prohibit model
training; the notebook adapter instead asks for multiple trained models. The
corrected cytopathology trial worked around that conflict by proposing frozen
models, moving substantial work into builder preparation. That is a changed task
boundary, not reproduction of the source notebook or its released SETA task.

The cytopathology draft also introduces a new 80/20 partition, 24 model bundles,
and unvalidated performance thresholds. In particular, it proposes revising the
model bank until the held-out threshold passes: this risks tuning to the holdout.
These are parent inspection findings, not executed scientific comparisons.
The RNA-seq rejection demonstrates a concrete mismatch between the unchanged
ML-specific gate and a biological analysis, not that DESeq2 cannot yield a task.

## Inputs and lineage

Real source-released inputs were staged under ignored `downloads/`, approximately
33 MiB total. `input-manifest.json` gives URLs, file sizes and SHA-256 hashes.
SETA's current Kaggle R Markdown v96 was used, not an asserted generation-time
version. BixBench uses its pinned v1.5 capsule and remains comparison-only.
Worker input excludes the released task, its ideal answer, upstream solution,
and our prior inspection notes. The original notebook's saved outputs remain
source evidence. No new scientific reference run occurred.

## Builder-stage outcome

The builder trial hit its 300-second limit (process exit 124). It left task
instructions, environment code, a reference evaluator, tests and weights, but
no completed validation report or prepared frozen model bank. Parent static
inspection passed 13 artifact/syntax/weight checks; none execute the task or
establish scientific correctness. Preserve this as a timeout with partial
artifacts, not a successful conversion. The outer resource guard exits zero
because the runner records child failures; execution.json holds the trial's 124.

Gonzalo subsequently authorized an Iris CPU job or Daytona for native validation.
No remote job has been submitted. A follow-up billing question arrived before
submission; no new model or compute call is running. All model trials used the
existing ChatGPT login, not an API key. ChatGPT plan/credit billing settings are
not visible here; do not describe the calls as cost-free or assign API prices.
