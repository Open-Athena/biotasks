# Published pr_runtime reproduction logbook

## 2026-10-21 — scope and preflight

Started from main `2a1950d239f1ada467c35393991dac87debe35f7` on a new permanent research branch. Issue #25 remains unchanged. The user authorized replay of Click #3004 and Werkzeug #2979, followed by fresh official generation. Retain the same Sonnet settings/bounds and no external repair calls.

Pinned the HF release at `2e7b836c8e1450d12535f7cd598a4705d51fceac`. Downloaded all 20 task files. Eight of 12 manifest-listed checksums agree; Dockerfile and verifier disagree for each task. Original published bytes are preserved unchanged, with independent hashes in published/download-manifest.json. The manifest's audited revision has the same Dockerfiles but no checksum fields in its own manifest; it does not resolve the newer manifest discrepancy. This is a provenance inconsistency, not a reason to edit the release. Replay will measure the actual pinned published files.

Read-only selection preflight found Click #3004 at rank 232 and Werkzeug #2979 at rank 134 among merged PRs. The official limit=100 overfetches 300 rows, covering both complete date windows: six Click PRs and three Werkzeug PRs. Use the published bootstrap refs and native date selectors without an allowlist bypass. No native model call has run for this issue yet.

Infrastructure uses the documented legacy Docker build resource flags, original Harbor 0.6.6, a pinned Compose client, the existing Iris egress network and a run-owned shared log volume. Published task source and grading remain unchanged. These choices enforce resource/cleanup boundaries and support Harbor's original sibling-container bind paths; they do not repair environments or alter acceptance.

## 2026-10-21 — published controls reproduced

Checkpoint b9386a37 ran once as biotasks26-replay-001. Both nop controls scored 0 with every tracked F2P failing and every P2P passing; both oracle controls scored 1 with parsed tests, tracked resolution and command resolution true. Click: 5 F2P/246 P2P (full selected suite 300 tests). Werkzeug: 9 F2P/110 P2P (119 tests). Task files remained unchanged. All four builds were bounded; the second build of each task reused Docker layers after Harbor removed the prior image. Archive SHA/readback, exact dependencies, logs and full trial artifacts are retained in evidence/replay-001. All owned containers, images and volumes were absent at cleanup. Allocated cost: 0.237969 CPU-hours.

Fresh official generation launched separately with the same checkpoint and approved model settings; published files are not supplied to its bootstrap agent.
