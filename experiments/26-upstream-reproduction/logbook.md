# Published pr_runtime reproduction logbook

## 2026-10-21 — scope and preflight

Started from main `2a1950d239f1ada467c35393991dac87debe35f7` on a new permanent research branch. Issue #25 remains unchanged. The user authorized replay of Click #3004 and Werkzeug #2979, followed by fresh official generation. Retain the same Sonnet settings/bounds and no external repair calls.

Pinned the HF release at `2e7b836c8e1450d12535f7cd598a4705d51fceac`. Downloaded all 20 task files. Eight of 12 manifest-listed checksums agree; Dockerfile and verifier disagree for each task. Original published bytes are preserved unchanged, with independent hashes in published/download-manifest.json. The manifest's audited revision has the same Dockerfiles but no checksum fields in its own manifest; it does not resolve the newer manifest discrepancy. This is a provenance inconsistency, not a reason to edit the release. Replay will measure the actual pinned published files.

Read-only selection preflight found Click #3004 at rank 232 and Werkzeug #2979 at rank 134 among merged PRs. The official limit=100 overfetches 300 rows, covering both complete date windows: six Click PRs and three Werkzeug PRs. Use the published bootstrap refs and native date selectors without an allowlist bypass. No native model call has run for this issue yet.

Infrastructure uses the documented legacy Docker build resource flags, original Harbor 0.6.6, a pinned Compose client, the existing Iris egress network and a run-owned shared log volume. Published task source and grading remain unchanged. These choices enforce resource/cleanup boundaries and support Harbor's original sibling-container bind paths; they do not repair environments or alter acceptance.
