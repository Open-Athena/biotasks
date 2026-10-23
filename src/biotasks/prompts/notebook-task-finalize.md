# Finalize an existing worker-authored task draft

Submit one complete artifact through `submit_artifact`, matching its schema.
Unchanged prior programs are supplied in `prior_worker_draft`, with their recorded
identities and provenance. They may be exploratory drafts or previously executed
programs; read the supplied records rather than assuming either. Prior execution
does not prove the public contract complete or scientifically validated.
You also receive the current public
scientific question, source evidence, approved policy and execution limits.

Also account for every supplied `source_operations` ID in `operation_coverage`.
Group IDs sharing the same role and explanation. `result` entries name requested
output `artifact_paths`; `supplied_input` entries name explicit intermediate input
files. Other roles (`support`, `presentation`, `diagnostic`, `not_executed`) have
empty paths and source-backed reasons. `redundant` additionally names a retained
`counterpart_id` and explains the actual projection with unchanged operation,
entities, state and parameters; all other entries set counterpart_id to null.
No absent/cyclic/different-call-target counterpart is accepted. This syntactic
inventory is not a runtime DAG or a scientific eligibility judgment. Matching
call names do not prove redundancy. Do not hide independent analyses as support
or diagnostics; unnamed results still need scientific accounting. Earlier worker
exclusions and drafts remain claims to check against the original source.

Your job is to turn this existing work into a complete submission for controlled
execution. Preserve its scientific scope and reuse the supplied programs where
appropriate. Do not start another exploratory investigation, invent numerical
tolerances or require exact floating-point agreement. Separate validation workers
will compare numerical results, establish acceptance rules and test wrong answers.
Public software choice does not require reimplementing reference packages in the
private oracle; use the simplest faithful implementation.

Make the public contract explicit from the source analysis and supplied programs:
identify entities and output grain, expected multiplicity, and any selection or
combination rule when source records share a key but have conflicting annotations.
Do not hide such rules in the oracle or invent a rule to match saved answers.
Describe file formats and headers supported by the supplied parsing code/evidence;
do not guess from extensions or repeat an unsupported description in a proposal.
Resolve supported omissions in the question; report a blocker for an unresolved
scientific conflict or missing evidence needed to define the task. Keep software
choice open without converting the question into an exhaustive API recipe.

Reuse the supplied code where supported. Where row order or textual numeric
formatting is free, do not demand byte equality. Do not invent observations,
numerical acceptance rules or claims of fresh execution: this stage has no
inspection shell, and later workers establish scientific comparison evidence.
If recorded inspection transcripts are supplied, use completed tool results as
evidence. A command that failed, timed out or was interrupted does not establish
the findings its code intended to calculate.

Return these fields:

- `disposition`: `ready`, or `blocked` with a concrete reason in `rationale`.
- `instruction`: a standalone scientific question with public input/output paths,
  identifiers, methods, output schema and resource limits. No private paths,
  measured answers, exhaustive API recipe or provisional workflow commentary.
  Acceptance rules will be appended after validation.
- `input_paths`, `output_paths`: exact file inventories relative to their respective
  roots. For example, declare `data.csv` and `result.csv`, while public instructions
  refer to `/workspace/inputs/data.csv` and `/workspace/outputs/result.csv`.
  Do not include the `inputs/` or `outputs/` directory prefix in these inventories.
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
