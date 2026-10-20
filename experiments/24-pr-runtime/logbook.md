# #24: unattended pr_runtime

## 2026-10-20 — baseline and inventory

Objective: finish [issue #24](https://github.com/Open-Athena/biotasks/issues/24).
Production discovery, conversion and acceptance must have no Codex dependency.
Development and separate quality assessment may use Codex; task-specific repairs
cannot count as unattended yield.

- Research branch: `codex/research/24-pr-runtime`.
- Verified current `main` and research base:
  `2a1950d239f1ada467c35393991dac87debe35f7`.
- Inventory source: #16 commit
  `09e375e2dd5a2d1e055ef2e78efe778f636b9311`.
- Historical #21 branch inspected at
  `89977ae00aff857474742e0d342db85af3dfdfcb`; its source manifest pins
  Repo2RLEnv `27d04ee8203cd5b2f20c3997d13836e5f5b64238`.
- No historical model/compute spending allowance is reused. No model calls,
  task execution or remote workers have been launched for #24.

`prepare_inventory.py` reconstructs the historical denominator using four
Git-versioned inputs. The output records each input's SHA-256 and byte size.
It found 1,014 sources, 871 primary GitHub repository mappings and 143 sources
without a primary mapping. The repository-count ledger contains 937 rows;
the README pass contains 952. Their union, including primary mappings and
historical aliases, contains 952 repository names. Of these, 871 have primary
source mappings; linked/tutorial repositories must not silently inherit primary
source status. Live GitHub IDs still need reconciliation.

Inventory execution: 2026-10-20 14:29:54–14:29:55 UTC, exit 0, peak RSS
24,076 KiB against a conservative 64 MiB estimate. The node-wide nonblocking
lock, single-thread environment, nice/ionice and memory/load admission checks
were applied. Completion load was 0.28 and MemAvailable 4,518,584 KiB.
An initial wrapper failed before starting the script because `load` is a gawk
builtin; renamed the wrapper variable to `node_load`.

`collect_repository_metadata.py` retrieves public metadata through ordinary
authenticated `gh api graphql`, in serial batches of 20, with exact-query
hashes, timestamps, resumable response files and a rate-limit stop.
The initial 20-repository batch succeeded without GraphQL errors. This is
read-only metadata collection, not repository builds or task generation.
Lifetime merged-PR counts are availability metadata, not counts within an
evaluation window and not eligibility estimates.

## Native implementation inspection

Inspected the following files at the pinned Repo2RLEnv revision via GitHub's
contents API:

- [pr_runtime.py](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/src/repo2rlenv/pipelines/pr_runtime.py)
- [pr_runtime_validate.py](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/src/repo2rlenv/pipelines/pr_runtime_validate.py)
- [Pipeline documentation](https://github.com/huggingface/Repo2RLEnv/blob/27d04ee8203cd5b2f20c3997d13836e5f5b64238/docs/pipelines/pr_runtime.md)

Existing code already handles PR listing, title/metadata filters, diff splitting,
structural filters, bootstrap-based validation and Harbor export. Reuse these
capabilities before introducing an alternative implementation.

Important baseline properties to preserve and test:

- `limit` bounds listed PRs, not accepted tasks; newest-first selection is not a
  representative sample.
- Linked-issue and language options are documented as accepted but unenforced.
- Native test-path and new-test-function heuristics can affect language coverage.
  Report unsupported profiles separately from structural rejection.
- Validation accepts FAILED or ERROR to PASSED transitions. A missing symbol
  introduced by a fix can be legitimate; unrelated environment/collection
  failures must be distinguished rather than categorically counting every
  ERROR as biological evidence.
- Native acceptance requires F2P but does not require P2P. The documented
  verifier can fall back to exit-code scoring on unparsed logs. A stricter
  automated acceptance profile must reject incomplete parsing and explicitly
  define regression coverage.
- Runtime cleanup preserves named dependency directories but can remove compiled
  project outputs. #21's adapted successes cannot establish the native
  baseline's unattended yield.

Next: reconcile live repository identities and language/activity coverage;
freeze the PR-history window, stratified sample and development/evaluation
split; inspect native selection against sampled diffs; then specify executable
inputs, numerical acceptance targets and a bounded resource budget.

## Completion status

Inventory reconstruction and live metadata collection are complete.
PR suitability, held-out execution, audited quality, recurring cost, operational
pipeline validation and the final develop/stop decision remain unproved.

## 2026-10-20 — live metadata and frozen repository panel

All 952 historical names received a disposition: 951 live repository IDs and
one unresolved API response. The 871 primary-source repositories are all
represented among the live IDs. Across all live repositories, 882 have at least
one merged PR; their lifetime total is 333,261. This is availability evidence,
not an estimate of eligible tasks or of recent PR volume.

The frozen hash-ranked, disproportionate language panel has 12 repositories:
psychopy/psychopy, nipy/nipype, MLCIL/scikit-fingerprints, fastlmm/PySnpTools,
Huber-group-EMBL/rhdf5, sneumann/xcms, nanoporetech/dorado, samtools/samtools,
fastlmm/bed-reader, nglviewer/ngl, AIM-Harvard/pyradiomics and
dauparas/ProteinMPNN. Selection considered primary-source repositories with
at least one lifetime merged PR, excluding archived/empty repositories.
The eligible stratum populations and all exclusions are in
`inventory/repository-panel.json`; the selection script was written before
reading any of these repositories' PRs.

PR inspection window: 2025-10-20 through 2026-10-19 inclusive. Sparse or inactive
sampled repositories will not be replaced. Primary language alone is not a
runner-compatibility determination: for example, notebook-dominant repositories
may contain Python libraries.

Metadata summarization, panel selection and input-derived accounting checks all
passed at 14:34:24 UTC. Each command held the shared heavy-work lock and used
the required resource guards/thread limits/priorities. Peak RSS was respectively
20,272 / 22,908 / 20,540 KiB, below the 64 MiB estimate; each exited 0.
End load was 0.11, MemAvailable 4,529,844 KiB. The metadata collector exited
normally and has no remaining worker.

## 2026-10-20 — PR window and static eligibility

The frozen panel contains 594 merged PRs in the declared window, with complete
pagination and count reconciliation for every repository. Hash sampling selected
115 PRs (up to 20 per repository). Four repositories had no merged PRs in the
window and were retained without substitution.

| Repository | Window merged PRs | Sampled | Native statically eligible |
| --- | ---: | ---: | ---: |
| psychopy/psychopy | 315 | 20 | 2 |
| nipy/nipype | 27 | 20 | 4 |
| MLCIL/scikit-fingerprints | 111 | 20 | 10 |
| fastlmm/PySnpTools | 2 | 2 | 0 |
| Huber-group-EMBL/rhdf5 | 57 | 20 | 0 |
| sneumann/xcms | 12 | 12 | 0 |
| nanoporetech/dorado | 0 | 0 | 0 |
| samtools/samtools | 69 | 20 | 0 |
| fastlmm/bed-reader | 0 | 0 | 0 |
| nglviewer/ngl | 1 | 1 | 0 |
| AIM-Harvard/pyradiomics | 0 | 0 | 0 |
| dauparas/ProteinMPNN | 0 | 0 | 0 |

These are 16 structurally eligible candidates, **not validated tasks**.
One additional PsychoPy PR has unresolved diff coverage because the native
diff-header parser's file count differs from GitHub's `changedFiles`; it is
neither admitted nor counted as a confirmed structural rejection.
The disproportionate repository/language sample does not support multiplying
16/115 by the whole inventory's lifetime PR count.

`native_filters.py` evaluates only the exact static-filter AST nodes from the
SHA-verified upstream source. It does not import or run bootstrap/runtime/model
clients. Metadata, source/test split, test-path and new-test-function fixtures
passed at 14:38:12 UTC, exit 0, peak RSS 20,324 KiB.

The static scan ran 14:38:41–14:39:48 UTC, exit 0, peak RSS 49,260 KiB against
a 128 MiB estimate, holding the node-wide lock with resource checks and
single-thread/nice/ionice settings. Active memory/load observations stayed above
2 GiB available and below the 2.5 load stop threshold. One later load reading
was 1.78, so no additional heavy command was launched then. The scan has exited;
there is no owned analysis worker left running.

Representative native filter limitation: rhdf5 PRs 175, 180 and 226 add
`test_that(...)` tests, but the new-test regex recognizes Python/Go/JavaScript
forms and does not recognize R's form. Native rejection is not evidence that
the underlying R changes lack regression tests. C/C++ parser/profile support
also remains separate from static source/test splitting.

Cached diffs and hash receipts remain local pending source-terms/public-eligibility
review; they have not been published or counted as archived. Search metadata,
sampling inputs and static-filter code are checkpointed separately.

Next: complete recent-PR count coverage beyond the small panel, resolve the
diff-coverage discrepancy, freeze the development/held-out candidate split,
inspect bootstrap/provider requirements and prepare the bounded execution plan.
The issue's execution, automatic acceptance, quality/cost and operational
pipeline requirements remain open.

## 2026-10-20 — Iris/TRC execution direction

The user explicitly directed parallel CPU work toward Iris, especially TRC.
Use existing reserved TRC CPU capacity for parallel builds/validation, with
bounded resources, durable evidence and cleanup. This is not permission to
purchase new capacity, launch accelerators or restart cluster services.
No Codex subagents were requested or launched.

The current Iris documentation distinguishes ordinary CPU jobs from Docker
socket access and privileged nested runtimes; the latter are admin-gated.
Check supported execution capabilities before choosing the worker implementation.
An old local Iris client environment failed imports before contacting the
controller; the read-only capacity query succeeded with the current Marin
environment at revision `24aa43cea9a508449d4c9094cb3877e6e43e0f67`.
Its bounded first page contained healthy reserved TRC workers. This was not a
full-cluster idle-capacity measurement.

One CPU-only runtime probe was then submitted to a specific already-running
reserved TRC host: 1 CPU, 512 MB RAM, 1 GB disk, DEFAULT container profile,
180-second scheduling deadline, 120-second execution deadline, zero failure or
preemption retries. It requested no accelerator and no new host. It executed
only the checkpointed capability script, with no model calls or target code.

The probe succeeded with exit 0 in one attempt. The standard container has
Python 3.12.15 and `unshare`, but no Docker client/socket, Podman, runsc or
bubblewrap binary. The user-namespace sysctl is enabled; actual rootless runtime
support has not been tested. This proves the reserved CPU execution path, not
native Docker bootstrap support.

The output archive was downloaded and its size/SHA-256 checked, then the report
hash was independently matched against the probe's emitted digest. Sanitized
evidence is in `evidence/trc-runtime-probe/`. Exact job identity and temporary
object-store location remain in private local receipts. The probe is terminal
and leaves no active task allocation; the shared reserved host is untouched.

Next runtime step: check a supported isolated execution route on TRC. Do not
silently mount host Docker access or reuse #21's paid Daytona allowance. If a
generic Iris adaptation is needed, record it as a declared pipeline variant
with separate baseline results.
