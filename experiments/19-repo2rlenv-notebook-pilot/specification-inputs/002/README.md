# Next stage: coverage review and task specification

The reviewed input bundle for specification run 002. This is stage 3
of the artifact-reproduction proposal. One fresh GLM pass reviews preparation's
endpoint choices against the original source and the executed reference, then
drafts one task spanning all eligible endpoints. It does not select a new scope.

- [Actual canonical prompt](../../../../src/biotasks/prompts/notebook-task-specification.md)
- [Exact proposed input](input.json), generated from [setup run 001](../../setup-runs/001/README.md)
- [Response schema](response-schema.json) and [schema implementation](../../specification_protocol.py)
- [Input builder](../../specification_inputs.py) and [task policy](../../specification-policy.json)

The input contains the complete converted source, preparation plan and exports,
tested reference and diff, input identities, resolved package/version list,
execution logs, and structural output audit. Each supplied file has a hash. The full uv lock is retained as execution evidence with its hash; wheel URLs/hashes are omitted from model context.
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

Regenerate the exact input from the repository root:

```bash
python experiments/19-repo2rlenv-notebook-pilot/specification_inputs.py \
  experiments/19-repo2rlenv-notebook-pilot/setup-runs/001 \
  experiments/19-repo2rlenv-notebook-pilot/specification-inputs/002/input.json \
  --policy experiments/19-repo2rlenv-notebook-pilot/specification-policy.json
```
