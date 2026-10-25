# Official PR generation and control workflow

`biotasks generate` exposes the pinned Repo2RLEnv `pr_runtime` pipeline through
declared, source-bound inputs. It acquires the original source, freezes a bounded
official PR listing, invokes the original bootstrap/generator once, locally
prepares its exports with the original native API, and feeds them to
[`biotasks validate`](validation.md). It does not add an author, solver, parser
repair or per-task model loop. Generated tasks may fail reconstruction or native
controls; workflow completion is not scientific acceptance.

This profile uses original source revision
`27d04ee8203cd5b2f20c3997d13836e5f5b64238`, OpenRouter Sonnet4.6,20bootstrap
iterations,1800sbootstrap,temperature0.2,2048outputtokens,$5estimated/actual stop,
no model fallback or request retries. Final-request cost can cross the stop
threshold; the unchanged original cost guard reserves that request separately
against the cumulative campaign ceiling. Native verifier300s and agent1800s are
preserved. No experimental APT or timeout policy is applied.

## Preparation

Use the locked [setup](../AGENTS.md#setup-and-cli), durable directories outside
Git and `/tmp`, and the already authorized reserved Iris backend described in
[validation](validation.md). The separate local SDK environment needs Iris and
Rigging; its libraries are isolated from BioTasks dependencies. A trusted
generation controller needs operator-approved `GH_TOKEN` and
`OPENROUTER_API_KEY` in the submitting process. Only these two names are delivered
through isolated Iris secret files to that controller; repository containers do
not receive them. The tool does not extract credentials or perform browser login.

```bash
biotasks generate prepare-source /durable/source-cache > source.json
biotasks generate identities
biotasks generate profile backend.json --log /durable/profile.log > profile.json
biotasks generate quote /durable/price-quote.json
```

Source preparation downloads the pinned official archive and a6.7KB pinned
`tomli-w` wheel for local export, verifies all353 selected official source members
and Git blob identities, and extracts only allowed paths. It neither installs
nor executes a package. Local `--archive`/`--dependency` files can supply the
same known bytes offline. Cache receipts bind complete source/dependency
inventories; completed reuse makes no download. Interrupted acquisition remains
held in its named staging directory for inspection. Source imports suppress
bytecode writes so normal CLI invocation does not mutate the verified cache.

`backend.json` is the Iris backend object from the validation manifest, not an
entire manifest. `profile` captures only the local SDK source identity. `quote`
captures bounded public route metadata, with no model call. Existing quote
paths are immutable/reused; use a new path to capture newer metadata. Runtime
checks live prices again before every original model request.

Native configuration files use the original upstream schema:

```json
{
  "repo": {"url": "https://github.com/OWNER/REPO", "ref": "FULL_COMMIT", "access": "public"},
  "pipeline": {"name": "pr_runtime", "options": {"limit": 50, "since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}},
  "llm": {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6", "api_key_env": "OPENROUTER_API_KEY", "fallback": null},
  "bootstrap": {"max_iterations": 20, "max_seconds": 1800, "max_llm_spend_usd": 5.0, "cache_dir": "./workspace/bootstrap"},
  "auth": {"use_gh_cli": false, "use_hf_cli": false},
  "output": {"destination": "/work/outputs/raw", "org": "open-athena", "dataset_name": "approved-run", "visibility": "private"}
}
```

The optional official `pipeline.options.require_new_test_funcs` field must be a
JSON boolean. Omitting it retains upstream's default `true`. Explicit `false`
allows assertions added inside an existing test through that structural gate;
it does not bypass the original failing-to-passing check or independent native
controls. This option is frozen into the listing/config binding. Other extra
native options remain unsupported.

Replace the placeholders with an approved full commit and date range. Freeze
the actual bounded native listing before generation:

```bash
biotasks generate freeze-candidates native.json --source-cache /durable/source-cache --output /durable/candidates.json
```

This calls the pinned official `list_merged_prs` using normal `gh`, with its own
read retries unchanged, and records complete descriptors. It calls no model.
Completed reuse verifies the snapshot without another listing. The generator
compares descriptors against an official listing before bootstrap; changed PRs
cause a hold, never replacement selection. Listing limit1..100 is a batch bound,
not evidence that all historical PRs were covered. Preserve an external backlog
when scheduling multiple windows/batches; do not infer suitability from stars or
merged-PR counts alone.

## Manifest and shared budgets

One JSON manifest declares exactly these fields:

| Field | Input |
| --- | --- |
| `schema_version`, `id` | `1` and a fixed lowercase/digit/hyphen cohort identity |
| `repo2rlenv_revision`, `validation_code_identity` | Values reported by `identities` |
| `source` | The `source` object printed by `prepare-source` |
| `backend`, `backend_config` | Backend object and its config file reference |
| `client_profile` | The captured `profile.json` object |
| `price_quote` | Captured quote file reference |
| `budget_ledger` | Absolute path to the one shared cumulative CPU/model ledger |
| `archive` | Local or reviewed public HF policy, as in validation |
| `cases` | Ordered list of one to ten cases; serial execution |

A file reference is `{"path":"/absolute/file","sha256":"..."}`. A directory
reference uses `inventory_sha256`, the canonical JSON SHA of
`biotasks.validation.files.inventory`, including sizes and modes. Each case
declares `id`, fixed `run_id`, `mode: "fresh"`, `native_config`, `candidates`,
`notices` and `publication`. `notices` is a directory reference; public
eligibility/review follows [storage](storage.md). The combined cohort and case
ID, separated by a hyphen, must be at most32characters for validation identity.
No executable adapter path or repository-specific Python file is supplied.

A case may explicitly declare `targeting_policy: "workspace-python-v1"`. This
is an opt-in adapter behavior change, recorded in the payload and generation
window; it is not the official baseline. It anchors newly appended Python test
arguments under `/workspace`, applies shell quoting and preserves recognized
existing targets. It does not change cwd, tests, import/install configuration,
parser, grading, resources or deadlines. Omitting the field applies no override.
Unknown policies and escaping paths reject. Runner/option-value ambiguity and
upstream file extraction remain limitations; filename-with-space cases may run
but still have no identities under the original parser. JUnit is not a reward
fallback. Source/manifest changes require a fresh frozen plan and admission;
never apply a new policy to an active old plan.

Mode `completed` additionally declares `generation_root` and
`generation_plan_sha256`. It imports only a supported source-bound completed,
billed, archived and cleaned generation. A known historical receipt is
import-only and cannot restart an active historical job under new code. Zero
candidates skip generation; zero exports skip native controls.

Create a ledger only for previously authorized limits, or use the existing
campaign ledger. Never create a replacement to reset costs or unresolved holds:

```bash
biotasks generate init-budget /durable/budget.json --cpu-hours 32 --operating-ceiling-usd 90 --exclusive-limit-usd 100 --storage-reserve-usd 10
biotasks generate plan cohort.json --work-dir /durable/cohort-plan
biotasks generate status /durable/cohort-plan
```

These numbers are examples of explicit campaign limits, not default permissions.
The ledger preserves actual cost, original call counts, conservative unresolved
model reservations and CPU/stop/cleanup reservations. It prohibits concurrent
unresolved model runs. `model_admission_closed` is an admission gate;
`paid_model_execution_enabled` records current execution status and is set by
the original reservation code for an authorized run. Creating a ledger or
passing an execution flag does not authorize spending or capacity.

## Execution, outcomes and recovery

```bash
biotasks generate run /durable/cohort-plan --allow-generation --allow-validation --once
```

Planning is offline and atomic; it never submits a job. Run without execution
flags stops before the corresponding stage. `--once` advances one serial pass
for an external scheduler; otherwise the command waits five minutes between
pending transitions. Incomplete or uncertain work prevents the next case
from being admitted. Preserve the same plan, installed code, shared ledger and
backend for resumption. Do not restart on an observation timeout or a missing
handle after submission intent. Unsupported exports with no native task are
recorded as a terminal case and cannot block later cases indefinitely.

Watch mode immediately advances a transition whose durable stage evidence is
already present. It keeps the five-minute interval for pending/uncertain or
unknown states, including missing original handles and incomplete cleanup.
Every next transition still verifies the original journal/evidence bindings;
scheduling does not admit a replacement job or bypass a hold. `--once` keeps
its one-pass behavior for an external scheduler.

Supported native reward-disagreement holds automatically enter the separate
[retention lifecycle](retention.md). A fully archived/readback-verified and
cleaned failure is recorded as scientifically held, with every acceptance flag
false. It can finish that group without skipping later unstarted groups. Unknown
holds, incomplete retention and closed admission still prevent further execution;
cleanup never clears a budget hold. This does not accept late reward files.

Generation allocates an existing4CPU/16GiB worker for at most5400s with a5000s
work deadline, plus pre-reserved stop/cleanup. Its original Docker wrapper caps
the native environments and permits the two containers needed for the upstream
fresh-image check. No new capacity is created. Native controls use the unchanged
validation resource profile and independent nop/oracle jobs. Both stages retain
evidence, verify readback/publication and clean only owned resources.

Each local handoff preserves raw/cache inputs, the base export manifest and a
separate execution-policy manifest. The default emitter rebuilds the recorded
recipe unchanged. It may expose missing installation prerequisites or fail to
reconstruct a bootstrap image. It is not repaired automatically.

`control-outcomes.json` records individual native flags and their source-bound
journal/readback/publication/cleanup hashes. An eligible bundle instance requires
all original collector flags: complete parseable pair, nop0/oracle1 positive
pair, clean oracle command and all P2P tests passing on both sides. This filter
does not alter the grader or turn missing/late rewards into scores. Output
instances are not new unique tasks, and the tool does not authorize dataset
release. Held/inconsistent native artifacts remain unaccepted; some retention
or publication failures require a separately reviewed recovery rather than a
silent log/grading rewrite. Keep the original evidence and reservations.

The installed interface is intentionally restricted to this pinned profile.
Changing upstream, models, images, emitters, timeouts or grading requires a new
explicitly compared profile. The command does not establish broad repository
yield, training readiness, sandbox security or a fix for native timeout/retry
semantics. Report discovery, exports, completed workflows, control flags and
release readiness separately.

## Completed generations after a local connector update

An explicit `completed` case may import a generation from a bundled known
profile after a local connector update. It must retain its original plan,
payload, complete seven-stage journal and evidence, raw/cache inventories,
publication readbacks, complete model billing and settled CPU/model reservations.
Active, partial, held, unknown or changed generations are rejected. The import
only verifies old evidence; it cannot submit, observe, reconcile or complete the
old run. Normal `fresh` resume still requires the exact current implementation.
A new consumer plan records the original and consuming code identities. It does
not count the imported task as newly generated and makes no model call.

Docker image tags are lowercase, while original repository/cache names can
retain case. Local export resolves one matching repository identity, rejects
ambiguous or unsafe caches, and normalizes cache directory names only in its
disposable staging copy for the unchanged upstream inline exporter. Original
cache JSON, raw task/grading assets and source lineage remain unchanged. The
recorded mapping and staging inventory expose this infrastructure adaptation;
missing recipes or mismatched repository/image/ref identities remain errors.
