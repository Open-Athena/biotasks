# Notebook reference workflow

Current agreement, 2026-10-15. Preparation selects existing terminal results and
returns export code for the controller to append to the untouched source. Execution owns environment and input setup. This update
implements the preparation interface; the replacement execution worker is not
integrated yet. The append-only preparation contract is implemented and locally
tested. [Run 007](preparation-runs/007/README.md) returned an append-only proposal
with exact source preservation, but endpoint selection remains flagged for
review. Run 006 used the preceding full-script response contract; its original
evidence remains unchanged.

## Stages and exact responsibilities

| Stage | Input | Work | Output and status |
| --- | --- | --- | --- |
| Conversion (programmatic) | Pinned original notebook JSON. | Pinned Jupytext `py:nomarker` conversion; preserve Markdown as comments; check source code order and syntax. No notebook execution. | `baseline.py` and conversion receipt. Implemented for the admitted Python profile. |
| Preparation (GLM, no tools) | Complete baseline script, provenance, conversion receipt and intended execution limits. No data contents, stored notebook outputs or images. | Select terminal scientific results already held in original named variables or object fields; add code to save those values. | `export_code` only, one `artifacts` inventory, explanation, excluded outputs and unresolved assumptions. Run 007 returned a proposal; full-state/diagnostic selection is flagged. |
| Preparation checks (programmatic) | Complete worker response and untouched baseline. | Append export code to the untouched baseline; validate JSON Schema, combined Python syntax and unique output-relative paths; save response and compute diff. Execute nothing. | Script and diff ready for inspection. These checks do not prove scientific fidelity. |
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
straightforward format conversion. Select results from the analysis goals before
choosing storage. Exclude mixed analysis-state containers; select their terminal
fields instead. Standalone result tables or embeddings may be exported whole,
preserving meaningful fields and identifiers. Explain any omitted result fields.
Plot display or earlier computation does not automatically make a result intermediate.

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
responses. It makes exactly one call, with no automatic repair, no extra client
token/byte limits and the existing 600-second per-request timeout. Schema or
syntax failures preserve the response and stop for inspection. It creates no task sandbox and executes no generated code.
The worker returns `export_code` instead of a full script. The controller saves
that response as `exports.py` and constructs `reference.py` as the untouched
baseline, two newlines, then that code. Original text is preserved by
construction. Artifact paths are relative to `/work/outputs`. No separate branch
map or duplicated environment inventory is requested.

The former combined runner is retired. `run_reference.py` and its packaging path
refuse execution before submitting a job. This prevents the old text-only
setup workflow from running against the new preparation schema. Its historical
implementation is preserved at
[2e1fb63](https://github.com/Open-Athena/biotasks/blob/2e1fb637ed0a8dad48e4e8ef9017e49e765d9575/experiments/19-repo2rlenv-notebook-pilot/run_reference.py).
Reusable environment, execution and evidence helpers remain available for the
replacement worker. This document does not assign new execution budgets or
claim that the replacement worker is ready.

## Existing evidence and next step

[Preparation run 006](preparation-runs/006/README.md) passed structural checks
on its first call under the earlier full-script response contract. Its CSV
endpoint selection remains unvalidated. The new append-only contract prevents
source-comment edits by construction and makes the output path base explicit;
source preservation and the explicit path convention passed run 007 checks.
Run 007 nevertheless proposed full-state and diagnostic exports; this requires
selection review before execution. The revised prompt excludes mixed-state
containers explicitly and requires evidence of each result’s scientific role.
The revised prompt and single-call policy completed [run 008](preparation-runs/008/README.md):
one call, no repair, structural checks passed. It avoids the full-object dump
but still exports diagnostic/intermediate columns in broad cell/gene tables.
Endpoint selection remains unresolved.

[Preparation run 005](preparation-runs/005/README.md) used the preceding contract:
its full-object export and newly captured expression are not evidence of
compliance with the revised selection rule. Its recorded output stays unchanged.
The [historical execution record](https://github.com/Open-Athena/biotasks/blob/2e1fb637ed0a8dad48e4e8ef9017e49e765d9575/experiments/19-repo2rlenv-notebook-pilot/reference-execution.md)
explains earlier reference runs under the superseded workflow.

The latest run 008 preparation output needs inspection before advancing. Tool-enabled setup
is the next implementation boundary; it must preserve the science while resolving
dependencies and staging inputs. Task construction, artifact comparisons, Harbor
validation, blind solving and publication remain downstream work. The preparation run is complete; execution and viewer updates remain deferred.
