# Authoring research migration

[Migration issue #3](https://github.com/Open-Athena/biotasks/issues/3) preserves
the prompt and task-authoring study from Marin. This research branch starts at
BioTasks `main` commit `37271415c4c201ba9dbbda66c203caa4050744c3` and is never
merged. It imports the source head
[`37973a95c71`](https://github.com/marin-community/marin/tree/37973a95c71d5e1d38bb15c238f1d40369255359),
relative to integration commit `72008dd68247318a367a840a4f41e27fb15ff7e1`.

## Read the evidence

- [Experiment index](baseline/prompt-experiments/index.md): 37 run records,
  exact templates and resolved prompts, inputs, worker outputs and independent
  parent reviews, including negative, incomplete and service-blocked outcomes.
- [Source handoff](baseline/index.md#research-handoff-and-repository-migration)
  and [authoring decisions](baseline/task-authoring.md#current-discovery-decisions).
- [Migration manifest](migration.json): all 482 changed source paths and five
  unchanged files retained for navigation and scientific context.
- [Logbook and promotion decisions](logbook.md): evidence, decisions and gaps.
- [Migration checks](runs/2026-09-30-migration/README.md): reproduction scope,
  commands and observed results.
- [Local-file inventory](runs/2026-09-30-migration/local-files.json): 73 files,
  8,912,921 bytes, including four recovered preparation/checking helpers.
- [Proposed archive](runs/2026-09-30-archive-preparation/README.md): locally
  verified bundle of 67 cache files plus notices; six UCSC files retained at
  source pending terms review. Nothing has been uploaded.

The imported `baseline/` is immutable historical evidence. Source files are
byte-identical, with their original links, dates, commands, hashes and outcome
claims. The entire source subtree is retained so its navigation remains local.
Historical absolute paths in commands and run records identify the Marin
checkout; use `migration.json` to locate the corresponding preserved file.
They are not instructions to execute a new run in that checkout.

The two candidate templates are also installed at the normal
[prompt paths](../../src/biotasks/prompts/) on this research branch. These copies
are the branch's editable candidates; the preserved baseline remains frozen.
They are not promoted to `main`. The discovery template still has recorded
failures, and the authoring template has never been trialed. No runnable
generator, Harbor task or independently validated task is supplied by this
migration.

The [original integration template](baseline/historical-prompts/72008dd682-find-units.md)
is recovered separately to verify the first experiment's historical hash.
The proposal-only and removed reconciliation templates remain available through
the source history and per-run snapshots; neither becomes an active prompt.

## Check the saved record

Run the read-only verifier from the repository root, using a new output location:

```bash
python3 experiments/3-authoring-migration/scripts/run_bounded.py 100 \
  python3 experiments/3-authoring-migration/scripts/verify_preservation.py \
  --output /tmp/biotasks-authoring-verification.json
```

The 100 MiB estimate covers about 5 MB of tracked inputs and streaming event-log
reads. The shared-node guard acquires the nonblocking lock, sets one thread and
low priority, checks load and memory, monitors the child, and records timing,
exit status and peak RSS. Use `--check-retained-local-source` only while the
original source cache is available. This checks its exact inventory too.

The verifier checks preserved hashes, historical prompt/input/output claims,
normalization originals, local navigation paths, JSONL counts and references,
identical-prompt repeats, the CLI comparison against its recorded metrics and
events, and the UCSC catalog's saved dispositions. These are integrity and
consistency checks, not a new scientific review. External URLs and Markdown
fragment anchors are outside its link-check scope.

Do not execute the recovered helpers or archived CLI wrapper directly: they
contain source-checkout paths, can overwrite results and can launch workers.
Their `.py.txt` suffix makes their historical status explicit. Future experiments
need a fresh run directory, an adapted and checkpointed runner, recorded inputs,
model/settings/environment, withheld review criteria, and a separately stated
scope and execution budget. Model outputs cannot be reproduced deterministically
from these records, and unavailable historical settings remain unknown.

## Continue after the migration

The continuing research question is how to obtain source-faithful inventories
that an independent task author can use successfully. Preserve the distinctions
between source discovery, inventory consistency, task construction, native
execution and independent validation. Output counts and worker readiness
statements do not measure those outcomes interchangeably.

As in [discovery migration #2](https://github.com/Open-Athena/biotasks/issues/2),
the migration issue can close after preservation and handoff while a separate
research issue remains open. A continuing authoring issue has not yet been
published. New model calls, paid compute and parallel agents are outside this
migration's execution budget. The current work is bounded preservation and
saved-input verification only, targeting under ten minutes of local computation
per command and at most 100 MiB for preservation/analysis.
