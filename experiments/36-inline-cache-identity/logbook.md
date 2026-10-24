# Native inline cache identity

## 2026-10-24 — frozen source/fixture comparison

Started from main 2a1950d239f1ada467c35393991dac87debe35f7. Checked official upstream HEAD 4b29471c3b280e752e7ab4f3452ae455a9097094 (0.9.4), acquired three files through ordinary authenticated public GitHub reads, and verified Git blob plus SHA-256 identities. The four relevant writer/parser/recipe/reader functions remain identical to pinned upstream.

Frozen source/fixture protocol and generic lookup-only candidate before execution. Candidate compares repository identities case-insensitively, validates cached metadata, and rejects ambiguous valid recipes. It reuses upstream rendering; no build/install/test command is altered. Copied the 12 original public OHIF task bundles and original bootstrap JSON from #35, verified every byte/mode against its original acquisition, and recorded inventories in original-inputs.json. No runtime or metadata candidate execution yet; no new allocation, model calls or capacity.
