# Evidence available to the notebook task designer

2026-10-13. Source assessment followed by a prepared design-stage integration.
The adapter, profiler and canonical prompt now have local fixture and upstream
controller checks. Live GLM compatibility and real-data profiling have not run;
this is not an accepted design or a completed pipeline campaign.

## Finding

The designer in reviews 004–013 received notebook source and provenance, but no
measured data profile, inspected package behavior or tools. General prompt revisions,
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

## Prepared integration

[Patch 0009](patches/0009-injectable-artifact-runtime.patch) adds an injectable
runtime to the pinned upstream artifact controller. Its default behavior is
unchanged, and the supplied runtime identity becomes part of retained-artifact
matching. The existing Anthropic bridge and OpenAI Responses implementations
cannot directly call the approved GLM Chat Completions service. This small
injection avoids modifying either transport or replacing the controller.

[design_stage.py](design_stage.py) calls that controller with SETA's existing
`TaskDesign(core_capabilities, draft_spec)` schema and the
[canonical design prompt](../../src/biotasks/prompts/notebook-task-design.md).
The controller handles submissions, revisions, input identity, durable drafts
and completed-artifact reuse. The GLM adapter supplies one bounded Chat
Completions request per turn, preserves reasoning/tool linkage and dispatches
only registered controller tools. It does not validate the science.

The adapter disables SDK retries and records each request before dispatch.
Incomplete or uncertain responses stop the stage; they cannot execute partial
tool calls or automatically restart the retained operation. Schema-invalid
submissions may be revised within the same allowance. The final two model calls
expose only submission/revision tools. Exact requests, responses and the bounded
tool transcript are retained alongside the upstream operation and budget records.
The free endpoint settles model cost to zero; the upstream monetary ledger needs
a one-micro-dollar bookkeeping hold before each request. Unknown outcomes retain
that hold and their request slot. This does not account for remote workspace cost;
the owning launcher must do so.

[The profiler](../../src/biotasks/data_profile.py) hashes explicitly staged files
and verifies supplied source checksums. It inspects bounded CSV/TSV prefixes or
HDF5 metadata using optional, [pinned readers](profile-reader-requirements.txt).
It never runs notebook code or chooses an analysis. Recorded dimensions, types
and tiny stored integer vectors do not establish biological axis semantics.
Unknown formats, missing readers, sampled row counts and truncated inspections
remain explicit. It is not a general data downloader or biological interpreter.

The old direct-call campaign entry point now refuses this tool-enabled prompt
before any model call or sandbox creation. The standalone integration ends with
`submitted_for_review`; it cannot invoke construction, quality checks or a solver.
Historical continuation support remains available for the previously built task.

### Before the first live design run

Review the actual canonical prompt first. Then prepare a credential-free remote
tool workspace using the existing execution boundary: model client on Iris,
commands through the upstream remote-worker interface. The launcher must enforce
resource ceilings, immutable original inputs, a writable scratch directory,
cost/time accounting, evidence download and owned-resource cleanup. These
provisioning steps are not implemented by `design_notebook`; it accepts an
already prepared worker. A shell command is not restricted to scratch by changing
its working directory; filesystem isolation must be established by the launcher.

Stage the newer notebook's real inputs and produce the factual profile remotely.
The generic profiler accepts a JSON list of file paths and optional source
checksums, for example via `python -m biotasks.data_profile --root INPUTS
--manifest FILES.json --output PROFILE.json`. Preserve the command, environment
and output. Data-source selection here supplies source files, not a manual task
objective, selected methods or expected answers.

For the first design trial, propose an eight-request ceiling, 16,000 output tokens
per request, high reasoning, 600 seconds per request and a 1,800-second stage
deadline. Inspection commands have at most 120 seconds each and 300 cumulative
command seconds, with a bounded termination grace period. These are upper bounds,
not guaranteed usable turns. Tool execution, download/setup and cleanup need
their own launch records within the existing overall authorization. The future
task envelope remains 4 vCPU, 8 GiB RAM, 10 GiB disk, CPU only and 600 seconds for
the solver; authoring time is separate. No new run or spending is claimed here.

### Local validation

The real upstream artifact controller accepted a scripted revision after rejecting
an invalid submission, reused the committed artifact without another call, and
refused to replay an incomplete operation. A mock HTTP transport exercised the
installed OpenAI SDK's GLM extension and reasoning fields. This establishes local
wiring, not live endpoint support. Root tests cover request accounting and factual
profile behavior; tiny synthetic HDF5 fixtures exercise the native reader without
downloading biological data. Affected upstream artifact-stage regressions pass.

Run the experiment checks with the pinned upstream environment, BioTasks `src`
and this experiment on `PYTHONPATH`. Run `test_hdf5_profile.py` with the pinned
optional readers installed separately. These checks use no model, remote worker
or biological download. Local checks must follow the repository's shared-node
resource guard. No generalization or runtime-feasibility claim follows from them.

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
