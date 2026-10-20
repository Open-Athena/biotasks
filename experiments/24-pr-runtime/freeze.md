# Held-out protocol: biotasks24-python-v1

Prepared before any held-out execution. `heldout-campaign.json` is the
machine-readable freeze: it hashes the worker, bootstrap installer, export
checks, runner constraints, launcher, and three input manifests. The committed
cohort v2 contains five held-out PRs, four development PRs and seven overlap
exclusions. There are no replacement inputs or retries.

The evaluated variant is the pinned Repo2RLEnv native validator, task emitter,
Dockerfile and grader, with a generic declarative Python bootstrap and a
bounded Iris Docker transport. It is not upstream's model-assisted bootstrap.
Pipeline model calls and token budgets are zero. Development used Codex to
write and debug the harness; Codex does not operate the frozen campaign.

Python 3.12 is digest-pinned. Runner dependencies are pinned to the successful
development environment. Target dependencies resolve from the selected
bootstrap revision's declared requirements, editable-backend hook, test
extras/groups and pytest. The resulting package versions are captured, but
package-index contents and target wheels are not archived. This is a frozen
bootstrap algorithm, not a fully reproducible image release.

Bootstrap once per repository: use the first development base for configured
repositories, and the first hash-ranked held-out base for the unseen
repository. Reuse that environment across its PRs. Preserve stage-specific
failures; do not install missing packages or change commands after inspecting
held-out results. Native command normalization and changed-test targeting are
unchanged. Each invocation includes the native empty-test-command rejection
control independently of the adapted profile.

Native-verified candidates proceed to native export, an actual Docker build,
and fresh offline-container grader runs. Require genuine pytest assertion
failures before the fix, nonempty retained passing coverage, complete tracked
test success and clean command completion afterward. Application logger
messages are not pytest test IDs. Reject actual collection/test errors.
Partial fixes may receive fractional native reward but must never receive
full reward or strict resolution. Run unchanged base, reference, up to five
hash-ranked source-file omission controls, and base test-file deletion.
Non-applying controls remain unresolved and fail acceptance.

Before staging hidden tests, check that the fresh container has no `/tests`,
`/solution` or Docker socket, one reachable Git commit and a clean worktree.
Native history scrubbing and the offline runtime reduce oracle access.
These checks do not prove absence of every possible cache or side channel.
No solver model or Harbor trial orchestrator is run.

Independent research audit covers all automatically successful candidates
and the first three rejected candidates by the recorded cohort hash rank.
Audit instruction sufficiency/answer leakage, test relevance, biological
relevance and grading discrimination. Audit cannot repair or rescue a rejected
candidate. It measures quality outside the unattended conversion loop.

Decision gate remains at least four independently verified tasks from the
twelve original held-out slots, across at least two repositories, with no
audited false acceptance and at most twelve allocated CPU-hours per verified
task. Report five actual execution inputs and seven overlap exclusions
separately. The small selected panel is not a population yield estimate.

Use at most two existing reserved TRC CPU workers. Each Iris reservation is
3 CPUs, 10 GB RAM, 30 GB disk and 4,200 seconds, with zero retries; no new
capacity or accelerators. Child containers have 2 CPU/8 GiB/512-process limits,
20 GiB writable-layer checks and 3,000-second lifetimes. Setup is bounded by
1,200 seconds, native validation by 300 seconds per stage, and export/controls
by a combined 1,800-second validation/export deadline per PR. Cleanup has
separate short timeouts and remains available after the deadline. The campaign's three reservations total at most
10.5 allocated CPU-hours, inside the experiment's 48 CPU-hour ceiling.
Remove only this run's labeled containers/images, retain shared base caches,
and record cleanup. Download and verify archive/report hashes automatically.

Run with Iris/rigging available on `PYTHONPATH`:

```bash
python run_campaign.py heldout-campaign.json \
  --state-dir /private/path/biotasks24-heldout \
  --iris-config /private/path/iris-config.yaml \
  --gcloud /path/to/gcloud
```

Resuming the same command inspects saved job identities and skips verified
completed outputs. Ambiguous submission, missing archive or hash mismatch
fails closed; it does not create a replacement job. Private state includes
infrastructure identities and is excluded from public evidence.
