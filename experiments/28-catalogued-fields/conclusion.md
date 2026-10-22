# Draft conclusion — not published

Final MNE/OHIF results, complete-cohort totals, final lifecycle/storage audits and immutable evidence links are pending. This file is preparation for the final issue body; it does not assert completion.

## Research question and comparison

Evaluate the pinned official Repo2RLEnv `pr_runtime` pipeline across ten popular repositories spanning the existing BioTasks #5 scientific-field annotations, using the same bounded settings and no additional environment/task repair loop. This is a purposive repository sample; field labels do not establish that every candidate PR measures a biological competency. Earlier #25/#26/#27 runs remain separate baselines.

Use `huggingface/Repo2RLEnv@27d04ee8203cd5b2f20c3997d13836e5f5b64238`, fresh bootstrap per repository, OpenRouter `anthropic/claude-sonnet-4.6`, no fallback, temperature 0.2, 2048 output tokens, at most 20 bootstrap turns and the original estimated-$5 threshold. The approved serial actual-$5 stop threshold additionally stops subsequent calls after recorded charges reach $5, allowing a final-request overshoot. No additional model calls, manual dependency/interpreter choices, parser/transport/test-scope fixes, candidate bypasses, generation retries or replacement repositories are included.

The approved infrastructure adaptations constrain native containers to 1.5 CPU/six GiB, at most two containers, and Harbor controls to one CPU/six GiB; supply the existing worker network and temporary image aliases; observe unchanged requests/decisions and per-generation charges; and track/remove only owned resources. Jobs use existing reserved TRC CPUs, run serially and allocate four CPUs/16 GiB with an aggregate 100 allocated-CPU-hour ceiling. These limits are part of the measured conditions, not a hardware-matched reproduction of the authors' results.

Each repository receives up to 84 minutes for setup/native generation, a separate hour for independent controls, then cleanup/archive time within 150 minutes. The native paired-validation limit is 600 seconds **per stage**. Harbor 0.6.6 no-op/base and reference-patch oracle controls retain the generated 300-second verifier limit; `-r 0` disables trial retries but retains Harbor's built-in single verifier-timeout retry. No longer-timeout diagnostic was run.

## Results

**Pending:** insert the final ten-row table and actual model/allocated-CPU totals after every original run is accounted for and durably archived. Include failures in cost ratios; distinguish unavailable candidate lists from zero candidates, native decision errors from eligibility skips, and entered/paired/export/control counts from the complete-window inventory.

The fixed September 2026 window contains 436 merged PRs before native filters; it is not a processed-PR or suitable-task denominator. The upstream newest-300 overfetch also limits what the unchanged pipeline can see. Preserve complete-window, preflight and actual native-returned sets separately.

The completed Scanpy controls demonstrate why tracked-test verification and whole-command resolution must be reported separately. PR4329 changes both tracked F2P tests from failed to passed and preserves all six P2P tests, with parsed base reward 0 and oracle reward 1, consistent reward records and unchanged task files. Both commands still exit 1 with the same ten untracked Pandas-warning failures. It qualifies under the declared tracked-test criterion; it is not a clean whole-command resolution. PR4333's two controls both time out and have no reward; retained partial test statuses cannot substitute for a completed grade.

## What limits automation under these settings

- **Acquisition and API robustness:** OpenMS times out in upstream's 60-second pinned checkout before any model call; MACS reaches bootstrap but `gh pr list` fails with GraphQL HTTP 504. These attempts say nothing about their PR suitability or runtime parser compatibility. No retry was added.
- **Bootstrap reliability:** SAMtools, LAMMPS and MMseqs2 exhaust the original 20 turns without a completed saved setup. LAMMPS accepts BASH actions containing trailing model-role/end tags, causing 17 shell syntax errors. MMseqs2 reaches compilation but encounters command timeouts. The retained evidence does not establish a universal model/provider failure or measured OOM/parallelism cause.
- **Historical environment compatibility:** Matchms has a clean fresh bootstrap, but an older PR base cannot import `chemap`. Upstream reuses the newer-revision environment across historical bases without reinstalling their dependencies. A successful current-revision smoke is insufficient evidence for every historical base.
- **Patch transport:** Matchms PR958 raises `OSError(errno=7)` when upstream passes the complete post-fix script as one Docker-exec argument. Exact original diff hashes match the retained validation ledger; read-only reconstruction measures 425,528 bytes for that argument. No reconstructed script was executed and no transport fix applied.
- **Eligibility constraints:** Cobrapy's four candidates are all filtered before paired validation. The unchanged new-test-function gate can reject modifications to existing test bodies, and its recognized function forms do not cover every language/test harness. Static parser limitations must not be attributed to repositories that never reached parsing.
- **Test scope, output parsing and timeout lifecycle:** Intermediate MNE evidence shows upstream preserving the broad positional path `mne/`, colored pytest output yielding empty maps in both original pytest parsers, and timed-out pytest main processes remaining runnable while later validation stages proceed. Resource caps were directly observed. **Pending:** reconcile these observations with the original terminal archive; do not infer repaired task yield or a quantified slowdown from them.

These are distinct failure boundaries. More CPUs alone would not resolve API errors, shell serialization, argument transport, historical dependencies or output parsing. Deterministic hardening at those boundaries is a plausible next experiment; none of those fixes was applied here, and this cohort cannot estimate the resulting yield.

## Evidence, limitations and retention

**Pending:** link the final pushed research commit, exact protocol/input checkpoint, ten original result records, candidate coverage, direct reward audit, actual-charge/resource audit, anonymous HF readback and cleanup/publication receipts. Every original attempt and any deadline-censored/unstarted work must remain visible.

Retain original archives separately from post-attempt diagnostics and derived summaries. Bootstrap transcripts/recipes, source refs and image/layer identifiers establish reconstruction provenance; image bytes are removed after controls, full native package freezes are unavailable, and reconstruction was not executed. Do not claim exact-image replay, solver benchmark scores, a production pipeline or release readiness.

Review public eligibility and source/data notices for each exact allowlist. Exclude credentials, whole-account usage snapshots and their enclosing raw wrapper archives. Important scientific evidence belongs in append-only `open-athena/biotasks` HF snapshots with committed manifests and fresh anonymous size/hash readback. **Pending:** verify all ten snapshots again, all original handles terminal and owned Docker resources empty, watcher exit and deletion of task-owned temporary files before closing the issue.
