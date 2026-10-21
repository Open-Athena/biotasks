# Published pr_runtime reproduction logbook

## 2026-10-21 — scope and preflight

Started from main `2a1950d239f1ada467c35393991dac87debe35f7` on a new permanent research branch. Issue #25 remains unchanged. The user authorized replay of Click #3004 and Werkzeug #2979, followed by fresh official generation. Retain the same Sonnet settings/bounds and no external repair calls.

Pinned the HF release at `2e7b836c8e1450d12535f7cd598a4705d51fceac`. Downloaded all 20 task files. Eight of 12 manifest-listed checksums agree; Dockerfile and verifier disagree for each task. Original published bytes are preserved unchanged, with independent hashes in published/download-manifest.json. The manifest's audited revision has the same Dockerfiles but no checksum fields in its own manifest; it does not resolve the newer manifest discrepancy. This is a provenance inconsistency, not a reason to edit the release. Replay will measure the actual pinned published files.

Read-only selection preflight found Click #3004 at rank 232 and Werkzeug #2979 at rank 134 among merged PRs. The official limit=100 overfetches 300 rows, covering both complete date windows: six Click PRs and three Werkzeug PRs. Use the published bootstrap refs and native date selectors without an allowlist bypass. No native model call has run for this issue yet.

Infrastructure uses the documented legacy Docker build resource flags, original Harbor 0.6.6, a pinned Compose client, the existing Iris egress network and a run-owned shared log volume. Published task source and grading remain unchanged. These choices enforce resource/cleanup boundaries and support Harbor's original sibling-container bind paths; they do not repair environments or alter acceptance.

## 2026-10-21 — published controls reproduced

Checkpoint b9386a37 ran once as biotasks26-replay-001. Both nop controls scored 0 with every tracked F2P failing and every P2P passing; both oracle controls scored 1 with parsed tests, tracked resolution and command resolution true. Click: 5 F2P/246 P2P (full selected suite 300 tests). Werkzeug: 9 F2P/110 P2P (119 tests). Task files remained unchanged. All four builds were bounded; the second build of each task reused Docker layers after Harbor removed the prior image. Archive SHA/readback, exact dependencies, logs and full trial artifacts are retained in evidence/replay-001. All owned containers, images and volumes were absent at cleanup. Allocated cost: 0.237969 CPU-hours.

Fresh official generation launched separately with the same checkpoint and approved model settings; published files are not supplied to its bootstrap agent.

## 2026-10-21 — fresh generation and independent replay completed

The unchanged official generator at the b9386a37 checkpoint exported both primary targets from empty caches. Click used six bootstrap turns (153.15 s); Werkzeug used five (108.43 s), including one format-error/INVALID action that the native loop recovered from without intervention. Native selection considered six Click and three Werkzeug PRs and emitted one task per repo; retain its original skip decisions/logs. No task-specific repair, retry or external model probe was used.

Both fresh controls scored 0 at base and 1 with the oracle, with parse_status=ok and command_resolved=true for both oracles. Click: 5 F2P/295 P2P; oracle full selected command 300 passed. Werkzeug: 9 F2P/930 P2P; oracle command 939 passed, one skipped. The source solution patches and F2P JSON files are byte-identical to the published bundles; fresh P2P sets are strict supersets. These are regenerated tasks, not byte-identical historical exports. Generated task files remained unchanged during grading.

The fresh Dockerfiles retain local bootstrap-image references, as upstream documents for native generation before `repo2rlenv push`. No registry or dataset publication was requested or performed. The original generated tasks, bootstrap recipes/transcripts and full trial archive are retained, but the images were cleaned up; a fresh machine requires rebuilding/publishing those bootstrap images or upstream inline packaging. Portability after publication has not been tested. The bootstrap metadata also records verify_passed=true for Click while verify_detail begins exit=1; preserve this inconsistency and rely on the separate task controls for the claims above. The broader Click repository smoke test is not claimed clean.

The generation phase completed successfully, but original cleanup returned early on an image-removal error (parent/child order and already-removed IDs). A dedicated one-CPU, eight-second cleanup on the same host removed the remaining labelled volume and verified no owned containers, controllers, images or volumes remained. Preserve the original supervisor error and separate correction. No generation or model call was repeated. The follow-up helper source was preserved after its one-off execution; its hash is recorded. The adapter now uses refreshed image passes and always attempts cleanup even after archival failure; a dependency-conflict fixture passed. This post-run correction was not part of the generation checkpoint.

All three Iris attempts are terminal, archives downloaded and SHA-verified. Total allocated compute: 0.857194 CPU-hours against the 24 CPU-hour ceiling. Native LLM estimates remain zero; provider billing/token usage was not emitted, so actual model cost is unavailable. The upstream action/observation transcripts are retained; complete rendered model requests are not available. Small evidence stays on this permanent research branch, retained while conclusions depend on it. No supported pipeline has been promoted to main.

Conclusion: the published controls and fresh official generation both work for these two known-success Python repositories. This separates the earlier biology-cohort failures from a universal failure of pr_runtime; it does not establish automated yield across biology repositories or production scalability. The next useful measurement is the unchanged official pipeline on a broader cohort with explicit installation, validation, export, portability and cost accounting.
