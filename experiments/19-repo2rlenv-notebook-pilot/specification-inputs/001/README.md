# Next stage: coverage review and task specification

The reviewed input bundle for specification run 001. This is stage 3
of the artifact-reproduction proposal. One fresh GLM pass reviews preparation's
endpoint choices against the original source and the executed reference, then
drafts one task spanning all eligible endpoints. It does not select a new scope.

- [Actual canonical prompt](../../../../src/biotasks/prompts/notebook-task-specification.md)
- [Exact proposed input](input.json), generated from [setup run 001](../../setup-runs/001/README.md)
- [Response schema](response-schema.json) and [schema implementation](../../specification_protocol.py)
- [Input builder](../../specification_inputs.py) and [task policy](../../specification-policy.json)

The input contains the complete converted source, preparation plan and exports,
tested reference and diff, input identities, resolved dependency environment,
execution logs, and structural output audit. Each supplied file has a hash.
Original evidence is checked against the setup manifest; the later audit is
matched to the executed output hashes, sizes and declared artifact inventory.
The provenance snapshot and audit are separately pinned by this bundle's hashes.
The full biological data and result tables are not included. Audit previews are
explicitly distinguished from full-file measurements.

The proposed worker interface is one GLM-5.3 medium JSON-schema response, with no
tools or automatic repair and no additional token/byte caps. The runner is `run_specification.py`; its launcher packages committed inputs only. Missing scientific evidence is a valid
result: the worker must request the specific inspection instead of guessing.

The response has four fields: a disposition, a coverage/fidelity review, a public
task brief, and a private validation plan. A blocked response cannot contain a
public brief. A ready draft still needs human review, empirical comparison
calibration and executable controls before it is a validated Harbor task.

This pass replaces the old scope-selection design step for the current workflow.
It also replaces the obsolete coverage-proposal-plus-coverage-review sequence;
it reviews the preparation worker's existing inventory rather than generating
another independent inventory first. Earlier prompts/runners remain evidence of
the earlier approach and are not invoked by this checkpoint. This stage performs no scientific execution, task construction, solver, publication of a task or viewer update.

This input is historical: it includes the full lockfile. Later iterations retain
the lock hash and supply the recorded package versions instead. To regenerate
this exact input, use factory checkpoint
`2ce946dc89ec28c9da2156afaf4937d5ae3f8ab7`; do not overwrite it with the current
builder. From a checkout of that revision:

```bash
python experiments/19-repo2rlenv-notebook-pilot/specification_inputs.py \
  experiments/19-repo2rlenv-notebook-pilot/setup-runs/001 \
  experiments/19-repo2rlenv-notebook-pilot/specification-inputs/001/input.json \
  --policy experiments/19-repo2rlenv-notebook-pilot/specification-policy.json
```
