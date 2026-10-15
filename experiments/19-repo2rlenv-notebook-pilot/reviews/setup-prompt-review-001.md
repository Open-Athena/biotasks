# Independent setup-prompt review

Reviewed revision: `da5fc02`. Date: 2026-10-15. Static inspection only; no model calls, sandbox creation, reference execution or tests. Scope: canonical setup prompt, its controller and the reviewed preparation-010 contract. No implementation or prompt edits were made.

## Findings

### P2 — Explain working directories and reset timing before asking for path adaptations

The prompt tells the worker to stage expected paths/caches and make necessary path changes, but omits the different working directories and when directories are deleted (`src/biotasks/prompts/notebook-reference-setup.md:25-32,50-62`). The shell starts in `/work/setup`; staging runs in `/work`; scientific execution runs in `/work/run`. The controller deletes `/work/run` and `/work/outputs` **after** staging (`reference_setup.py:153-160,247-267`; `reference_environment.py:31-45`). A reasonable attempt to make relative input paths work by staging a symlink into the execution directory would be erased before execution.

Smallest fix: state those three working directories and that `/work/run` and `/work/outputs` are recreated after staging. Tell the worker to keep staged inputs in the permitted persistent roots and make necessary input-path adaptations refer to those paths. This is generic execution-contract documentation, not a notebook-specific rule. No controller change is necessary for that documented behavior.

### P2 — Describe the allowance as complete test-tool invocations, not guaranteed scientific executions

The prompt describes `test_reference` as building/staging and then running the full reference, without saying that an allowance is consumed even if validation or setup fails (`notebook-reference-setup.md:28-32,86-89`). The counter increments before candidate validation (`reference_setup.py:186-195`). Consequently two malformed manifests or dependency failures can consume both allowances with zero scientific executions. The tool schema and workflow document disclose this, but the actual prompt and the user-facing phrase “two full reference tests” should agree.

Smallest fix: say that each invocation consumes one allowance, including validation/build/staging failures, and recommend inexpensive source/manifest/import checks with `shell` before invoking it. Describe the proposal to the user as one GLM setup session, up to 20 model calls within that session and at most two combined build/stage/offline-test invocations. If the desired policy is instead two actual scientific starts, that requires an explicit controller accounting change rather than a prompt-only correction.

## Small clarifications worth including

- State that declared staged input/cache files must remain byte-identical through execution. The controller checks this after running (`reference_setup.py:270-275`), while the prompt currently only says it “hashes and verifies” them. Distinguish these supplied files from scratch files or caches created by the analysis; do not imply that every runtime-generated file must be declared as an input.
- State that uv uses the base image's existing Python and automatic interpreter downloads are disabled (`reference_environment.py:38-41`). The worker should inspect that interpreter before choosing `requires-python`; the project declaration does not provision another Python version.

## Assessment

The overall stage is coherent: the worker handles setup investigation and recipes, while the controller performs the complete offline reference test and preserves the fixed exports. The five generated files and brief typed final report are understandable. The prompt appropriately refuses scientific rewrites and distinguishes process completion from scientific validation. I found no reason to reintroduce preparation repairs, a new design stage, notebook-specific package rules or another orchestration layer. Address the two execution-contract ambiguities before the first run; then evaluate actual setup behavior.
