# Experimental generation manifest

`manifest_flow.py` replaces the reference planner's repository, one-PR and
notice-path constants with declared inputs. It reuses the exact source-bound45
generation adapter, original official generation entry, model observer/cost
guard, audited local exporter and seven-stage validator. No official source,
model request, task, test selection or grading setting is repaired. The optional
APT experiment47 is **not** applied here.

This remains research code, dependent on explicitly declared sibling research
sources and PR46's frozen validator. It is not a supported installed CLI, a
complete PR-history crawler or evidence that new tasks pass controls.

## Inputs and stages

One JSON manifest declares `schema_version: 1`, an `id`, the pinned
`repo2rlenv_revision`, `validation_code_identity`, and these fields:

| Field | Meaning |
| --- | --- |
| `adapter` | Absolute source directory and exact hashes for the ten original adapter/handoff files listed in `ADAPTER_FILES` |
| `infrastructure` | File references for the six original Docker/controller/observer/pins/cost-guard assets in `ASSETS` |
| `source` | Source directory inventory, acquisition file reference, and local preparation dependency inventory |
| `price_quote` | Captured public price-quote file reference; offline planning only, not a claim that prices are current |
| `backend`, `backend_config`, `client_profile` | Existing reserved Iris backend and its recorded local SDK identity |
| `budget_ledger` | Absolute shared campaign ledger, checked by the original admission/accounting code during execution |
| `archive` | Explicit local or reviewed public HF archive policy |
| `cases` | Ordered list of one to ten cases; serial admission |

A file reference is `{"path": "/absolute/file", "sha256": "..."}`. A directory
reference uses `inventory_sha256` instead, the canonical JSON hash of the bounded
`biotasks.validation.files.inventory` result, including modes and sizes.

Each case declares `id`, fixed `run_id`, `mode`, `native_config`, `candidates`,
`notices` and `publication`. Native settings stay at the approved Sonnet4.6
profile:20calls,1800sbootstrap,$5estimated/actual stop,temperature.2,2048output,
no fallback or request retries. Existing conservative final-request reservation
is preserved. Its original guard refreshes the public quote before each model
request and refuses a request that cannot fit the admitted reservation. A stale
planning quote does not authorize overspending.

`fresh` prepares a new original-adapter plan. `completed` additionally declares
`generation_root` and `generation_plan_sha256`; it consumes the original complete,
billed, archived and cleaned receipt without driving or restarting generation.
The complete native candidate descriptors and listing options must be frozen;
the original runtime compares them to the official listing before bootstrap.
This interface does not collect candidates or imply all PRs were covered. Empty
candidate batches are explicitly skipped without a job or model call.

```bash
python manifest_flow.py plan --manifest /absolute/cohort.json --output /absolute/new-plan
python manifest_flow.py verify --manifest /absolute/cohort.json --output /absolute/new-plan
python manifest_flow.py advance --manifest /absolute/cohort.json --output /absolute/new-plan
```

Planning is offline, atomic and never admits a job. Interrupted staging is held
for inspection. Completed planning is byte-inert. `advance` defaults to stopping
before fresh generation and controls; it can prepare a local export from an
already completed generation. Explicit `--allow-generation` and/or
`--allow-validation` enter the unchanged admitted lifecycles. These flags do not
override campaign gates, authorize spending, create capacity or enable models
in a disabled ledger. An incomplete, uncertain or held case prevents admission
of later cases. The command advances one pass; an external scheduler must use
bounded/event-driven waits instead of tight polling.

The handoff preserves raw/cache inputs, produces a separate immutable local
base manifest, freezes notices and declares a separate validation execution
manifest. Zero exports produce no control plan or job. Native verifier300s,
agent1800s and the existing validation resource overrides are unchanged. A
workflow completion is distinct from scientific acceptance; read each native
control result. Export counts are not new unique task counts.

## Evidence and remaining limits

`check_manifest.sh` runs offline synthetic cases, with network and child-process
transport forbidden. Fixtures covering two populated repository configurations,
multiple and empty candidates are interface tests, not live PR discovery.
`prove_archived.py` consumes the actual completed45 receipt with global network,
subprocess and credential-read guards; it verifies byte-inert repeated handoff
and unchanged original evidence/global budget. It does not regenerate or rerun
the known task's controls.

The original generator's uncertain-submission, seven-stage interruption,
unknown-billing and cleanup tests remain relevant because those implementation
files are reused byte-for-byte. This new wrapper still needs supported-package
extraction, a portable source/dependency acquisition interface and a fresh native
manifest-path exercise before claiming end-to-end execution through the new
interface. No modified timeout or experimental emitter is implicitly admitted.
