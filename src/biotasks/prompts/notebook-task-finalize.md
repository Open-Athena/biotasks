# Finalize an existing worker-authored task draft

Submit one complete artifact through `submit_artifact`, matching its schema. The
prior worker performed exploratory construction but did not submit an artifact. Its unchanged
programs are supplied in `prior_worker_draft`, with their recorded identities.
They are drafts, not validated task outputs. You also receive the current public
scientific question, source evidence, approved policy and execution limits.

Your job is to turn this existing work into a complete submission for controlled
execution. Preserve its scientific scope and reuse the supplied programs where
appropriate. Do not start another exploratory investigation, invent numerical
tolerances or require exact floating-point agreement. Separate validation workers
will compare numerical results, establish acceptance rules and test wrong answers.
Public software choice does not require reimplementing reference packages in the
private oracle; use the simplest faithful implementation.

Return these fields:

- `disposition`: `ready`, or `blocked` with a concrete reason in `rationale`.
- `instruction`: a standalone scientific question with public input/output paths,
  identifiers, methods, output schema and resource limits. No private paths,
  measured answers, exhaustive API recipe or provisional workflow commentary.
  Acceptance rules will be appended after validation.
- `input_paths`, `output_paths`: exact relative file inventories.
- `derive_code`: complete Python CLI taking `--source-inputs PATH` (JSON manifest
  with original absolute input paths), `--reference-dir PATH`, `--destination PATH`.
  Create exactly `destination/inputs/` and `destination/reference/`: copy original
  data as required, select approved metadata, and project existing reference
  answer fields. Do not recompute or change the reference analysis.
- `oracle_code`: complete Python CLI taking `--input-dir PATH`, `--output-dir PATH`.
  Each declared input path is relative directly to `--input-dir`; there is no
  additional `inputs/` level. Write each output directly under `--output-dir`.
  The oracle runs offline in a clean directory as a separate user, without the
  author workspace, reference answers or undeclared caches. Never embed answers.
- `rationale`: explain provenance, scientific fidelity and unresolved validation
  questions. Distinguish earlier exploratory observations from controlled tests.

Only submission and revision tools are available; there is no exploratory shell.
Submitting a ready artifact triggers real derivation and isolated oracle execution. If the
controller returns a runtime or interface error, submit a complete corrected
artifact through `revise_artifact` using the same schema. Fix the demonstrated
defect; do not change the scientific target or manufacture expected values. A successful execution is only
the handoff to numerical validation, not proof of scientific validity.
