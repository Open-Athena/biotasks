# Migration verification

This run preserves the existing authoring study and checks saved evidence. It
does not launch authors, solvers, model calls, biological data downloads or
scientific software. Source and destination revisions are recorded in the
[migration manifest](../../migration.json).

## Inputs and commands

[preservation.txt](preservation.txt) records the exact local preservation command:
487 tracked files, 4,854,558 bytes, and an inventory of 73 ignored files,
8,912,921 bytes. It exited zero in 0.70 seconds, with peak RSS 22,896 KiB.
The recovered integration prompt and four historical helpers are additional
small evidence files. Original source bytes remain untouched.

The verifier and its inputs are checkpointed before recorded verification:

```bash
python3 experiments/3-authoring-migration/scripts/run_bounded.py 100 \
  python3 experiments/3-authoring-migration/scripts/verify_preservation.py \
  --check-retained-local-source \
  --output /tmp/biotasks-authoring-verification.json
```

The optional local-source check requires the original checkout. Without it,
verification uses only migrated Git files. Record results alongside this page
after execution. Resource estimates are 100 MiB; all substantial commands use
the shared nonblocking lock, resource gates, one thread and low priority.

## Boundaries

Navigation checks concern relative Markdown target paths, excluding immutable
worker prompts, inputs and outputs that contain historical source locators.
External link availability and fragment anchors are not tested. Keeping the
whole source subtree avoids rewriting historical links or recorded hashes.

JSONL checks validate counts, identities and references, not scientific
semantics. CLI event/metric checks verify the recorded comparison's consistency,
not served model identity, billed cost or model reproducibility. The saved
UCSC catalog can be recounted without executing any listed command. Full native
execution and independent task authoring remain absent.

The source's historical Marin documentation-build failure remains preserved
in its records; a BioTasks package test cannot turn that failure into a success.
Report migration integrity, package checks and GitHub CI independently.
