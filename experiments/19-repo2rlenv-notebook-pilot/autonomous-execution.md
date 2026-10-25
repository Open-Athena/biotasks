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

Endpoint preparation remains append-only and saves accessible named results.
For v1, construction may also recover required endpoints absent from those exports
by faithfully rerunning their original source computations on the same inputs and
required state, preserving methods and arguments. This is a provenance-recorded
addition, not a replacement of earlier reference evidence. Independent scientific
validation remains required. Missing state, broken source or recovery requiring
new analyses or changed methods/inputs blocks the candidate; it does not authorize
manual repairs or a smaller task. The canonical prompts now state this rule;
recorded prompts in prior runs remain immutable.

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
not invoices. Payload construction, submission and controller initialization refuse
a full run that cannot reserve all five stages; a smaller financial ceiling does
not define a shorter supported pipeline. The aggregate authorization, reconciled holds and available balance
are recorded in `aggregate-budget.json`; a new submission requires a funded slot.
GLM-5.3 requests
native `high` reasoning; the served effective effort is unverified. Preparation
has one initial call and at most one correction after programmatic validation
rejects its response or a controlled execution finds an export failure. This is
one shared correction, not one correction per failure type. Both responses and
the validation feedback are preserved; a second call is never automatic.
Other tool sessions retain their
existing finite wall-time boundaries without added byte/token/request caps.
Reference and solver computation are limited to 600 seconds, verifier to 120.
The setup worker retains two reference tests. Validation has one shared quality-repair allowance; no external operator supplies repair feedback.

## Preparation repair at the execution boundary

The first preparation response is a `ReferencePlan`, validated against its JSON
schema and materialized as an append-only script. If that response fails static
validation, its optional second call is consumed there. There is then no further
preparation repair available during execution.

If the first response is valid but a controlled reference test reaches a definite
exception in the appended exports, the setup controller can spend that same unused
second call. The repair worker receives the unchanged baseline, original plan and
recorded runtime feedback. It has the existing artifact-submission tool, without
shell or data access. Its response contains only replacement `export_code` (or
`null` to decline) and an explanation. It does not restate endpoint metadata.

The controller preserves all original paths, endpoint descriptions, source
evidence, exclusions and other plan fields, replacing only the export block.
The explanation and exact original request/response remain separate records.
The replacement must compile and pass the existing preparation checks before it
can be handed back to setup. Execution still uses the remaining allowance of
two reference tests; a repair does not replenish it. A valid submission or
successful compilation is not evidence that the reference ran successfully.

A declined or statically invalid repair returns recorded rejection feedback to
setup without crashing the host. The worker can then report an explicit blocker;
it cannot edit the frozen scientific source or silently generate another export
repair. Transport or unexpected controller failures remain incomplete outcomes.
Reference execution, clean replay, scientific comparison, native controls and
release qualification remain separate gates after any accepted repair.

## Specification review before construction

The specification stage now includes an independent GLM review before task assets
are constructed. The reviewer sees source/execution evidence, the proposed public
question and validation handoff, with the writer's self-review and previous review
feedback withheld. Read-only package/reference inspection remains available.
Blocking findings must quote supplied evidence exactly. This grounds findings;
it is not a programmatic proof of their scientific correctness.

A ready review permits construction. An explicit rejection stops the candidate.
A correctable proposal can consume the existing single scientific quality-repair
allowance here: GLM revises the complete proposal under the same source/policy,
then a fresh review checks it. Original proposal, critique, revision and second
review remain separate. A second unresolved review or declined revision rejects;
there is no additional proposal-repair round. Downstream materialization uses the
reviewed effective proposal. If this repair was used, later grader/comparison
repairs are disabled. Review does not supply an executable reward or replace any
independent implementation, negative controls, native trials or release gate.

This adds model sessions within the existing campaign deadline, with no new
sandbox stage, resource allowance or request/token/byte cap. The implementation
has offline routing and evidence-grounding tests; fresh model validation is still
pending. Frozen campaigns 170/171 do not contain this later change.

## Scientific quality repair

If the allowance was not used at specification, the controller may route it to a demonstrated
generated-contract defect or an independent implementation defect. The retained
conflict must bind the exact grader and original probe suite, and the previous
sandbox must have verified cleanup. Routing retains the passing reference-control
requirements; a public-question review must also approve source coverage. A
missing scientific branch cannot be repaired through this contract-only path.
The existing specification session provides
the original source, executed evidence and pinned read-only package inspection to
the `notebook-question-repair` prompt. Broken source, insufficient evidence or a
necessary change to scientific inputs, outputs or methods blocks this path.

A contract correction may revise the public question together with related
grader code, acceptance rules and probe expectations. Check identities and
coverage remain bound to the original inventory; mutation scripts remain
unchanged. The original materialization stays unchanged: a separate derived view
records the question edit and its parent identity. Input bytes, output inventory,
derivation, oracle and original execution remain fixed; the view itself claims
no scientific reexecution. Typed grader edits are separately bound to their
original candidate and probe suite. A fresh sandbox runs a new blind independent
implementation, the revised comparator, every retained probe and source review.
It inherits no prior implementation or acceptance.

For an independent implementation correction, feedback contains only exact
quotes from the public question and that worker's prior code. It does not expose
private diagnosis, grader code or expected answers. Native and release gates
remain required in either case. Consuming the allowance disables a later grader
repair; a further unresolved conflict rejects. A prior grader repair also
prevents another comparison repair. Original and revised evidence/export paths
stay distinct, and `pipeline.json` records the effective materialization/grading
paths for downstream use. This is a bounded attempt, not a guarantee of
correction or broad software portability.

## Model response recovery

The model adapter permits one retry after a timeout, typed SDK connection
failure, or transient HTTP 502/503/504 per author session using the packaged
`worker-generation-retry` prompt. These failure types share one allowance.
Only pure model generation is repeated:
no response from the failed request reached tool dispatch, and earlier tool actions are
not replayed. The backend outcome and request hold remain uncertain, every new
attempt claims a new ledger slot, and the original deadline and turn/request
allowances still apply. Cancellation, unclassified transport failures, other HTTP
failures and uncertain remote tool executions are not retried by this policy. Preparation
does not use this timeout recovery or the empty-response retry: its optional
second response is reserved for static validation or a definite runtime export
failure, as described above. This adds
no worker stage or quality-repair allowance.

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


## Command transport

New autonomous stage configurations select `async_session`: a single owned
AsyncDaytona client is reused for a stage, looks up the exact existing sandbox,
and closes before artifact export and sandbox cleanup. Commands submit once,
observe their event stream and verify the original completion receipt and log
hash. An uncertain submission is never reexecuted. The previous blocking
transport remains available to direct stage configurations that omit
`command_transport`; frozen historical payloads are unchanged.

The transport changes no scientific calls, model allowances, reference tests,
time limits or resource profile. Client lookup/close failures preserve evidence
and trigger the existing incomplete/cleanup path. A synthetic live check covers
success, nonzero exit and intentionally hidden acknowledgement; it does not
establish notebook-level latency or platform-wide exactly-once execution.
