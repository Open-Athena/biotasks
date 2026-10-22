# Autonomous notebook pilot

`run_autonomous.py` runs one frozen notebook through conversion, terminal-export
preparation, dependency/input setup and an offline reference test, replay,
specification, construction, scientific grading controls, and native Harbor
oracle/no-op/one blind solver attempt. Scientific artifacts come exclusively from
the existing GLM workers and version-controlled prompts. All intermediate copies,
manifests, structural observations and stage dispatch are programmatic.

Construction uses a candidate-first workflow: its worker submits a reference-based
candidate from the supplied evidence before exploratory shell commands can run.
Controlled execution returns failures; those failures unlock tools for repair.
Numerical comparison and an independent implementation belong to the subsequent
validation stage. A worker may explicitly block an unsupported proposal instead.
This ordering is implemented and tested offline; live evidence is recorded by
factory revision in the run receipts, not implied by this description.

The existing Iris bootstrap accepts this entrypoint. Its submitted payload pins
the factory revision, notebook bytes, runtime archives and configuration. Model
and Daytona credentials remain runtime environment variables from the existing
Secret Manager launcher. Conversion uses the repository's locked environment;
remote workers retain the pinned Repo2RLEnv runtime. No notebook code runs on the
shared development VM. The entrypoint consumes `BIOTASKS_CONFIG` and
`BIOTASKS_SEED`, so changing the seed needs data/configuration, not source edits.

Fresh autonomous payloads contain the project package/build files, experiment
Python helpers and requirements, upstream pin/patches, and only the selected
notebook, seed manifest and any explicitly selected source-notice file. The separately hashed campaign configuration remains
a top-level payload member. Historical outputs and other seeds are excluded;
input metadata records `autonomous-runtime-and-seed-v1`. Continuation entrypoints
retain their complete-checkout archive because they may need prior evidence.

A single host has a two-hour campaign deadline plus the established cleanup
allowance, and at most one Daytona sandbox at a time. Each of five sandbox stages
reserves $1 before creation ($5 total); reservations are conservative allowances,
not invoices. These are within the standing $100 authorization. GLM-5.3 uses
medium reasoning; preparation has one call, other tool sessions retain their
existing finite wall-time boundaries without added byte/token/request caps.
Reference and solver computation are limited to 600 seconds, verifier to 120.
The setup worker retains two reference tests. The grading worker retains its
existing review and repair pass; no external operator supplies repair feedback.

The model adapter permits one timeout retry per author session using the packaged
`worker-timeout-retry` prompt. Only pure model generation is repeated: no response
from the timed-out request reached tool dispatch, and earlier tool actions are
not replayed. The backend outcome and request hold remain uncertain, every new
attempt claims a new ledger slot, and the original deadline and turn/request
allowances still apply. Cancellation, other transport failures, HTTP failures and
uncertain remote tool executions are not retried by this policy. One-call
preparation has no spare turn for recovery. This adds no worker stage or repair.

Terminal outcomes are:

- `validated`: scientific controls accepted the candidate and native oracle/no-op
  controls passed, with a recorded blind solver attempt. Solver success is not
  required. No automatic public release is performed by this runner.
- `rejected`: an explicit worker refusal, unsupported conversion profile,
  or recorded scientific validation failure. Successful reference replays supply
  observations to scientific workers; byte differences alone never reject a seed. The receipt
  links the evidence and rejected stage; it does not label the seed bad science.
- `infrastructure_failed`: unexpected controller/provider failures, time/budget
  exhaustion, uncertain cleanup or missing evidence. This is not a successful
  rejection and does not satisfy the autonomous-run acceptance criterion.

Runs never resume in-place or overwrite prior evidence. Each stage retains its
complete receipts; final evidence is archived and downloaded for hash checking
by the existing export helper. A fresh attempt requires a new campaign identity.
If a controller defect requires a factory change, the next proof run starts from
the original seed; it cannot count a repaired stage continuation as unattended.

The first held-out case is Bioframe's `tutorial_assign_peaks_to_genes.ipynb`, pinned
at `95007ed6fc03b01005d75f95cac511b2df286854`. It had not been used for model task
generation in this project before the autonomous attempts recorded here. The runner receives the notebook and general task
policy, without a manually selected analysis endpoint or task design. Input-data
redistribution is not assessed by this execution test; output remains private
unless separately approved for publication. PR 23 stays draft and unmerged until
this acceptance criterion is met and the user approves promotion.


## Attribution before native validation

An optional `source_notices_file` selects already-reviewed attribution JSON by
canonical experiment-relative path. It is checkpointed and included in the frozen
payload with the chosen seed. This is source/data metadata, not a task question
or scientific-method override; workers do not author it. The controller carries
it unchanged into `attribution.json` before packaging and native trials, retaining
the exact existing notice-equality gate for publication.

The file binds `source_provenance` and `notebook_source_sha256` to that seed,
includes the original `notebook_license.text` with its `sha256`, and lists
`reviewed_inputs`: each has a SHA256, byte count, source URL and terms. Every
materialized input must match a reviewed identity; filenames may change while
bytes remain identical. Unused reviewed source notices may remain. Derived or
additional inputs whose identities are absent require an explicit new review;
the controller does not infer rights or treat a software license as a data
license. Packaging independently rehashes the actual input bytes.

Without an explicit reviewed file, native execution still produces a local task
with publication marked unassessed. This option is not an automatic legal review
or a publication authorization. Scientific controls, native trials, the final
inventory review and a fresh release download remain separate requirements.
Changing notices after native validation still changes the executable bundle
identity and requires validation of that identity; do not relabel an older run.

All subsequent model stages request native GLM-5.3 `high` by default, or another
explicitly configured native level. Effective served effort is not inferred from
the requested setting. A text-only reply in tool mode can receive one explicit
protocol reminder within the same existing session bounds. It executes no tool,
repeats no completed action and preserves the original response. It is not a
semantic task repair or permission to modify frozen scientific artifacts.

## Starting another seed

Commit the notebook, its provenance JSON (a one-item array including `source_sha256`), and a
configuration with a new `campaign` identifier. `notebook_file` and `seed_file`
are paths relative to this experiment directory. Scientific endpoint selection
and task design are not configuration inputs; workers derive them from the seed.

Build the immutable launch payload without network/model effects:

```bash
python experiments/19-repo2rlenv-notebook-pilot/launch_autonomous.py \
  --revision HEAD \
  --config autonomous-cases/peaks-to-genes/config.json \
  --upstream-archive /path/to/pinned-repo2rlenv.tar.gz \
  --output /tmp/new-autonomous-payload
```

The builder reads the configuration and seed from the chosen Git revision,
checks notebook identity before submission, and hashes every payload member.
It refuses an existing output directory. Submit those files through the existing
`launch_iris.submit_prepared` adapter using the approved private provider setup;
credentials and endpoint discovery stay outside the public payload. Submission
is distinct from payload creation. Once the job starts, `run_autonomous.py`
performs the complete stage dispatch without operator-produced handoffs.
