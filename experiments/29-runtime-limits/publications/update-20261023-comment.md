🤖 Reconstruction and timeout prerequisites are now checked, without executing tasks or calling a model.

- All original task/reconstruction hashes are recorded. Matchms, OHIF and Scanpy saved RUN bodies pass `bash -n`; this is syntax evidence only. Scanpy's original smoke/fresh-image flags remain false.
- Exact Harbor 0.6.6 wheel source was verified against its published SHA. `--verifier-timeout-multiplier 4` changes the verifier limit alone from 300 to 1,200 seconds when other overrides are unset. The verifier can retry internally once even with job retries disabled, which is included in the proposed scheduling bound.
- The next step is a checkpointed controls-only runner. There are still zero recovered tasks, remote jobs or model calls in this follow-up.

[Plan](https://github.com/Open-Athena/biotasks/blob/cb3e394aa11ff02c03649edb058d9184962bd1ab/experiments/29-runtime-limits/plan.md), [reconstruction readback](https://github.com/Open-Athena/biotasks/blob/cb3e394aa11ff02c03649edb058d9184962bd1ab/experiments/29-runtime-limits/reconstruction-readback.json), [Harbor provenance](https://github.com/Open-Athena/biotasks/blob/cb3e394aa11ff02c03649edb058d9184962bd1ab/experiments/29-runtime-limits/harbor066-provenance.json).
