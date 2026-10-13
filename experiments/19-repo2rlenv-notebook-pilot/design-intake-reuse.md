# Evidence available to the notebook task designer

2026-10-13. Static source inspection and proposed next experiment. No new
authoring runtime, profiling job, construction, solver or viewer change has
been implemented or run for this proposal.

## Finding

The current designer receives notebook source and provenance, but no measured
data profile, inspected package behavior or tools. General prompt revisions,
additional reasoning and model critiques have not reliably produced a coherent
scientific contract. Reviews 004–013 preserve six design responses and four
critique responses, including incomplete outputs; none establishes an accepted,
scientifically validated design. This small, adaptively revised series is not a
controlled comparison of models, prompts or frameworks.

The next experiment should change the evidence available to the designer. It
should preserve worker ownership of the task's objective and scope. More data
does not by itself fix reasoning or verification errors: the label-permutation
contradiction in review 013 is detectable from the draft alone.

## Upstream components inspected

Repo2RLEnv revision: `55554430cd724efded1f5ad0ff98ebca5d88c0a6`, already pinned by
this experiment. Inspected Tasksmith source files were checked against Git blob
identities at that revision. Original SETA revision:
`e4715b01174e6c9503fc46120d81dd692ced75e6`.

| Component | What the code supplies | Fit and remaining work |
| --- | --- | --- |
| [Repo2RLEnv SETA design call](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/src/repo2rlenv/pipelines/recipes/seta_seed2synth/recipe.py) | One structured completion producing `TaskDesign(core_capabilities, draft_spec)`. Its adaptation explicitly forbids tools. | Keep this output boundary and the later builder/quality/release path. Adding factual profile input is straightforward; tools require changing the design mechanism. |
| [Original SETA notebook intake](https://github.com/camel-ai/seta/blob/e4715b01174e6c9503fc46120d81dd692ced75e6/datasynth/seed2synth_pipeline/agents/claude_agents.py#L473) | Loads existing dataset manifests, lists local data files, summarizes the first 20 notebook cells and leaves the full notebook available for reading. | Reuse the prepared-evidence pattern. This adapter consumes manifests; it is not a general profiler for arbitrary biological formats. Preserve whole-notebook coverage rather than selecting the task from an early-cell preview. |
| [Original SETA idea worker](https://github.com/camel-ai/seta/blob/e4715b01174e6c9503fc46120d81dd692ced75e6/datasynth/seed2synth_pipeline/agents/claude_agents.py#L679) | Claude Agent SDK worker with Bash, Read, Write, WebSearch and WebFetch; produces `draft_spec.md`. | The notebook route is real, not merely a suggested use of text seeds. Its concrete implementation selects Claude Opus 4.6; it is not already a tested GLM endpoint adapter. Its source-specific task-selection policies are not our scientific policy. |
| [Tasksmith artifact stage](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/src/repo2rlenv/tasksmith/author/artifact.py#L79) | Accepts a Pydantic schema, inputs, prompts, deadline, budget, optional shell and validation handler. Supplies submit/revise tools, saved drafts, input identity checks, bounded recovery and completed-artifact reuse. | Best candidate for direct code reuse beneath a notebook design stage. It does not require Tasksmith's PR-specific schema. Structural acceptance must remain distinct from scientific validation. This is an internal interface to pin and test. |
| [Tasksmith author runtimes](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/src/repo2rlenv/tasksmith/author/agent.py) | Pi/OpenCode through an Anthropic-only bridge; a separate Responses runtime with an explicit OpenAI model allowlist. | Neither path currently supports the approved GLM Chat Completions endpoint. This needs a real transport/tool-loop adapter, including request accounting and response handling, not just a model-name change. |
| [Tasksmith PR workflow](https://github.com/huggingface/Repo2RLEnv/blob/55554430cd724efded1f5ad0ff98ebca5d88c0a6/src/repo2rlenv/tasksmith/runner.py) | Investigation, environment readiness, design, patch reversal, before/after tests and quality checks. | Reuse the evidence-before-design principle and bounded remote-tool pattern. Its PR intake, test profile and patch-reversal oracle do not apply directly to a notebook analysis task. |

The original SETA and Repo2RLEnv SETA routes must not be conflated. The original
has a tool-using notebook idea agent. The selected Repo2RLEnv adaptation replaces
that with a direct structured call. SETA's
[download helper](https://github.com/camel-ai/seta/blob/e4715b01174e6c9503fc46120d81dd692ced75e6/datasynth/seed2synth_pipeline/hf_utils.py)
retrieves prepared seed folders; no general biological-data manifest producer
was identified in the inspected intake path.

## Recommended minimal change

Keep one design stage with bounded investigation inside it. Reuse Tasksmith's
artifact-stage controller and preserve the existing `TaskDesign` output for the
SETA builder. Keep the pinned dependency plus an explicit, reviewed integration
patch; a full fork or adoption of Tasksmith's PR pipeline is not required by the
inspected interfaces.

1. **Prepare factual evidence.** Stage the original notebook and accessible real
   data with verified byte identities. Supply file inventory, sizes, format and
   measured structural metadata where available: dimensions, data types,
   identifiers, schema and representation. Record the inspection command,
   environment and output for each claim. Distinguish observed facts, source
   statements and unresolved questions. No task objective, selected analysis
   stage, target genes or expected result belongs in this manifest.
2. **Let GLM investigate when needed.** Give the design worker bounded remote
   inspection tools to read source, inspect data and check versioned package
   documentation or small behavior probes. Preserve original inputs and use a
   scratch workspace for probes. Do not require executing the entire notebook
   or creating a complete task before the worker can choose a design. For an
   unfamiliar format, report an unknown or let the worker inspect it rather
   than adding a notebook-specific extraction rule.
3. **Submit a compact design.** GLM chooses the scientific question, justified
   scope, public methods and outputs, and how correctness could be established.
   Cite the evidence inspected. Leave measured runtime and numerical calibration
   to construction. Resolve contradictions at design; do not turn unknown facts
   into invented defaults or use future calibration to redefine the method.
4. **Stop for review.** Preserve the factual profile, exact prompt, tool trace,
   submitted design, rejected submissions and accounting. No automatic transition
   to construction or update of the explorer.

Do not add a second LLM agent merely to summarize the first. Deterministic
intake plus on-demand tools in one design stage is the initial proposal. A
separate investigation stage becomes useful only if its reusable evidence or
failure isolation justifies it. Tasksmith's pre-design readiness checks have a
known merged implementation to test; here, pre-design readiness can establish
input access and inspectability, not yet certify an unchosen task's solution.

## Integration work still needed

- Add GLM Chat Completions support under the artifact-stage runtime boundary,
  or parameterize that boundary to use an existing compatible tool runtime.
  Compare those concrete patches before choosing a harness; the current source
  does not establish which has lower maintenance cost. Retain tool-result
  linkage, reasoning fields where needed, explicit raw-request limits, durable
  responses and no model fallback.
- Reuse the existing Iris-hosted model client / remote task execution separation.
  The authoring tool workspace is separate from the future offline solver.
  Profile and probe time is authoring work, not part of the 600-second solver
  allowance. Specify finite authoring request, wall-clock and tool budgets
  before executing the proposed stage.
- Use upstream artifact submission and schema feedback without treating them
  as scientific approval. Task-specific analysis and corrections still come
  from GLM; deterministic code supplies facts and enforces generic boundaries.
- Review the changed canonical design prompt before running it. Replace its
  no-tools assumption and reduce the demand for speculative implementation
  detail; do not append a list of methods or mistakes from this seed.

These are proposed modifications, not completed compatibility checks or a
newly authorized full pipeline campaign. GLM-only authoring and the factory-only
rule remain in force.

## Alternatives and assessment

**Profile only, keeping the direct call** is the smallest implementation and a
useful control. It improves knowledge of actual inputs but cannot answer an
unanticipated methodological or package question. **Tools without prepared
evidence** can work but repeatedly spends turns rediscovering elementary facts.
**Porting original SETA wholesale** brings its Claude integration and Kaggle
policies. **Switching to all of Tasksmith** changes the task type to repository
repair. Neither wholesale switch is needed to test the missing-evidence
hypothesis. More text-only critiques have already shown their limits here.

Freeze the general review criteria, prompt and budgets before assessing the
next mechanism. Record whether each important claim has source or execution
evidence, whether a scientifically coherent task was selected, whether public
requirements agree with verification, and the time/calls spent. Tools should
resolve a specific uncertainty, not be required for appearances. Report rejection
as a valid outcome. The current notebook is a development case; a frozen test on
different notebooks is needed before claiming generality. This proposal does not
silently expand the one-notebook pilot or authorize those additional runs.
