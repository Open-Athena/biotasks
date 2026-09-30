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

## Recorded outcomes

The [saved-input verification](verification.json) passes: 487 tracked files,
37 run records, 879 hash claims (including all 73 retained local files), six
embedded pre-normalization originals, and 636 relative navigation paths.
The [resource record](verification.txt) reports exit zero in 0.15 seconds and
23,208 KiB peak RSS. The verifier/input checkpoint is
`3aef93310e4be3255e8df30f748b9b626a7631d8`.

The first [attempt](verification-attempt-1.json) correctly matched all hashes
but failed its catalog recount: the verifier parsed the 45 inspected table rows
and missed the 283 separately listed pending entries. This was a migration
checker defect. The correction includes both forms; the original worker output
and historical catalog claim were not changed. Keep the failed check as evidence.

The four uncapped CLI cells use identical saved templates/resolved prompts and
the recorded source revision. Saved event streams, completion/failure status,
unit/data counts, elapsed times and reported token usage match the comparison
manifest. Sol/high remains an incomplete service-blocked result with no final
response. All five round-two/round-three pairs use identical templates. The
UCSC table recount is 328 unique entries: 45 inspected and 283 pending. This
check does not establish the semantics or completeness of those commands.

[Package checks](package-checks.txt) pass: Ruff lint and formatting, ty, all
five pytest tests, and all pre-commit hooks. Tests build/install the package and
verify exact candidate-template bytes and CLI loading outside the checkout.
They used Python 3.13.13, locked uv 0.12.21 and one worker; exit zero in 2.12
seconds, peak RSS 57,080 KiB. [Environment setup](environment-setup.txt) used
the locked offline cache. The independent [helper lint/format check](helper-checks.txt)
passed and formatted three experiment scripts. These are local checks;
no GitHub CI run or scientific task validation is claimed.
