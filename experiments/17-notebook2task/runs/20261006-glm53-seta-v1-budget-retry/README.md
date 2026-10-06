# GLM-5.3 baseline: one draft, one output-limited attempt

The bounded retry obtained 17 GLM-5.3 responses through the existing bulk
service. Cytopathology wrote a complete draft; ASXL1 reached its output ceiling
without a draft. This establishes working model access and idea-stage authoring,
not a validated task package or scientific result.

| Case | Outcome | Requests | Authoring seconds |
| --- | --- | --- | --- |
| Cytopathology | Draft written; final response completed | 8 | 85.53 |
| ASXL1 / DESeq2 | Output limit; final 8,192 tokens entirely reasoning | 9 | 71.87 |

Read the [actual cytopathology draft](results/seta-cytopathology/artifacts/draft_spec.md),
[case summaries](results/summary.json), and per-case events.jsonl files. Raw
responses, tool results and prompts are retained. The returned artifact archive
passed its [SHA-256 transport check](results/transport.json).

## Protocol and limits

The [plan](plan.md) records the change from the first live GLM attempt. Original
source prompts are byte-identical. Requests use explicit medium reasoning,
8,192 output tokens, at most 12 requests and 480 seconds per case, with a
180,000-character serialized-context ceiling. Tools read/list/write files; they
do not execute scientific workflows. One CPU worker ran cases sequentially.
No new inference service, GPU, or commercial model API was provisioned.

Provider usage totals: 290,196 prompt tokens and
25,767 completion tokens across 17 responses; repeated
context and reasoning are included. Billing is not observable. The service
reports model `glm-5.3` and fingerprint `vllm-0.28.0-tp8-f8f644d5`; this is not an
independently pinned weights revision. [Installed package versions](installed-packages.txt)
come from worker setup logs; transitive dependencies were resolved at runtime.
The harness and budgets differ from Codex and SETA's original runner.

## Parent inspection: draft is not accepted

- The draft asks for training three model families, contradicting the shared
  SETA idea prompt's no-training instruction. Unlike Codex's frozen-model
  workaround, GLM follows the notebook adapter's training goal. This is an
  observed response to conflicting instructions, not faithful compliance with
  the whole prompt stack.
- Its proposed test-set integrity check allows solver-chosen rows and makes
  training/test disjointness conditional on an optional training-ID artifact.
  True labels are visible in the input; consistent prediction files alone
  cannot establish genuine held-out model performance.
- The draft introduces a new split and performance thresholds without executing
  a reference. Its proposed grader also requires nonzero CV variation and a
  particular top-feature overlap, which could reject valid alternative models.
  These are static review concerns, not demonstrated exploits or measured
  false rejections.

No builder continuation or native validation ran in this GLM retry. ASXL1's
truncated reasoning is neither a rejection nor a finished biological task.
Preserve both outcomes before changing the recipe or increasing budgets again.

Iris terminal state `SUCCEEDED` was confirmed at 22:06 UTC (6:06pm Eastern).
All earlier dispatch attempts are terminal; no job from this pilot remains active.
