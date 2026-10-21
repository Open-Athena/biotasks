# Two additional notebook examples

The user selected MDAnalysis RMSD and COBRApy FBA after the first autonomous
validated Bioframe task. These notebooks have not previously been executed by
this factory. They are deliberately selected examples, not a random sample.

Use the original pinned notebooks and source metadata in
`autonomous-cases/mdanalysis-rmsd` and `autonomous-cases/cobrapy-fba`. Source
licenses are retained beside them. MDAnalysis uses a simulation trajectory;
COBRApy uses a curated metabolic model. These are not observed experimental
sample cohorts. Data redistribution and any new public release require their
own review; execution archives remain private.

Freeze one factory revision before either first attempt. Run RMSD 015 and FBA
016 sequentially, with the existing two-hour campaign plus cleanup allowance,
GLM-5.3 medium, CPU-only 4 CPU/8 GiB/10 GiB task environment, ten-minute
reference/solver limits, offline scientific execution and $5 per-run ceiling.
Budget reconciliation is recorded in `budget-reconciliation-20261021.json` and
`aggregate-budget.json`; no higher aggregate authorization is assumed.

The only admission changes are general presentation normalization: remove
standalone `%matplotlib inline` and argument-free first-line `%%time`, preserve
Python statements in order, and ignore recorded editor presentation metadata.
Unknown magics remain unsupported. The runtime never branches on notebook
identity. Seed metadata does not prescribe task objectives, selected outputs,
scientific methods, grader rules or repair instructions.

Record the first outcome for both notebooks under this frozen revision before
revising the factory. Distinguish validated tasks, explicit rejections and
infrastructure failures. Preserve any failure; do not substitute a notebook or
manually repair generated science to obtain success. General factory changes
motivated by the results require a new recorded revision and separate reruns.
Two examples provide additional evidence, not broad generalization proof.

## First outcomes and subsequent decision

Both first attempts used `da37f25d` without operator handoffs. MDAnalysis 015
passed reference execution and fresh replays, then failed specification because
the provider returned an empty tool response. Preserve this infrastructure failure
in `autonomous-runs/015`. COBRApy 016 reached construction and returned a blocked
diagnostic candidate, so its original pipeline outcome was worker decline.

COBRApy's setup worker had repaired a missing source import. The user subsequently
decided to reject notebooks needing source-code repairs for now. Record that
source rejection separately from the original run's construction outcome in
`autonomous-runs/016`. Missing installed dependencies and input/cache staging
remain setup responsibilities. The general prompt and import-change guard now
enforce the narrower boundary; neither baseline run was patched or rerun under
the new policy. Both hosts terminated and owned sandboxes were verified absent.
