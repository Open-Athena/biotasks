# Notebook reference workflow

Current agreement, 2026-10-14. Preparation selects existing terminal results and
adds code to save them. Execution owns environment and input setup. This update
implements the preparation interface; the replacement execution worker is not
integrated yet. No model or scientific run has used this revised contract.

## Stages and exact responsibilities

| Stage | Input | Work | Output and status |
| --- | --- | --- | --- |
| Conversion (programmatic) | Pinned original notebook JSON. | Pinned Jupytext `py:nomarker` conversion; preserve Markdown as comments; check source code order and syntax. No notebook execution. | `baseline.py` and conversion receipt. Implemented for the admitted Python profile. |
| Preparation (GLM, no tools) | Complete baseline script, provenance, conversion receipt and intended execution limits. No data contents, stored notebook outputs or images. | Select terminal scientific results already held in original named variables or object fields; add code to save those values. | Complete `reference_script`, one `artifacts` inventory, explanation, excluded outputs and unresolved assumptions. Updated; not rerun. |
| Preparation checks (programmatic) | Complete worker response and untouched baseline. | Validate JSON Schema, Python syntax and unique relative artifact paths; save response and compute diff. Execute nothing. | Script and diff ready for inspection. These checks do not prove scientific fidelity. |
| Scientific review (separate GLM call) | Original script/narrative, proposed script, diff and inventory. | Check endpoint eligibility, exclusions, faithful saving and unchanged science against the original source. | Approve, revise or reject with specific findings. Prompt updated; not run on the new contract. |
| Environment and input setup (tool-enabled execution worker) | Reviewed preparation output, original source/provenance and available environment instructions. | Inspect dependencies, build and test the environment, download original inputs, configure caches and offline paths; preserve recipe, lockfile, hashes and changes. | Runnable reference environment and staged inputs. Replacement worker not integrated. |
| Scientific execution (programmatic) | Prepared environment, staged original inputs and reviewed script. | Run the ordinary script offline, CPU-only, with the agreed resource/time limits; record outputs, logs, timing and failures. | Measured reference evidence. Not launched by preparation. |

The current converter admits ordinary Python nbformat-4 sources. Unsupported
kernel-dependent syntax/state is rejected; other languages need separate
profiles. The user-selected newer Scanpy source and untouched conversion are in
`reference-inputs/scanpy/`; source identity and terms are in `source-manifest.json`
and `seeds/current.json`. No seed-specific endpoint rules are in the factory.

## What preparation may save

Select scientific end products, not every object that remains in memory.
Eligible results must already be stored in named variables or fields in the
original script. Save their values and identifiers through native writers or
straightforward format conversion. A whole object qualifies only if it is itself
the scientific deliverable; it is not a fallback for selecting endpoints.

Intermediate matrices, diagnostic counts, checkpoints and full-state snapshots
are outside the exported targets. Do not add computation for exporting results:
no new filtering, ranking, aggregation, scaling or reconstruction of plotting
internals. Do not turn a previously unnamed expression into a new variable.

Consider all analysis branches in one endpoint inventory for one task. Explain
branches or plot-only results without eligible stored outputs in
`excluded_outputs`. Their original computation remains intact. Reject if there
are no eligible terminal results. The preparation worker leaves input-loading
code unchanged and does not generate dependency manifests or staging scripts.

The canonical [preparation prompt](../../src/biotasks/prompts/notebook-reference-prepare.md)
and [review prompt](../../src/biotasks/prompts/notebook-reference-review.md) state
these rules. Scientific eligibility and preservation need review; the schema
and syntax validator alone cannot enforce them.

## Preparation interface and run boundary

`run_preparation.py` uses GLM-5.3, medium reasoning and strict JSON-schema
responses. It permits one creation and at most one complete-object structural
repair, with no extra client token/byte limits and the existing 600-second
per-request timeout. It creates no task sandbox and executes no generated code.
No separate branch map or duplicated environment inventory is requested.

The former combined runner is retired. `run_reference.py` and its packaging path
refuse execution before submitting a job. This prevents the old text-only
setup workflow from running against the new preparation schema. Its historical
implementation is preserved at
[2e1fb63](https://github.com/Open-Athena/biotasks/blob/2e1fb637ed0a8dad48e4e8ef9017e49e765d9575/experiments/19-repo2rlenv-notebook-pilot/run_reference.py).
Reusable environment, execution and evidence helpers remain available for the
replacement worker. This document does not assign new execution budgets or
claim that the replacement worker is ready.

## Existing evidence and next step

[Preparation run 005](preparation-runs/005/README.md) used the preceding contract:
its full-object export and newly captured expression are not evidence of
compliance with the revised selection rule. Its recorded output stays unchanged.
The [historical execution record](https://github.com/Open-Athena/biotasks/blob/2e1fb637ed0a8dad48e4e8ef9017e49e765d9575/experiments/19-repo2rlenv-notebook-pilot/reference-execution.md)
explains earlier reference runs under the superseded workflow.

The next preparation run needs inspection before advancing. Tool-enabled setup
is the next implementation boundary; it must preserve the science while resolving
dependencies and staging inputs. Task construction, artifact comparisons, Harbor
validation, blind solving and publication remain downstream work. No model run,
execution or viewer update accompanies this interface change.
