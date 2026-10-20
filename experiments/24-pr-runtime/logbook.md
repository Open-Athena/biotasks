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
