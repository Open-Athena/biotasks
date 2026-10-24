# Existing PR task validation

`biotasks validate` resumes native controls for existing Repo2RLEnv `pr_runtime`
exports. It does not search PRs, generate tasks, call models or repair tasks.
The supported exporter revision is `27d04ee8203cd5b2f20c3997d13836e5f5b64238`,
native inline Dockerfiles with the original single-service egress guard.
Recorded bootstrap replay and other initializers are explicit unsupported
inputs and receive no jobs.

Validation requires a POSIX controller and Linux x86-64 workers; prompt
inspection does not require POSIX locking. The backend uses existing healthy
Iris reserved v4 workers with `DOCKER_ACCESS`;
it cannot create capacity. Supply an authenticated Iris SDK environment and YAML
configuration separately from the locked BioTasks environment. The local
controller also needs `gcloud storage cp` to retrieve Iris archives. Credentials
stay local; workers receive isolated run/worker identity variables only. HF
publication uses normal local SDK authentication. These permissions and the CPU
budget must already be authorized: creating a ledger does not authorize spend.

## Planning and execution

Follow the locked [setup](../AGENTS.md#setup-and-cli). Keep run directories on
durable storage, outside Git and `/tmp`. Retain the installed code and Iris
configuration for resumption.

```bash
biotasks validate init-budget /durable/validation/cpu.json --cpu-hours 12
biotasks validate plan manifest.json --work-dir /durable/validation/run-001
biotasks validate status /durable/validation/run-001
biotasks validate run /durable/validation/run-001 --once
```

Example manifest (paths resolve relative to it):

```json
{
  "schema_version": 1,
  "id": "native-validation",
  "repo2rlenv_revision": "27d04ee8203cd5b2f20c3997d13836e5f5b64238",
  "backend": {
    "type": "iris",
    "python": "/path/to/iris-venv/bin/python",
    "config": "/path/to/iris.yaml",
    "worker_revision": "c7c14a252d",
    "network": "iris-egress",
    "gcloud": "/path/to/gcloud"
  },
  "budget_ledger": "cpu.json",
  "max_cpu_hours_per_task": 6,
  "archive": {"kind": "local"},
  "exports": [{
    "path": "exports/cobrapy",
    "initializer": "native-inline",
    "publication": {"eligible": false}
  }]
}
```

Use the actual verified revision/network for your deployment; this example's
revision is not an Iris default. `plan` discovers task directories, copies their
original bytes/modes and freezes payloads and the local SDK source profile.
It does not connect to Iris or submit jobs. Its configured interpreter must
import Iris/rigging for fingerprinting. Inspect `plan.json` and unsupported
inputs before running. Changed code, payloads or configuration stop execution;
adding tasks needs a new plan. No repository-specific Python edits are needed.

`run --once` advances one journal transition; a supervisor can repeat it at
intervals of at least five minutes. Without `--once`, the command runs tasks
serially and waits five minutes between observations. Each PR has independent
identity, payload, journal, budget admission and ownership. Parallel admission
has not been validated here. Completed reinvocations verify local evidence and
perform no remote operations.

## Native settings and recovery

Harbor 0.6.6 and Tenacity 9.2.1 wheels are hash-pinned. Installed Python sources
and metadata are compared against the wheels; dependency versions are recorded.
Other transitive dependencies resolve during setup and are not claimed identical
to historical runs. The task Dockerfile receives only an ownership label. The
Docker/Compose transport adds resource/network caps. Task files, patch, grader,
tracked IDs and native timeout values remain unchanged.

The supported task profile is one CPU/6144 MiB, within a two-CPU/12-GiB Iris
allocation. Controller/build limits fit that allocation. Native nop/oracle
commands retain verifier timeouts and native retry behavior. Their outer bounds
include the agent timeout, two verifier windows and 300 seconds. Admission also
reserves setup, builds and cleanup time; insufficient bounds are rejected before
submission. A timeout is an incomplete control, not permission to repair it.

One cumulative ledger reserves each task maximum plus one-sixth CPU-hour each
for emergency stop and cleanup. Terminal actual allocations, including failures,
reconcile reservations. Actual overruns close new admission while preserving
already reserved stop/cleanup operations; the run reports a budget hold after
preservation and cleanup finish. Recorded actual usage is never discarded.
Models and new capacity remain disabled.

The journal flushes intent before every effect: candidate verification,
submission, terminal observation, archive readback, publication, cleanup and
cleanup verification. Interrupted submissions query their original job names.
A missing uncertain handle remains pending and never permits resubmission.

The worker stops owned execution before sealing evidence. Its stopped controller,
volume and images remain until local archive readback and publication policy are
resolved. A separate cleanup job on the exact original worker verifies the
retained archive hash, removes only owned resources and verifies absence. Shared
public parent images are preserved; there is no prune operation.

Zero task attempts in a terminal scheduler state prove no worker execution.
An empty archive after an attempt proves no such thing: the pre-admitted stop
job runs, the volume is retained, and the workflow holds for salvage. Unverified
stops, unavailable workers and changed evidence cannot become successful cleanup
or native task results. Retain the run directory and investigate the existing
handle; do not regenerate tasks as a recovery shortcut.

## Outcomes and preservation

`complete` describes the **workflow**, including preservation and cleanup. A
build or scheduler failure can complete that workflow with zero usable tasks.
Read `readback.json` for scientific outcomes:

- A complete parseable pair requires original trial/reward/log evidence for nop
  and oracle, matching tracked totals and original source/image identity.
- A positive pair has native nop reward 0 and oracle reward 1.
- A clean oracle command also has whole-command exit 0. Tracked reward 1 alone
  does not establish this.

These controls do not establish biological quality, grader robustness, difficulty
or release readiness. Native timeout/cancellation limitations remain visible.

Every run keeps a flushed, hash-verified local `preserved/` snapshot. For public
HF archival, use `{"kind":"hf-public","bucket":"open-athena/biotasks",
"prefix":"research/<issue>-<topic>"}`. An eligible export needs an actual review
in `publication.review` and source `notices` file paths. A disclaimer cannot
replace redistribution permission. Ineligible exports remain local and are
never uploaded; arrange an approved durable store for restricted evidence.

Public snapshots use date/manifest-hash prefixes, exact allowlists, a credential
scan and anonymous download/hash verification. Interrupted uploads resume missing
objects; differing or unexpected existing objects cause a hold, never overwrite
or deletion. Primary evidence is verified before remote cleanup; cleanup proof
is preserved separately. Follow the [retention policy](storage.md). Remove local
duplicates only after verifying their durable replacement; canonical evidence
and other runs' files/caches are never automatically deleted.

Default checks use synthetic export/transport fixtures without external data,
models or paid compute. They establish lifecycle behavior and package resources.
Native comparisons must be recorded separately before claiming equivalence on
biological reference tasks.
