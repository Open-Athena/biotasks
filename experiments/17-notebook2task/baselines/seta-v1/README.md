# v1: released SETA prompt baseline

Start with SETA's released prompts, not the earlier bespoke BioTasks draft.
`manifest.json` pins byte hashes, original paths and commit
`5868a1b5e6ae7528db5904ccb87ff245c2761651`. Files in `upstream/` are unchanged
Apache-2.0 source snapshots. No baseline run has occurred.

## Stages and remaining porting work

1. Stage 1: `kaggle_notebook_adapter.md` plus the preloaded seed block, then
   `idea_agent_base_prompt.md`, produces `draft_spec.md`. The original
   `claude_agents.py` replaces only `{seed_data_folder}` and `{output_path}`
   using string replacement, inserts seed metadata/manifest/notebook outline,
   and appends the shared base. Do not use Python format on the whole prompt.
2. Stage 2: `agent.md` plus the draft spec builds the Harbor task, including
   instructions, environment, solution and tests. It expects the upstream
   `example/hello-world/` boilerplate and a compatible Harbor runtime. Those
   runtime inputs must be pinned and staged before a run; these prompt snapshots
   alone are not an executable replication of the SETA pipeline.
3. Independent BioTasks validation evaluates resulting artifacts. Do not inject
   our desired scientific/grader fixes into the baseline author prompt and then
   call it unchanged SETA.

Before execution, freeze the source manifest, complete seed-preload formatting,
boilerplate, tool permissions, model/settings, budgets and environment. Record
all deviations from SETA's orchestration separately. Prompt-baseline comparison
under our harness is not reproduction of their reported training result.

The adapter assumes downloaded datasets. Stage input retrieval outside the
matched prompt comparison and report its work/cost separately. Our earlier
end-to-end draft additionally asks the worker to retrieve inputs; comparing those
without equal staging would confound prompt quality with input access.

## Preserve limitations to measure them

The original adapter may reject one-model analyses or sources mentioning neural
networks. It favors model comparison and suggests non-general checks such as
train/test accuracy gaps and minimum CV variance. Retain these in the original
baseline and count rejections as outcomes. Do not silently generalize them for
DESeq2/Scanpy. A subsequent `v1-seta-bio` must have an explicit diff and hypothesis.
No such revision is claimed tested or selected.

`src/biotasks/prompts/notebook2task.md` remains the earlier
`v0-biotasks-draft` candidate; it is not the new baseline.

## Other released baselines inspected

- **AutoSDT:** actual code-adaptation and instruction-generation templates are
  released in [adaptation](https://github.com/OSU-NLP-Group/AutoSDT/blob/744a3c70a49c6e53effae65a93d2a7ad9ce923ba/autosdt/src/autosdt_adapt_modify_code.py)
  and [instruction generation](https://github.com/OSU-NLP-Group/AutoSDT/blob/744a3c70a49c6e53effae65a93d2a7ad9ce923ba/autosdt/src/autosdt_adapt_generate_instruction.py).
  They aim to preserve scientific program functionality and specify file outputs.
  Good second candidate, but their Python-program input and evaluation workflow
  differ from a notebook-to-Harbor worker. Not yet ported or run.
- **BixBench:** the inspected official repository at
  `49311180bdacb324c596f2e07596c126f2004008` exposes evaluation/solver prompts.
  An equivalent released notebook-to-task authoring prompt was not established
  in this inspection. Use the released task/notebook pairs as comparison evidence.
- **LongDS:** the inspected DataMind tree at
  `a814927159470ad1624602d233f57b7c0be5882e` includes runner skills/prompts and
  DSGym synthesis code. The specific seed-derived authoring skill described in
  the paper was not identified here. Do not label a solver skill as its authoring
  baseline or infer that the authoring skill is unavailable everywhere.
